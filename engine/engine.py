import json
import sqlite3
import os

DB_PATH = "../database/progress.db"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))



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

    #     CREATE TABLE IF NOT EXISTS content_versions (
    #     content_id TEXT PRIMARY KEY,
    #     version TEXT
    # );
    

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
    return os.path.join(
        BASE_DIR,
        "..",
        "content",
        "concepts",
        f"{concept_id}.json"
    )


def load_lesson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_lesson_index():
    index_path = os.path.join(
        BASE_DIR, "..", "content", "lessons", "index.json"
    )
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)



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

def main():
    if not os.path.exists("../database"):
        os.makedirs("../database")

    init_db()

    index = load_lesson_index()
    selected = select_lesson(index)

    lesson_path = os.path.join(
        BASE_DIR, "..", "content", "lessons", selected["path"]
    )
    lesson = load_lesson(lesson_path)
    lesson_id = lesson["lesson_id"]

    if get_lesson_status(lesson_id) == "completed":
        print(f"\nLesson '{lesson['title']}' already completed.\n")
        return

    print("\n=== Lesson Start ===\n")
    print(lesson["title"])
    print("\n" + lesson["intro"] + "\n")

    for concept_id in lesson["concepts"]:
        concept_path = get_concept_path(concept_id)
        concept = load_concept(concept_path)
        run_concept(concept)

    if is_lesson_completed(lesson["concepts"]):
        save_lesson_status(lesson_id, "completed")
        print("\n=== Lesson Complete ===\n")
        print(lesson["outro"])


if __name__ == "__main__":
    main()
