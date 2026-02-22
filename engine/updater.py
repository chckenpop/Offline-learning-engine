import requests
import sqlite3
import json
import os
import shutil

# ==============================
# 🔑 CONFIG (ADD YOUR KEYS HERE)
# ==============================

SUPABASE_URL = "https://njqlzvelsatdwzwynyek.supabase.co"
SUPABASE_KEY = "sb_publishable_NOFcz2mruM_oYS8NaKWlIg_lrXZqXEM"

LESSONS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/delivery_lessons"
CONCEPTS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/delivery_concepts"
VIDEOS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/videos"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ==============================
# 📁 NEW DIRECTORY STRUCTURE (Sync-to-Edge)
# ==============================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUNE_CONTENT_DIR = os.path.join(BASE_DIR, "pune_content")
LESSONS_DIR = os.path.join(PUNE_CONTENT_DIR, "lessons")
CONCEPTS_DIR = os.path.join(PUNE_CONTENT_DIR, "concepts")
ASSETS_DIR = os.path.join(PUNE_CONTENT_DIR, "assets")
THUMBNAILS_DIR = os.path.join(ASSETS_DIR, "thumbnails")
VIDEOS_DIR = os.path.join(ASSETS_DIR, "videos")
DB_PATH = os.path.join(PUNE_CONTENT_DIR, "metadata.db")

# Ensure directories exist
for d in [LESSONS_DIR, CONCEPTS_DIR, THUMBNAILS_DIR, VIDEOS_DIR]:
    os.makedirs(d, exist_ok=True)

