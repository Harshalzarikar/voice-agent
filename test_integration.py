"""
Quick integration test for LiveKit Voice Agent setup.
Tests: .env loading, API keys, Django token endpoint, LiveKit connection.
"""
import os
import sys
import json
import urllib.request
import urllib.error

# Add project root
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(ROOT, ".env"))

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
results = []

def test(name, passed, detail=""):
    status = PASS if passed else FAIL
    results.append((name, passed))
    print(f"  {status} {name}" + (f" — {detail}" if detail else ""))

print("\n" + "="*60)
print("  LiveKit Voice Agent — Integration Test")
print("="*60)

# --- 1. Check .env keys ---
print("\n[1] Checking .env API Keys...")

deepgram = os.environ.get("DEEPGRAM_API_KEY", "")
test("DEEPGRAM_API_KEY loaded", bool(deepgram), f"{'set (' + deepgram[:8] + '...)' if deepgram else 'MISSING'}")

groq = os.environ.get("GROQ_API_KEY", "")
test("GROQ_API_KEY loaded", bool(groq), f"{'set (' + groq[:8] + '...)' if groq else 'MISSING'}")

openai_key = os.environ.get("OPENAI_API_KEY", "")
test("OPENAI_API_KEY loaded", bool(openai_key), f"{'set (' + openai_key[:8] + '...)' if openai_key else 'MISSING'}")

lk_url = os.environ.get("LIVEKIT_URL", "")
test("LIVEKIT_URL loaded", bool(lk_url), lk_url or "MISSING")

lk_key = os.environ.get("LIVEKIT_API_KEY", "")
test("LIVEKIT_API_KEY loaded", bool(lk_key), f"{'set (' + lk_key[:8] + '...)' if lk_key else 'MISSING'}")

lk_secret = os.environ.get("LIVEKIT_API_SECRET", "")
test("LIVEKIT_API_SECRET loaded", bool(lk_secret), f"{'set (' + lk_secret[:8] + '...)' if lk_secret else 'MISSING'}")

# --- 2. Check Python imports ---
print("\n[2] Checking Python package imports...")

try:
    from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli
    test("livekit.agents (Agent, AgentSession, etc.)", True)
except ImportError as e:
    test("livekit.agents", False, str(e))

try:
    from livekit.plugins import deepgram as dg_plugin
    test("livekit.plugins.deepgram (STT)", True)
except ImportError as e:
    test("livekit.plugins.deepgram", False, str(e))

try:
    from livekit.plugins import openai as oai_plugin
    test("livekit.plugins.openai (LLM + TTS)", True)
except ImportError as e:
    test("livekit.plugins.openai", False, str(e))

try:
    from livekit.plugins import silero
    test("livekit.plugins.silero (VAD)", True)
except ImportError as e:
    test("livekit.plugins.silero", False, str(e))

try:
    from livekit import api as lk_api
    test("livekit-api (token generation)", True)
except ImportError as e:
    test("livekit-api", False, str(e))

# --- 3. Test token generation locally ---
print("\n[3] Testing LiveKit token generation (local)...")

try:
    from livekit import api as lk_api
    token = lk_api.AccessToken(lk_key, lk_secret) \
        .with_identity("test-user") \
        .with_name("Test User") \
        .with_grants(lk_api.VideoGrants(room_join=True, room="test-room"))
    jwt_str = token.to_jwt()
    test("Token generation works", bool(jwt_str), f"JWT length: {len(jwt_str)} chars")
except Exception as e:
    test("Token generation", False, str(e))

# --- 4. Test Django endpoint ---
print("\n[4] Testing Django /api/livekit-token/ endpoint...")

django_url = "http://localhost:8000/api/livekit-token/?room=test-room&username=test-user"
try:
    req = urllib.request.Request(django_url)
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read().decode("utf-8"))
    has_token = "token" in data and bool(data["token"])
    has_url = "url" in data and bool(data["url"])
    test("Django endpoint reachable", True)
    test("Response has 'token'", has_token, f"length: {len(data.get('token',''))} chars" if has_token else "MISSING")
    test("Response has 'url'", has_url, data.get("url", "MISSING"))
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8") if e.fp else ""
    test("Django endpoint", False, f"HTTP {e.code}: {body}")
except urllib.error.URLError as e:
    test("Django endpoint", False, f"Cannot connect — is Django running on port 8000? ({e.reason})")
except Exception as e:
    test("Django endpoint", False, str(e))

# --- 5. Test Groq API ---
print("\n[5] Testing Groq LLM API (quick completion)...")

try:
    import urllib.request
    groq_url = "https://api.groq.com/openai/v1/chat/completions"
    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": "Say hello in 3 words"}],
        "max_tokens": 20,
    }).encode("utf-8")
    req = urllib.request.Request(groq_url, data=payload, headers={
        "Authorization": f"Bearer {groq}",
        "Content-Type": "application/json",
    })
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read().decode("utf-8"))
    reply = data["choices"][0]["message"]["content"]
    test("Groq API works", True, f'Response: "{reply}"')
except Exception as e:
    test("Groq API", False, str(e))

# --- Summary ---
passed = sum(1 for _, p in results if p)
total = len(results)
print("\n" + "="*60)
print(f"  Results: {passed}/{total} passed")
if passed == total:
    print(f"  {PASS} ALL TESTS PASSED — You are ready to go!")
else:
    failed = [name for name, p in results if not p]
    print(f"  {FAIL} Failed: {', '.join(failed)}")
print("="*60 + "\n")
