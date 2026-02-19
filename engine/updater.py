import requests
import sqlite3
import json
import os

# ==============================
# 🔑 CONFIG (ADD YOUR KEYS HERE)
# ==============================

SUPABASE_URL = "https://njqlzvelsatdwzwynyek.supabase.co"
SUPABASE_KEY = "sb_publishable_NOFcz2mruM_oYS8NaKWlIg_lrXZqXEM"

LESSONS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/delivery_lessons"
CONCEPTS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/delivery_concepts"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ==============================
# 📁 PATHS
# ==============================

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONTENT_DIR = os.path.join(BASE_DIR, "content")
LESSONS_DIR = os.path.join(CONTENT_DIR, "lessons")
CONCEPTS_DIR = os.path.join(CONTENT_DIR, "concepts")
DB_PATH = os.path.join(BASE_DIR, "database", "progress.db")
INDEX_FILE = os.path.join(LESSONS_DIR, "index.json")


# ==============================
# 🗄️ DB FUNCTIONS
# ==============================

def get_db():
    return sqlite3.connect(DB_PATH)


def get_installed_version(content_id, ctype):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT version FROM installed_content
        WHERE content_id=? AND type=?
    """, (content_id, ctype))

    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def upsert_installed(content_id, ctype, version):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO installed_content(content_id, type, version)
        VALUES (?, ?, ?)
    """, (content_id, ctype, version))

    conn.commit()
    conn.close()


# ==============================
# 📥 FETCH FROM SUPABASE
# ==============================

def fetch_lessons():
    res = requests.get(
        LESSONS_ENDPOINT + "?select=lesson_id,version,json_data",
        headers=HEADERS
    )
    res.raise_for_status()
    return res.json()


def fetch_concepts():
    res = requests.get(
        CONCEPTS_ENDPOINT + "?select=id,version,json_data",
        headers=HEADERS
    )
    res.raise_for_status()
    return res.json()


def fetch_concept_detail(concept_id, current_version=None):
    """Fetch single concept detail using delivery endpoint.

    Expected response JSON keys:
      - concept: full concept JSON
      - delivery_version: server version
      - update_available: bool (if current_version provided)
      - contract_version
    """
    url = f"{SUPABASE_URL}/delivery/concepts/{concept_id}"
    params = {}
    if current_version:
        params['current_version'] = current_version

    res = requests.get(url, headers=HEADERS, params=params)
    # If endpoint not available or error, fall back to fetching all and filtering
    if res.status_code != 200:
        # fallback: try to find in bulk list
        try:
            all_concepts = fetch_concepts()
            for c in all_concepts:
                if c.get('id') == concept_id:
                    return {
                        'concept': c.get('json_data'),
                        'delivery_version': c.get('version'),
                        'update_available': (current_version != c.get('version')) if current_version is not None else True,
                        'contract_version': 'v1'
                    }
        except Exception:
            res.raise_for_status()

    res.raise_for_status()
    return res.json()


def preview_updates():
    """Return a preview dict of what would be downloaded/updated/skipped.

    Structure:
    {
      'concepts': {'new': [id], 'update': [id], 'skip': [id]},
      'lessons': {'new': [id], 'update': [id], 'skip': [id]}
    }
    """
    try:
        lessons = fetch_lessons()
        concepts = fetch_concepts()
    except Exception as e:
        raise

    result = {'concepts': {'new': [], 'update': [], 'skip': []},
              'lessons': {'new': [], 'update': [], 'skip': []}}

    for c in concepts:
        cid = c['id']
        version = c.get('version')
        installed = get_installed_version(cid, 'concept')

        if not installed:
            result['concepts']['new'].append({'id': cid, 'version': version})
        elif installed == version:
            result['concepts']['skip'].append({'id': cid, 'version': version})
        else:
            result['concepts']['update'].append({'id': cid, 'version': version, 'installed': installed})

    for l in lessons:
        lid = l['lesson_id']
        version = l.get('version')
        installed = get_installed_version(lid, 'lesson')

        if not installed:
            result['lessons']['new'].append({'id': lid, 'version': version})
        elif installed == version:
            result['lessons']['skip'].append({'id': lid, 'version': version})
        else:
            result['lessons']['update'].append({'id': lid, 'version': version, 'installed': installed})

    return result


