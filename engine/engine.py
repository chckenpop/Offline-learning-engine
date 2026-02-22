import json
import sqlite3
import os
import sys
import time
import shutil
from updater import run_update, preview_updates

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
PUNE_CONTENT_DIR = os.path.join(PROJECT_DIR, "pune_content")
DB_PATH = os.path.join(PUNE_CONTENT_DIR, "metadata.db")
LESSONS_DIR = os.path.join(PUNE_CONTENT_DIR, "lessons")
CONCEPTS_DIR = os.path.join(PUNE_CONTENT_DIR, "concepts")
# Optional: index.json is now legacy if we use the lessons folder directly, 
# but I'll keep the variable for compatibility if needed.


# -------------------- SIMPLE TERMINAL UI --------------------
def clear_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def term_width():
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def print_header(title):
    clear_screen()
    w = term_width()
    print("=" * w)
    print(title.center(w))
    print("=" * w)
    print()




# -------------------- DATABASE --------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Track concept completion
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            concept_id TEXT PRIMARY KEY,
            status TEXT
        )
    """)

    # Track lesson completion
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            lesson_id TEXT PRIMARY KEY,
            status TEXT
        )
    """)

    # Track installed content versions (Merged with updater's requirement)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cached_content (
            id TEXT NOT NULL,
            type TEXT NOT NULL,
            version INTEGER NOT NULL,
            PRIMARY KEY (id, type)
        )
    """)
    
    # Optional aliases mapping
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_aliases (
            alias TEXT PRIMARY KEY,
            canonical TEXT
        )
    """)
    
    conn.commit()
    conn.close()


