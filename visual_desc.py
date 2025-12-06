from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv
import io
import os
import threading
import queue
import subprocess
import tempfile
import time
from gtts import gTTS

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

def resize_image(path, max_size=(640, 480)):
    img = Image.open(path)
    img.thumbnail(max_size)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return buf.getvalue()

prompt = """
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

# Queue to pass text chunks from description thread to TTS thread
text_queue = queue.Queue()
audio_queue = queue.Queue()

def generate_description():
    """Generate visual description and put chunks in queue"""
    print("Generating visual description...\n")
    
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
        if chunk.text:
            print(chunk.text, end='', flush=True)
            text_queue.put(chunk.text)
    
    # Signal that description is complete
    text_queue.put(None)
    print("\n\nDescription complete!")

def generate_audio():
    """Convert text chunks to audio using gTTS and put in audio queue"""
    buffer = ""
    sentence_endings = ('.', '!', '?')
    last_tts_time = time.time()
    min_chunk_words = 8  # Minimum words before forcing TTS
    max_wait_time = 1.5  # Maximum seconds to wait before forcing TTS
    
    print("[Audio Generator Started]\n")
    
    while True:
        try:
            # Use timeout to periodically check buffer
            text_chunk = text_queue.get(timeout=0.3)
        except queue.Empty:
            # Check if we should force TTS on buffered text
            current_time = time.time()
            if buffer.strip() and (current_time - last_tts_time) > max_wait_time:
                print(f"\n[Generating TTS: {len(buffer)} chars]")
                try:
                    tts = gTTS(text=buffer, lang='en', slow=False)
                    
                    # Save to temporary file
                    temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                    tts.save(temp_file.name)
                    temp_file.close()
                    
                    audio_queue.put(temp_file.name)
                    print(f"[Audio generated and queued]")
                    buffer = ""
                    last_tts_time = time.time()
                except Exception as e:
                    print(f"\n[Error generating audio: {e}]")
            continue
        
        # If None, description is complete
        if text_chunk is None:
            print("\n[Received end signal]")
            # Generate audio for any remaining text
            if buffer.strip():
                print(f"[Generating final audio: {len(buffer)} chars]")
                try:
                    tts = gTTS(text=buffer, lang='en', slow=False)
                    
                    # Save to temporary file
                    temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                    tts.save(temp_file.name)
                    temp_file.close()
                    
                    audio_queue.put(temp_file.name)
                    print(f"[Final audio generated]")
                except Exception as e:
                    print(f"\n[Error generating final audio: {e}]")
            
            # Signal audio generation is complete
            audio_queue.put(None)
            print("[Audio generation complete]")
            break
        
        buffer += text_chunk
        
        # Check if we have a complete sentence or enough words
        word_count = len(buffer.split())
        has_sentence_ending = any(buffer.rstrip().endswith(ending) for ending in sentence_endings)
        
        if has_sentence_ending or word_count >= min_chunk_words:
            print(f"\n[Generating TTS: {len(buffer)} chars, {word_count} words]")
            try:
                tts = gTTS(text=buffer, lang='en', slow=False)
                
                # Save to temporary file
                temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                tts.save(temp_file.name)
                temp_file.close()
                
                audio_queue.put(temp_file.name)
                print(f"[Audio generated and queued]")
                buffer = ""  # Clear buffer after successful conversion
                last_tts_time = time.time()
            except Exception as e:
                print(f"\n[Error generating audio: {e}]")
                # Keep text in buffer to try again

def play_audio():
    """Play audio files as they arrive using ffplay or mpv"""
    temp_files = []
    player_process = None
    
    print("[Audio Player Started]\n")
    
    # Check which player is available
    player = None
    try:
        subprocess.run(['ffplay', '-version'], capture_output=True, check=True)
        player = 'ffplay'
        print(f"[Using ffplay for audio playback]\n")
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.run(['mpv', '--version'], capture_output=True, check=True)
            player = 'mpv'
            print(f"[Using mpv for audio playback]\n")
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run(['play', '--version'], capture_output=True, check=True)
                player = 'play'
                print(f"[Using sox play for audio playback]\n")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("\n[Warning: No audio player found (ffplay, mpv, or sox)]")
                print("[Install one with: sudo apt install ffmpeg  (for ffplay)]")
                print("[                  sudo apt install mpv     (for mpv)]")
                print("[                  sudo apt install sox     (for play)]")
    
    chunk_count = 0
    while True:
        audio_file = audio_queue.get()
        
        if audio_file is None:
            print("\n[Received audio end signal]")
            break
        
        chunk_count += 1
        temp_files.append(audio_file)
        print(f"[Playing audio chunk #{chunk_count}]")
        
        # Play audio file immediately
        if player:
            # Wait for previous audio to finish before playing next chunk
            if player_process:
                player_process.wait()
            
            # Play the audio chunk
            if player == 'ffplay':
                player_process = subprocess.Popen(
                    ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', audio_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            elif player == 'mpv':
                player_process = subprocess.Popen(
                    ['mpv', '--no-video', '--really-quiet', audio_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            elif player == 'play':
                player_process = subprocess.Popen(
                    ['play', '-q', audio_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        else:
            print(f"[Would play: {audio_file} (no player available)]")
    
    # Wait for last audio to finish
    if player_process:
        print("[Waiting for final audio to complete]")
        player_process.wait()
    
    # Clean up temporary files
    print("[Cleaning up temporary files]")
    for temp_file in temp_files:
        try:
            os.remove(temp_file)
        except:
            pass
    
    print("[Audio playback complete]")

# Create and start threads
description_thread = threading.Thread(target=generate_description)
audio_gen_thread = threading.Thread(target=generate_audio)
audio_play_thread = threading.Thread(target=play_audio)

print("Starting visual aid system...\n")
description_thread.start()
audio_gen_thread.start()
audio_play_thread.start()

# Wait for all threads to complete
description_thread.join()
audio_gen_thread.join()
audio_play_thread.join()

print("\n✓ Visual aid complete!")