# ==============================
# 📁 FILE INSTALL HELPERS
# ==============================

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def update_index(lesson_id, title):
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = {"lessons": []}

    # remove existing
    index["lessons"] = [l for l in index["lessons"] if l["lesson_id"] != lesson_id]

    index["lessons"].append({
        "lesson_id": lesson_id,
        "title": title,
        "path": f"{lesson_id}.json"
    })

    save_json(INDEX_FILE, index)


# ==============================
# 🚀 MAIN UPDATE FUNCTION
# ==============================

def run_update():
    print("\n🔄 Checking for updates...\n")

    try:
        lessons = fetch_lessons()
        concepts = fetch_concepts()
    except Exception:
        print("❌ No internet or Supabase unreachable.\n")
        return

    new_count = 0
    update_count = 0
    skip_count = 0

    # --------------------------
    # 📦 INSTALL CONCEPTS FIRST (per-concept endpoint)
    # --------------------------
    for c in concepts:
        cid = c.get("id")
        installed = get_installed_version(cid, "concept")

        try:
            detail = fetch_concept_detail(cid, current_version=installed)
        except Exception:
            # fallback to bulk payload if per-concept endpoint fails
            version = c.get("version")
            data = c.get("json_data")
            if not installed:
                action = "new"
            elif installed == version:
                skip_count += 1
                continue
            else:
                action = "update"

            path = os.path.join(CONCEPTS_DIR, f"{cid}.json")
            save_json(path, data)
            upsert_installed(cid, "concept", version)

            if action == "new":
                new_count += 1
                print(f"📦 Installed concept: {cid}")
            else:
                update_count += 1
                print(f"♻️ Updated concept: {cid}")
            continue

        # detail expected shape: {'concept':..., 'delivery_version':..., 'update_available':bool}
        if isinstance(detail, dict) and 'concept' in detail:
            data = detail['concept']
            delivery_version = detail.get('delivery_version') or detail.get('version')
            update_available = detail.get('update_available', True)
        else:
            # unexpected shape; try to use bulk record
            data = c.get('json_data')
            delivery_version = c.get('version')
            update_available = (installed != delivery_version)

        if not installed:
            action = 'new'
        elif not update_available:
            skip_count += 1
            continue
        else:
            action = 'update'

        path = os.path.join(CONCEPTS_DIR, f"{cid}.json")
        save_json(path, data)
        upsert_installed(cid, 'concept', delivery_version)

        if action == 'new':
            new_count += 1
            print(f"📦 Installed concept: {cid}")
        else:
            update_count += 1
            print(f"♻️ Updated concept: {cid}")

    # --------------------------
    # 📦 INSTALL LESSONS
    # --------------------------
    for l in lessons:
        lid = l["lesson_id"]
        version = l["version"]
        data = l["json_data"]

        installed = get_installed_version(lid, "lesson")

        if not installed:
            action = "new"
        elif installed == version:
            skip_count += 1
            continue
        else:
            action = "update"

        path = os.path.join(LESSONS_DIR, f"{lid}.json")
        save_json(path, data)
        upsert_installed(lid, "lesson", version)

        update_index(lid, data.get("title", lid))

        if action == "new":
            new_count += 1
            print(f"📘 Installed lesson: {lid}")
        else:
            update_count += 1
            print(f"♻️ Updated lesson: {lid}")

    print("\n✅ Update complete")
    print(f"New: {new_count}")
    print(f"Updated: {update_count}")
    print(f"Skipped: {skip_count}\n")
