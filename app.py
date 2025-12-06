# app.py
# Flask app for Cloud Run: upload image -> Vision API analysis -> Vertex ImageTextModel caption
import os
import io
import json
import yaml
import tempfile
from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv

load_dotenv()  # Load .env variables

from google.cloud import vision
import vertexai
from vertexai.preview.vision_models import Image as VertexImage, ImageTextModel
from gemini_agent import GeminiAgent
from tts_generator import TTSGenerator

app = Flask(__name__)

# Config: set via env vars on Cloud Run or locally
PROJECT_ID = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("VERTEX_LOCATION", "us-central1")  # change if desired

# Initialize clients lazily
# Initialize clients lazily
vision_client = None  # uses ADC (Application Default Credentials)
vertex_initialized = False
vertex_model = None

def init_vertex():
    global vertex_initialized, vertex_model
    if vertex_initialized:
        return
    if not PROJECT_ID:
        raise RuntimeError("Set env var GCP_PROJECT / GOOGLE_CLOUD_PROJECT to your project id.")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    # Use the imagen/imagetext model for captions / Q&A about images
    vertex_model = ImageTextModel.from_pretrained("imagetext@001")
    vertex_initialized = True

def analyze_with_vision(image_bytes):
    """Call Google Cloud Vision API for labels, object localization, and OCR."""
    image = vision.Image(content=image_bytes)

    responses = {}

    # 1) Label detection
    global vision_client
    if not vision_client:
        vision_client = vision.ImageAnnotatorClient()

    labels_resp = vision_client.label_detection(image=image)
    labels = [{"description": l.description, "score": l.score} for l in labels_resp.label_annotations]
    responses["labels"] = labels

    # 2) Object localization (object detection w/ bounding boxes)
    try:
        obj_resp = vision_client.object_localization(image=image)
        objs = []
        for o in obj_resp.localized_object_annotations:
            objs.append({
                "name": o.name,
                "score": o.score,
                "bounding_poly": [
                    {"x": v.x, "y": v.y} for v in o.bounding_poly.normalized_vertices
                ]
            })
        responses["objects"] = objs
    except Exception:
        responses["objects"] = []

    # 3) Text detection (OCR)
    text_resp = vision_client.text_detection(image=image)
    full_text = text_resp.full_text_annotation.text if text_resp.full_text_annotation else ""
    responses["ocr_text"] = full_text

    # 4) Safe search (explicit content flags)
    safe_resp = vision_client.safe_search_detection(image=image)
    safe = safe_resp.safe_search_annotation
    if safe:
        responses["safe_search"] = {
            "adult": safe.adult.name,
            "spoof": safe.spoof.name,
            "medical": safe.medical.name,
            "violence": safe.violence.name,
            "racy": safe.racy.name,
        }

    return responses

def build_prompt(vision_data):
    """
    Build a structured prompt for the ImageTextModel.
    We'll include the Vision API findings so the model has structured grounding.
    """
    labels_text = ", ".join([f"{l['description']} ({l['score']:.2f})" for l in vision_data.get("labels", [])]) or "none"
    objects_text = ", ".join([f"{o['name']} ({o['score']:.2f})" for o in vision_data.get("objects", [])]) or "none"
    ocr = vision_data.get("ocr_text", "").strip() or "none"

    try:
        with open("prompts.yaml", "r") as f:
            prompts = yaml.safe_load(f)
            template = prompts["prompts"]["image_description"]
    except Exception as e:
        # Fallback if file missing or parse error, though ideally we should log this
        print(f"Error loading prompts.yaml: {e}")
        return "Describe this image."

    prompt = template.format(
        labels_text=labels_text,
        objects_text=objects_text,
        ocr=ocr
    )
    return prompt.strip()

