import time
import soundfile as sf
import sounddevice as sd
from gradio_client import Client

class KokoroVoiceAgent:
    def __init__(self, voice="af_heart", speed=1.0):
        print("Initializing Kokoro TTS Engine...")
        # Connect to the API once when the agent starts
        self.client = Client("Pendrokar/Kokoro-TTS")
        self.voice = voice
        self.speed = speed
        print("TTS Engine Ready!")

    def speak(self, text):
        """Generates and plays audio instantly from memory."""
        print(f"\nAgent speaking: '{text}'")
        start_time = time.time()
        
        try:
            # 1. Ping the API to get the audio
            temp_filepath = self.client.predict(
                text=text,
                voice=self.voice,
                speed=self.speed,
                api_name="/predict"
            )
            
            # 2. Read the audio file directly into a NumPy memory array
            audio_data, sample_rate = sf.read(temp_filepath)
            
            print(f"[Latency: {time.time() - start_time:.2f}s]")
            
            # 3. Play the audio directly from memory (blocks until finished speaking)
            sd.play(audio_data, sample_rate)
            sd.wait() 
            
        except Exception as e:
            print(f"TTS Error: {e}")

# --- Test it as if it were in your main loop ---
if __name__ == "__main__":
    agent = KokoroVoiceAgent()
    
    # Imagine this is your LLM passing text back to the user
    agent.speak("saurabh fuck off.")
    agent.speak("I am ready for the next task.")