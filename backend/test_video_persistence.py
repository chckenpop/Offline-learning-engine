import requests
import os

# ==============================
# 🔑 CONFIG
# ==============================
SUPABASE_URL = "https://njqlzvelsatdwzwynyek.supabase.co"
SUPABASE_KEY = "sb_publishable_NOFcz2mruM_oYS8NaKWlIg_lrXZqXEM" # Using public key from updater.py
STORAGE_URL = f"{SUPABASE_URL}/storage/v1/object/public/videos"
LESSONS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/delivery_lessons"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

def test_supabase_connectivity():
    print("🔍 Testing Supabase connectivity...")
    try:
        res = requests.get(LESSONS_ENDPOINT, headers=HEADERS)
        res.raise_for_status()
        print("✅ Supabase REST API is accessible.")
        lessons = res.json()
        print(f"📊 Found {len(lessons)} lessons in delivery_lessons.")
        return lessons
    except Exception as e:
        print(f"❌ Supabase REST API error: {e}")
        return None

def test_video_accessibility(lessons):
    if not lessons:
        print("⚠️ No lessons to test for videos.")
        return

    print("\n🔍 Testing video accessibility...")
    for lesson in lessons:
        payload = lesson.get('payload', {})
        concepts = payload.get('concepts', [])
        for concept in concepts:
            videos = concept.get('videos', [])
            for video in videos:
                url = video.get('url')
                if not url:
                    continue
                
                print(f"📁 Testing video: {video.get('id')} - {url}")
                try:
                    res = requests.head(url)
                    if res.status_code == 200:
                        size = res.headers.get('Content-Length')
                        print(f"  ✅ Accessible. Size: {size} bytes.")
                        
                        # Verify against metadata if available
                        meta_size = video.get('metadata', {}).get('size')
                        if meta_size:
                             print(f"  ℹ️ Metadata size: {meta_size}")
                    else:
                        print(f"  ❌ Error: Status code {res.status_code}")
                except Exception as e:
                    print(f"  ❌ Fetch error: {e}")

if __name__ == "__main__":
    lessons = test_supabase_connectivity()
    if lessons:
        test_video_accessibility(lessons)