def generate_description_with_vertex(image_bytes, vision_data):
    """Call Vertex ImageTextModel to get caption and description. Returns the generated text JSON."""
    init_vertex()
    # Vertex image object from bytes
    v_image = VertexImage.from_bytes(image_bytes)

    # We pass the prompt as a guided question + the raw image
    prompt = build_prompt(vision_data)

    # Get captions (short) first - method get_captions is supported
    try:
        captions = vertex_model.get_captions(
            image=v_image,
            number_of_results=1,
            language="en",
        )
        short_caption = captions[0].text if captions and len(captions) > 0 else ""
    except Exception:
        short_caption = ""

    # Ask a question to get a longer description using ask_question (image Q&A)
    # We'll use the prompt as the question so model composes a paragraph guided by Vision facts.
    try:
        answers = vertex_model.ask_question(
            image=v_image,
            question=prompt,
            number_of_results=1,
        )
        # answers is a list; the model's response text is in answers[0].text or .answer
        long_answer = answers[0].text if answers and len(answers) > 0 else ""
    except Exception:
        long_answer = ""

    # Compose notes from safe_search if present
    notes = []
    ss = vision_data.get("safe_search")
    if ss:
        notes.append(f"SafeSearch flags: {ss}")

    return {
        "caption_from_model": short_caption,
        "description_from_model": long_answer,
        "notes": notes
    }

@app.route("/upload", methods=["POST"])
def upload():
    """
    POST /upload
    form-data: file field named 'image'
    returns: json { vision: {...}, ai: {...} }
    """
    if "image" not in request.files:
        return jsonify({"error": "no 'image' file field in request"}), 400

    f = request.files["image"]
    image_bytes = f.read()
    if not image_bytes:
        return jsonify({"error": "empty file"}), 400

    # 1) Vision API analysis
    try:
        vision_results = analyze_with_vision(image_bytes)
    except Exception as e:
        return jsonify({"error": "vision API failed", "details": str(e)}), 500

    # 2) Vertex AI image->text
    try:
        ai_results = generate_description_with_vertex(image_bytes, vision_results)
    except Exception as e:
        # still return vision results if vertex fails
        return jsonify({
            "vision": vision_results,
            "ai_error": str(e)
        }), 500

    # 3) Return structured result
    return jsonify({
        "vision": vision_results,
        "ai": ai_results
    }), 200


@app.route("/upload-with-audio", methods=["POST"])
def upload_with_audio():
    """
    POST /upload-with-audio
    form-data: file field named 'image'
    returns: WAV audio file download
    
    Process flow:
    1. Read image from request
    2. Generate text description using Gemini
    3. Convert text to audio using Gemini TTS
    4. Return audio file as download
    """
    if "image" not in request.files:
        return jsonify({"error": "no 'image' file field in request"}), 400

    f = request.files["image"]
    image_bytes = f.read()
    if not image_bytes:
        return jsonify({"error": "empty file"}), 400

    # Initialize agents (lazy initialization)
    try:
        gemini_agent = GeminiAgent()
        tts_generator = TTSGenerator()
    except Exception as e:
        return jsonify({"error": "Failed to initialize agents", "details": str(e)}), 500

    # Create temporary file for audio output
    temp_audio_path = None
    try:
        # Generate text description from image
        try:
            description_text = gemini_agent.generate_description(image_bytes)
            if not description_text or not description_text.strip():
                return jsonify({"error": "Empty description generated"}), 500
        except Exception as e:
            return jsonify({"error": "Failed to generate description", "details": str(e)}), 500

        # Generate audio from text
        try:
            # Create temporary file for audio
            temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_audio_path = temp_audio_file.name
            temp_audio_file.close()  # Close so TTS can write to it
            
            tts_generator.generate_audio(description_text, temp_audio_path)
        except Exception as e:
            return jsonify({"error": "Failed to generate audio", "details": str(e)}), 500

        # Return audio file as download
        return send_file(
            temp_audio_path,
            mimetype='audio/wav',
            as_attachment=True,
            download_name='description.wav'
        )
    
    finally:
        # Clean up temporary file after sending
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
            except Exception:
                pass  # Ignore cleanup errors

if __name__ == "__main__":
    # For local testing only; Cloud Run will use gunicorn if you prefer.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
