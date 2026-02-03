import json
import sqlite3
import os

DB_PATH = "../database/progress.db"
CONTENT_PATH = "../content/concepts/fraction-definition.json"


# -------------------- DATABASE --------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            concept_id TEXT PRIMARY KEY,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()


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


# -------------------- LEARNING LOOP --------------------

def run_concept(concept):
    concept_id = concept["id"]

    if get_progress(concept_id) == "completed":
        print(f"\nConcept '{concept_id}' already completed.\n")
        return

    print("\n--- Learning Concept ---\n")
    print(concept["explain"])
    print("\nExample:")
    print(concept["example"])

    print("\nQuestion:")
    user_answer = input(concept["check"]["question"] + "\n> ").strip().lower()

    correct_answer = concept["check"]["answer"].strip().lower()

    if user_answer == correct_answer:
        print("\nCorrect!\n")
        save_progress(concept_id, "completed")
    else:
        print("\nIncorrect.")
        print("Correct answer:", concept["check"]["answer"])
        print("Try again later.\n")


# -------------------- MAIN --------------------

def main():
    if not os.path.exists("../database"):
        os.makedirs("../database")

    init_db()

    concept = load_concept(CONTENT_PATH)
    run_concept(concept)


if __name__ == "__main__":
    main()
