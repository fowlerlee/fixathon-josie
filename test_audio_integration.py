"""
Test script for text-to-audio integration.
Tests the complete flow: image -> text -> audio
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def test_gemini_agent():
    """Test Gemini agent with a sample image."""
    print("Testing Gemini Agent...")
    try:
        from gemini_agent import GeminiAgent
        
        # Check if API key is set
        if not os.getenv("GEMINI_API_KEY"):
            print("ERROR: GEMINI_API_KEY not set in environment")
            return False
        
        agent = GeminiAgent()
        print("✓ GeminiAgent initialized successfully")
        
        # Test with sample image if it exists
        sample_image = "sample2.jpg"
        if os.path.exists(sample_image):
            print(f"Testing with {sample_image}...")
            description = agent.generate_description(sample_image)
            if description and description.strip():
                print(f"✓ Description generated: {description[:100]}...")
                return True
            else:
                print("ERROR: Empty description generated")
                return False
        else:
            print(f"WARNING: {sample_image} not found, skipping image test")
            return True  # Agent initialization works
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_tts_generator():
    """Test TTS generator with sample text."""
    print("\nTesting TTS Generator...")
    try:
        from tts_generator import TTSGenerator
        
        # Check if API key is set
        if not os.getenv("GEMINI_API_KEY"):
            print("ERROR: GEMINI_API_KEY not set in environment")
            return False
        
        generator = TTSGenerator()
        print("✓ TTSGenerator initialized successfully")
        
        # Test with sample text
        test_text = "Hello, this is a test of the text to speech functionality."
        test_output = "test_output.wav"
        
        print(f"Generating audio for: '{test_text}'...")
        output_path = generator.generate_audio(test_text, test_output)
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✓ Audio file generated: {output_path} ({file_size} bytes)")
            
            # Clean up test file
            os.unlink(test_output)
            print("✓ Test file cleaned up")
            return True
        else:
            print(f"ERROR: Audio file not created at {output_path}")
            return False
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_flask_endpoint():
    """Test that Flask app can be imported and endpoint exists."""
    print("\nTesting Flask Integration...")
    try:
        from app import app
        
        # Check if the endpoint exists
        with app.test_client() as client:
            # Test that endpoint exists (will fail without image, but that's expected)
            response = client.post('/upload-with-audio')
            # Should get 400 (bad request) not 404 (not found)
            if response.status_code == 400:
                print("✓ /upload-with-audio endpoint exists")
                return True
            elif response.status_code == 404:
                print("ERROR: /upload-with-audio endpoint not found")
                return False
            else:
                print(f"✓ /upload-with-audio endpoint exists (status: {response.status_code})")
                return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Text-to-Audio Integration Tests")
    print("=" * 60)
    
    results = []
    
    # Test 1: Gemini Agent
    results.append(("Gemini Agent", test_gemini_agent()))
    
    # Test 2: TTS Generator
    results.append(("TTS Generator", test_tts_generator()))
    
    # Test 3: Flask Integration
    results.append(("Flask Integration", test_flask_endpoint()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{name}: {status}")
    
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

