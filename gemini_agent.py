"""
Gemini Agent module for image-to-text conversion.
Wraps Google Gemini API calls for generating visual descriptions.
"""
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv
import io
import os

load_dotenv()

# Visual aid prompt for blind person navigation
VISUAL_AID_PROMPT = """
    You are acting as a visual aid for a blind person. The person is navigating their surroundings and cannot see, but you provide a complete understanding of what is happening around them. 

    1. **Hazards first**: Begin by immediately mentioning any potential dangers or obstacles that could affect the person's movement or safety. Examples include stairs, curbs, vehicles, bicycles, moving objects, slippery surfaces, crosswalks, or any other hazards. Use clear, concise instructions like "watch out for stairs ahead" or "you are approaching a crosswalk." 

    2. **Scene description**: After mentioning hazards, describe the rest of the surroundings as if the person could perceive it naturally. Include:
    - Key objects and people in the scene
    - Their relative positions (left, center, right)
    - Approximate distances or sizes
    - Any other notable environmental details
    - Don't focus on irrelevant details which don't serve a purpose

    3. **Format and style**: Keep your description short, actionable, and easy to understand. Use natural, conversational language as if you are narrating the scene to someone walking through it. Avoid saying "this is an image" or "the image shows"; describe the scene as if it is happening in real life.

"""


def resize_image(image_input, max_size=(640, 480)):
    """
    Resize an image to a maximum size while maintaining aspect ratio.
    
    Args:
        image_input: Either a file path (str) or image bytes (bytes)
        max_size: Tuple of (width, height) for maximum dimensions
    
    Returns:
        bytes: Resized image as JPEG bytes
    """
    if isinstance(image_input, bytes):
        img = Image.open(io.BytesIO(image_input))
    else:
        img = Image.open(image_input)
    
    img.thumbnail(max_size)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return buf.getvalue()


class GeminiAgent:
    """Agent that wraps Google Gemini API for image-to-text conversion."""
    
    def __init__(self, api_key=None):
        """
        Initialize the Gemini agent.
        
        Args:
            api_key: Optional API key. If not provided, will use GEMINI_API_KEY from environment.
        """
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be set in environment or provided as parameter")
        
        self.client = genai.Client(api_key=api_key)
        self.model = 'gemini-2.5-flash-lite'
    
    def generate_description(self, image_input, prompt=None):
        """
        Generate a text description from an image.
        
        Args:
            image_input: Either a file path (str) or image bytes (bytes)
            prompt: Optional custom prompt. If not provided, uses the default visual aid prompt.
        
        Returns:
            str: Complete text description of the image
        """
        if prompt is None:
            prompt = VISUAL_AID_PROMPT
        
        # Resize image
        image_bytes = resize_image(image_input)
        
        # Generate content stream and collect all chunks
        text_chunks = []
        for chunk in self.client.models.generate_content_stream(
            model=self.model,
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type='image/jpeg',
                ),
                prompt
            ],
        ):
            if chunk.text:
                text_chunks.append(chunk.text)
        
        # Combine all chunks into complete description
        return ''.join(text_chunks)