def get_lesson_status(lesson_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT status FROM lessons WHERE lesson_id = ?",
        (lesson_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def save_lesson_status(lesson_id, status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO lessons (lesson_id, status)
        VALUES (?, ?)
    """, (lesson_id, status))
    conn.commit()
    conn.close()


def is_lesson_completed(concept_ids):
    for concept_id in concept_ids:
        if get_progress(concept_id) != "completed":
            return False
    return True



def get_progress(concept_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT status FROM progress WHERE concept_id = ?",
        (concept_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def save_progress(concept_id, status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO progress (concept_id, status)
        VALUES (?, ?)
    """, (concept_id, status))
    conn.commit()
    conn.close()


# -------------------- CONTENT --------------------

def load_concept(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def is_answer_correct(user_answer, keywords):
    user_answer = normalize(user_answer)
    return all(keyword in user_answer for keyword in keywords)

import re

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def get_concept_path(concept_id):
    # Resolve alias -> canonical id using DB mapping if present
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT canonical FROM content_aliases WHERE alias = ?', (concept_id,))
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            resolved = row[0]
        else:
            resolved = concept_id
    except Exception:
        resolved = concept_id

    return os.path.join(CONCEPTS_DIR, f"{resolved}.json")


def load_lesson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_lesson_index():
    # Dynamically build index from lessons folder if index.json is missing
    lessons = []
    if os.path.exists(LESSONS_DIR):
        for f in os.listdir(LESSONS_DIR):
            if f.endswith(".json"):
                 with open(os.path.join(LESSONS_DIR, f), "r", encoding="utf-8") as jf:
                     try:
                         data = json.load(jf)
                         lessons.append({
                             "lesson_id": data.get("id") or f.replace(".json", ""),
                             "title": data.get("title", f),
                             "path": f
                         })
                     except:
                         pass
    return {"lessons": lessons}



# -------------------- LEARNING LOOP --------------------

def run_concept(concept):
    concept_id = concept["id"]
    keywords = concept["check"]["keywords"]

    if get_progress(concept_id) == "completed":
        print(f"\nConcept '{concept_id}' already completed.\n")
        return

    print("\n--- Learning Concept ---\n")
    print(concept["explain"])
    print("\nExample:")
    print(concept["example"])

    print("\nQuestion:")
    user_answer = input(concept["check"]["question"] + "\n> ")




    if is_answer_correct(user_answer, keywords):
        print("\nCorrect!\n")
        save_progress(concept_id, "completed")
    else:
        print("\nIncorrect.")
        print("Expected answer:")
        print(concept["check"]["desired_answer"])
        print("Try again later.\n")
# -------------------- HELPER FUNCTIONS --------------------
def select_lesson(index):
    print("\nAvailable Lessons:\n")

    for i, lesson in enumerate(index["lessons"], start=1):
        status = get_lesson_status(lesson["lesson_id"]) or "not started"
        print(f"{i}. {lesson['title']} ({status})")

    while True:
        try:
            choice = int(input("\nSelect a lesson number: "))
            if 1 <= choice <= len(index["lessons"]):
                return index["lessons"][choice - 1]
        except ValueError:
            pass

        print("Invalid choice. Try again.")

def get_local_version(content_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT version FROM content_versions WHERE content_id = ?",
        (content_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def save_local_version(content_id, version):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO content_versions (content_id, version)
        VALUES (?, ?)
    """, (content_id, version))
    conn.commit()
    conn.close()



# -------------------- MAIN --------------------

def show_preview(preview):
    print_header("Smart Update Preview")
    c_new = preview['concepts']['new']
    c_update = preview['concepts']['update']
    c_skip = preview['concepts']['skip']

    l_new = preview['lessons']['new']
    l_update = preview['lessons']['update']
    l_skip = preview['lessons']['skip']

    def print_section(title, items):
        print(f"{title} ({len(items)})")
        for it in items:
            if 'installed' in it:
                print(f" - {it['id']}  (installed: {it['installed']} -> new: {it['version']})")
            else:
                print(f" - {it['id']}  (v{it.get('version')})")
        print()

    print_section("New Concepts", c_new)
    print_section("Updated Concepts", c_update)
    print_section("Skipped Concepts", c_skip)

    print_section("New Lessons", l_new)
    print_section("Updated Lessons", l_update)
    print_section("Skipped Lessons", l_skip)


def main():
    # Ensure database directory exists
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    init_db()

    while True:
        print_header("OFFLINE LEARNING ENGINE - MAIN MENU")
        print("1) Start Learning")
        print("2) Smart Update: Preview")
        print("3) Smart Update: Apply")
        print("4) Exit")

        choice = input("\nSelect option (1-4): ").strip()

        if choice == "1":
            try:
                index = load_lesson_index()
            except FileNotFoundError:
                print('\nNo lessons installed. Run Smart Update first.')
                input('Press Enter to continue...')
                continue

            selected = select_lesson(index)
            lesson_path = os.path.join(LESSONS_DIR, selected["path"])
            lesson = load_lesson(lesson_path)
            lesson_id = lesson["lesson_id"]

            if get_lesson_status(lesson_id) == "completed":
                print(f"\nLesson '{lesson['title']}' already completed.\n")
                input('Press Enter to continue...')
                continue

            print_header(f"Lesson: {lesson.get('title', lesson_id)}")
            print(lesson.get('intro', ''))
            for concept_id in lesson.get('concepts', []):
                concept_path = get_concept_path(concept_id)
                concept = load_concept(concept_path)
                run_concept(concept)

            if is_lesson_completed(lesson.get('concepts', [])):
                save_lesson_status(lesson_id, "completed")
                print("\n=== Lesson Complete ===\n")
                print(lesson.get("outro", ""))
            input('\nPress Enter to return to menu...')

        elif choice == "2":
            print_header("Smart Update: Preview")
            try:
                preview = preview_updates()
            except Exception:
                print('\n❌ Could not fetch preview. Check internet or config.')
                input('Press Enter to continue...')
                continue
            show_preview(preview)
            input('Press Enter to return to menu...')

        elif choice == "3":
            print_header("Smart Update: Apply")
            print('Running update now...')
            run_update()
            input('Press Enter to return to menu...')

        elif choice == "4":
            print('Goodbye')
            break
        else:
            print('Invalid choice. Please select 1-4.')
            time.sleep(0.6)

if __name__ == "__main__":
    main()
