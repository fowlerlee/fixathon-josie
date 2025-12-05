# pip install google-genai
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv
import io
import os

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

def resize_image(path, max_size=(640, 480)):
    img = Image.open(path)
    img.thumbnail(max_size)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return buf.getvalue()

prompt = (
    """
    You are acting as a visual aid for a blind person. The person is navigating their surroundings and cannot see, but you provide a complete understanding of what is happening around them. 

    1. **Hazards first**: Begin by immediately mentioning any potential dangers or obstacles that could affect the person’s movement or safety. Examples include stairs, curbs, vehicles, bicycles, moving objects, slippery surfaces, crosswalks, or any other hazards. Use clear, concise instructions like “watch out for stairs ahead” or “you are approaching a crosswalk.” 

    2. **Scene description**: After mentioning hazards, describe the rest of the surroundings as if the person could perceive it naturally. Include:
    - Key objects and people in the scene
    - Their relative positions (left, center, right)
    - Approximate distances or sizes
    - Any other notable environmental details
    - Don't focus on irrelevant details which don't serve a purpose

    3. **Format and style**: Keep your description short, actionable, and easy to understand. Use natural, conversational language as if you are narrating the scene to someone walking through it. Avoid saying “this is an image” or “the image shows”; describe the scene as if it is happening in real life.

"""
)
client = genai.Client()
for chunk in client.models.generate_content_stream(
    model='gemini-2.5-flash-lite',
    contents=[
        types.Part.from_bytes(
        data=resize_image("sample2.jpg"),
        mime_type='image/jpeg',
        ),
        prompt
    ],
):
    print(chunk.text)
