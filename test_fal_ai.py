import os
import asyncio
import httpx
from dotenv import load_dotenv

async def test_fal_ai():
    load_dotenv()
    fal_key = os.getenv("FAL_KEY")
    
    if not fal_key:
        print("❌ Error: FAL_KEY not found in .env")
        return
        
    print(f"✅ FAL_KEY loaded: {fal_key[:10]}...")
    
    try:
        print("⏳ Testing Fal AI Kokoro Hindi API connection...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://fal.run/fal-ai/kokoro/hindi",
                headers={
                    "Authorization": f"Key {fal_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": "नमस्ते, यह एक परीक्षण संदेश है।",  # "Hello, this is a test message."
                    "voice": "hm_omega"
                }
            )
            
            if response.status_code == 200:
                print("✅ Successfully connected to Fal AI API.")
                data = response.json()
                audio_url = data.get("audio", {}).get("url")
                
                if audio_url:
                    print(f"✅ Audio generated successfully! URL: {audio_url}")
                    
                    print("⏳ Downloading audio...")
                    audio_resp = await client.get(audio_url)
                    if audio_resp.status_code == 200:
                        print(f"✅ Audio downloaded. Size: {len(audio_resp.content)} bytes.")
                        
                        try:
                            import soundfile as sf
                            import io
                            
                            with io.BytesIO(audio_resp.content) as f:
                                audio_data, sample_rate = sf.read(f)
                            print(f"✅ Soundfile successfully parsed the audio! Sample rate: {sample_rate}Hz, Duration: {len(audio_data)/sample_rate:.2f}s")
                            print("🎉 Fal AI Kokoro Integration is working perfectly!")
                        except ImportError:
                            print("⚠️ soundfile module not found in this environment, but API works.")
                        except Exception as e:
                            print(f"❌ Error parsing audio with soundfile: {e}")
                    else:
                        print(f"❌ Failed to download audio. Status: {audio_resp.status_code}")
                else:
                    print("❌ API responded, but no audio URL found in response.")
            else:
                print(f"❌ API Request failed! Status: {response.status_code}, Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Exception during testing: {e}")

if __name__ == "__main__":
    asyncio.run(test_fal_ai())
