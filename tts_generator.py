"""
Text-to-Speech module using Google Gemini TTS API.
Generates audio files from text descriptions.
"""
from google import genai
from google.genai import types
from dotenv import load_dotenv
import wave
import os

load_dotenv()


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """
    Save PCM audio data to a WAV file.
    
    Args:
        filename: Output file path
        pcm: Raw PCM audio data (bytes)
        channels: Number of audio channels (1 = mono, 2 = stereo)
        rate: Sample rate in Hz
        sample_width: Sample width in bytes (2 = 16-bit)
    """
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


class TTSGenerator:
    """Generator for text-to-speech conversion using Gemini TTS API."""
    
    def __init__(self, api_key=None):
        """
        Initialize the TTS generator.
        
        Args:
            api_key: Optional API key. If not provided, will use GEMINI_API_KEY from environment.
        """
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be set in environment or provided as parameter")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash-preview-tts"
        self.voice_name = 'Kore'
    
    def generate_audio(self, text, output_path):
        """
        Generate an audio file from text.
        
        Args:
            text: Text to convert to speech
            output_path: Path where the WAV file should be saved
        
        Returns:
            str: Path to the generated audio file
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Generate audio content
        response = self.client.models.generate_content(
            model=self.model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self.voice_name,
                        )
                    )
                ),
            )
        )
        
        # Extract audio data from response
        if not response.candidates or len(response.candidates) == 0:
            raise ValueError("No audio data in response")
        
        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            raise ValueError("Invalid response structure")
        
        part = candidate.content.parts[0]
        if not hasattr(part, 'inline_data') or not part.inline_data:
            raise ValueError("No audio data found in response")
        
        audio_data = part.inline_data.data
        
        # Save audio file
        wave_file(output_path, audio_data)
        
        return output_path

