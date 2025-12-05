import os
from google.cloud import aiplatform
from vertexai.preview.generative_models import GenerativeModel, Part

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "secrets.json"

aiplatform.init(
    project="josie-480320",
    location="us-central1",
)

model = GenerativeModel("gemini-1.5-flash")

# NEW: load image correctly
with open("sample.jpg", "rb") as f:
    image_bytes = f.read()

image = Part.from_data(
    data=image_bytes,
    mime_type="image/jpeg"
)

prompt = "I am a blind person, provide me with the visual description of the surroundings. The description should be specifically usefull for a blind person"

response = model.generate_content(
    [prompt, image],
    stream=False
)

print(response.text)
