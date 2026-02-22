"""
Quick test script to verify OpenRouter API key works.
Run from the engine folder: python test_openrouter.py
"""
import os
import requests

try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', '.env')
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=True)
        print(f"✅ Loaded .env from: {env_path}")
    else:
        print(f"⚠️  .env not found at: {env_path}")
        load_dotenv(override=True)
except Exception as e:
    print(f"⚠️  dotenv error: {e}")

API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free").strip()

print(f"\n🔑 Key: {API_KEY[:10]}...{API_KEY[-6:] if len(API_KEY) > 16 else '(too short)'}")
print(f"📊 Key Length: {len(API_KEY)}")
print(f"🤖 Model: {MODEL}")

if not API_KEY:
    print("\n❌ ERROR: No API key found! Check backend/.env file.")
    exit(1)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "HTTP-Referer": "https://bright-study1.onrender.com",
    "X-Title": "Bright Study",
    "Content-Type": "application/json"
}

payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": "Say 'AI is working!' in exactly 5 words."}],
    "max_tokens": 50
}

print(f"\n📡 Sending test request to OpenRouter...")
print(f"   URL: https://openrouter.ai/api/v1/chat/completions")
print(f"   Headers: {headers}")

try:
    res = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=20
    )
    print(f"\n📬 Status Code: {res.status_code}")
    print(f"📄 Raw Response: {res.text}")

    if res.status_code == 200:
        data = res.json()
        reply = data["choices"][0]["message"]["content"]
        print(f"\n✅ SUCCESS! AI replied: {reply}")
    else:
        print(f"\n❌ FAILED with status {res.status_code}")
except Exception as e:
    print(f"\n❌ Exception: {e}")