# ==============================
# 🗄️ DB FUNCTIONS
# ==============================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    # Ensure tables exist according to the new spec (tracking versions)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cached_content (
            id TEXT NOT NULL,
            type TEXT NOT NULL,
            version INTEGER NOT NULL,
            PRIMARY KEY (id, type)
        )
    """)
    conn.commit()
    return conn

def get_installed_version(content_id, ctype):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT version FROM cached_content WHERE id=? AND type=?", (content_id, ctype))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def upsert_installed(content_id, ctype, version):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO cached_content (id, type, version) VALUES (?, ?, ?)", 
                (content_id, ctype, version))
    conn.commit()
    conn.close()

# ==============================
# 📥 SYNC HELPERS
# ==============================

def download_file(url, dest_path, expected_size=None):
    """Download a file with verification and cleanup on failure."""
    print(f"  ⬇️ Downloading: {url}")
    temp_path = dest_path + ".tmp"
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(temp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        # Verification
        if expected_size:
            # expected_size might be a string like "15.4 MB" or an int
            actual_size = os.path.getsize(temp_path)
            # Rough conversion if it's a string, or just skip if we don't want to parse it now
            # For now, if it's an int, compare directly.
            if isinstance(expected_size, int) and actual_size != expected_size:
                 raise Exception(f"Size mismatch: expected {expected_size}, got {actual_size}")
        
        os.replace(temp_path, dest_path)
        return True
    except Exception as e:
        print(f"  ⚠️ Download failed: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ==============================
# 🚀 SYNC PROTOCOL
# ==============================

def sync_video(video_id):
    print(f"  🔍 Fetching independent Video: {video_id}")
    try:
        res = requests.get(f"{VIDEOS_ENDPOINT}?id=eq.{video_id}", headers=HEADERS)
        res.raise_for_status()
        if not res.json():
            print(f"  ❌ Video {video_id} not found.")
            return False
        
        v_data = res.json()[0]
        video_url = v_data.get('url')
        thumb_url = v_data.get('thumbnail_url')
        
        if not video_url:
            print(f"  ❌ Video {video_id} has no URL.")
            return False

        all_assets_success = True
        
        # Determine extension and download video
        ext = ".mp4" if ".mp4" in video_url.lower() else ".mp4"
        video_path = os.path.join(VIDEOS_DIR, f"{video_id}{ext}")
        if not os.path.exists(video_path):
            success = download_file(video_url, video_path)
            if not success: all_assets_success = False

        # Download thumbnail if present
        if thumb_url:
            t_ext = ".jpg" if ".jpg" in thumb_url.lower() else ".png"
            thumb_path = os.path.join(THUMBNAILS_DIR, f"{video_id}{t_ext}")
            if not os.path.exists(thumb_path):
                t_success = download_file(thumb_url, thumb_path)
                if t_success:
                    v_data['local_thumb'] = f"assets/thumbnails/{video_id}{t_ext}"
        
        if all_assets_success:
            v_data['local_video'] = f"assets/videos/{video_id}{ext}"
            save_json(os.path.join(VIDEOS_DIR, f"{video_id}.json"), v_data)
            print(f"  ✅ Video {video_id} fully synced.")
            return True
        return False
    except Exception as e:
        print(f"  ❌ Failed to fetch Video {video_id}: {e}")
        return False


def sync_concept(concept_id, remote_version=1):
    print(f"  🔍 Fetching independent Concept: {concept_id}")
    try:
        c_res = requests.get(f"{CONCEPTS_ENDPOINT}?id=eq.{concept_id}&select=json_data,version", headers=HEADERS)
        c_res.raise_for_status()
        c_data = c_res.json()[0]
        concept = c_data['json_data']
        if isinstance(concept, str):
            concept = json.loads(concept)
        concept['id'] = concept_id
        concept['version'] = c_data.get('version') or 1

        # Check if concept needs update
        if get_installed_version(concept_id, 'concept') != concept['version']:
            print(f"  📝 Syncing Concept: {concept_id} (v{concept['version']})")
            save_json(os.path.join(CONCEPTS_DIR, f"{concept_id}.json"), concept)

        all_assets_success = True
        videos = concept.get('videos', [])
        for video in videos:
            video_id = video.get('id')
            video_url = video.get('url')
            if not video_url: continue
            
            ext = ".mp4" if ".mp4" in video_url.lower() else ".mp4"
            video_path = os.path.join(VIDEOS_DIR, f"{video_id}{ext}")
            
            if not os.path.exists(video_path):
                success = download_file(video_url, video_path)
                if not success:
                    all_assets_success = False

        if all_assets_success:
            upsert_installed(concept_id, 'concept', concept['version'])
            return True
        return False
    except Exception as e:
        print(f"  ❌ Failed to fetch Concept {concept_id}: {e}")
        return False

def sync_lesson(lesson_id, remote_version):
    print(f"📦 Fetching payload for Lesson: {lesson_id} (v{remote_version})")
    try:
        res = requests.get(f"{LESSONS_ENDPOINT}?lesson_id=eq.{lesson_id}&select=json_data", headers=HEADERS)
        res.raise_for_status()
        row = res.json()[0]
        payload_data = row['json_data']
        
        if isinstance(payload_data, str):
            payload_data = json.loads(payload_data)
        
        # order_index might be inside json_data, if not we default to 0
        if 'order_index' not in payload_data:
            payload_data['order_index'] = 0
        
        save_json(os.path.join(LESSONS_DIR, f"{lesson_id}.json"), payload_data)
        
        concepts_data = payload_data.get('concepts', [])
        all_assets_success = True
        
        for c_entry in concepts_data:
            concept = None
            if isinstance(c_entry, dict):
                concept = c_entry
            else:
                success = sync_concept(c_entry)
                if not success:
                    all_assets_success = False
                continue

            concept_id = concept.get('id')
            concept_version = concept.get('version') or 1
            
            if get_installed_version(concept_id, 'concept') != concept_version:
                print(f"  📝 Syncing Concept: {concept_id} (v{concept_version})")
                save_json(os.path.join(CONCEPTS_DIR, f"{concept_id}.json"), concept)
            
            videos = concept.get('videos', [])
            for video in videos:
                video_id = video.get('id')
                video_url = video.get('url')
                if not video_url: continue
                
                ext = ".mp4" if ".mp4" in video_url.lower() else ".mp4"
                video_path = os.path.join(VIDEOS_DIR, f"{video_id}{ext}")
                
                if not os.path.exists(video_path):
                    success = download_file(video_url, video_path)
                    if not success:
                        all_assets_success = False

            if all_assets_success:
                upsert_installed(concept_id, 'concept', concept_version)

        if all_assets_success:
            upsert_installed(lesson_id, 'lesson', remote_version)
            print(f"🌸 Lesson '{payload_data.get('title')}' fully synced.")
        else:
            print(f"⚠️ Lesson '{payload_data.get('title')}' partially synced. Retrying next time.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Failed to sync Lesson {lesson_id}: {e}")

def run_update():
    print("\n🔄 Background Sync Protocol Started\n")
    try:
        res = requests.get(LESSONS_ENDPOINT + "?select=lesson_id,version", headers=HEADERS)
        res.raise_for_status()
        remote_lessons = res.json()
    except Exception as e:
        print(f"❌ Discovery Phase failed: {e}")
        return

    for rl in remote_lessons:
        lesson_id = rl['lesson_id']
        remote_version = rl.get('version') or 1
        local_version = get_installed_version(lesson_id, 'lesson')

        # LAZY LOADING: Only sync if already installed locally and needs update
        if local_version is None:
            continue
        if local_version == remote_version:
            continue
        
        sync_lesson(lesson_id, remote_version)

    print("\n✅ Background Sync complete.\n")

def download_specific_item(item_id, item_type):
    print(f"\n📥 On-Demand Download started for {item_type}: {item_id}\n")
    if item_type.lower() == 'lesson':
        try:
            res = requests.get(f"{LESSONS_ENDPOINT}?lesson_id=eq.{item_id}&select=version", headers=HEADERS)
            if res.ok and len(res.json()) > 0:
                rv = res.json()[0].get('version') or 1
                sync_lesson(item_id, rv)
            else:
                print(f"❌ Lesson {item_id} not found in cloud.")
        except Exception as e:
            print(f"❌ Failed to initiate specific lesson sync: {e}")
    elif item_type.lower() == 'concept':
        sync_concept(item_id)
    elif item_type.lower() == 'video':
        sync_video(item_id)

def preview_updates():
    """Simple implementation of preview using local state."""
    try:
        res = requests.get(LESSONS_ENDPOINT + "?select=lesson_id,version", headers=HEADERS)
        res.raise_for_status()
        remote_lessons = res.json()
    except Exception:
        return None

    result = {'lessons': {'new': [], 'update': [], 'skip': []}}
    for rl in remote_lessons:
        lid = rl['lesson_id']
        rv = rl['version']
        lv = get_installed_version(lid, 'lesson')
        
        if not lv:
            result['lessons']['new'].append({'id': lid, 'version': rv})
        elif lv != rv:
            result['lessons']['update'].append({'id': lid, 'version': rv, 'installed': lv})
        else:
            result['lessons']['skip'].append({'id': lid, 'version': rv})
    
    return result

if __name__ == "__main__":
    run_update()
