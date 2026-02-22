import os
import json
import sqlite3
import requests

# Load environment variables for local development
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', '.env')
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv(override=True)
except Exception:
    pass

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
# Clean up accidental copy-paste errors
if OPENROUTER_API_KEY.startswith("sk or v1"):
    OPENROUTER_API_KEY = "sk-or-v1" + OPENROUTER_API_KEY[8:]
OPENROUTER_API_KEY = OPENROUTER_API_KEY.replace(" ", "")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free").strip()

# Log on startup
if OPENROUTER_API_KEY and len(OPENROUTER_API_KEY) > 10:
    key_preview = f"{OPENROUTER_API_KEY[:6]}...{OPENROUTER_API_KEY[-4:]}"
    print(f"🤖 [AI Tutor] Initialized with key: {key_preview} (Length: {len(OPENROUTER_API_KEY)})")
    print(f"🤖 [AI Tutor] Using Model: {OPENROUTER_MODEL}")
else:
    print(f"⚠️ [AI Tutor] No valid OPENROUTER_API_KEY found. Check backend/.env")

import sys
sys.stdout.flush()


class AITutorService:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize a local SQLite table for chat history per user."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS ai_tutor_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error initializing AI Tutor DB: {e}")

    def get_history(self, user_id):
        """Retrieve the chat history for a given user."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('SELECT role, content FROM ai_tutor_history WHERE user_id = ? ORDER BY timestamp ASC', (user_id,))
            rows = cur.fetchall()
            conn.close()
            return [{"role": r[0], "content": r[1]} for r in rows]
        except Exception as e:
            print(f"Error getting history: {e}")
            return []

    def _save_message(self, user_id, role, content):
        """Save a single message to the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('INSERT INTO ai_tutor_history (user_id, role, content) VALUES (?, ?, ?)', (user_id, role, content))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving message: {e}")

    def chat(self, user_id, prompt, lesson_context=None, file_text=None):
        """
        Process a chat message using the requests library (bypasses openai SDK issues).
        lesson_context is a snippet of text from the currently viewed lesson.
        file_text is the content of any uploaded text document.
        """
        # Save user message
        self._save_message(user_id, "user", prompt)

        if not OPENROUTER_API_KEY:
            fallback_msg = "⚠️ AI Tutor is not configured. Please set OPENROUTER_API_KEY in backend/.env"
            self._save_message(user_id, "assistant", fallback_msg)
            return fallback_msg

        # Build system prompt dynamically based on context
        system_msg = (
            "You are a helpful, intelligent, and patient AI Tutor designed for an offline learning platform. "
            "Your goal is to answer student questions clearly and concisely, helping them clear their doubts. "
            "Respond in a friendly, encouraging tone. Do not give away direct answers immediately if prompted for homework; guide the student instead.\n\n"
        )

        if lesson_context:
            system_msg += f"The student is currently looking at this lesson content:\n\"\"\"{lesson_context}\"\"\"\nBase your answer heavily on this context.\n"

        if file_text:
            system_msg += f"The student has uploaded a document with the following text to provide context:\n\"\"\"{file_text}\"\"\"\nUse this to help answer their question.\n"

        # Retrieve prior history
        history = self.get_history(user_id)

        # Build messages list
        messages = [{"role": "system", "content": system_msg}]

        # Append recent history (excluding the message we just saved)
        MAX_HISTORY = 20
        recent_history = history[-(MAX_HISTORY):]
        for msg in recent_history[:-1]:  # exclude the last user message we just added
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add the latest prompt
        messages.append({"role": "user", "content": prompt})

        # Use requests library directly — same as ai_gen.py, avoids openai SDK issues
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://bright-study1.onrender.com",
            "X-Title": "Bright Study",
            "Content-Type": "application/json"
        }

        payload = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 600
        }

        print(f"📡 [AI Tutor] Sending request → model: {OPENROUTER_MODEL}")
        sys.stdout.flush()

        try:
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=30
            )

            print(f"📬 [AI Tutor] Response status: {response.status_code}")
            sys.stdout.flush()

            if response.status_code != 200:
                error_detail = response.text
                print(f"❌ [AI Tutor] Error from OpenRouter: {error_detail}")
                sys.stdout.flush()
                error_msg = f"Sorry, I encountered an error. Error: {response.status_code} - {error_detail}"
                self._save_message(user_id, "assistant", error_msg)
                return error_msg

            data = response.json()
            ai_reply = data["choices"][0]["message"]["content"].strip()

            # Save AI response
            self._save_message(user_id, "assistant", ai_reply)
            print(f"✅ [AI Tutor] Got reply ({len(ai_reply)} chars)")
            sys.stdout.flush()
            return ai_reply

        except requests.exceptions.Timeout:
            error_msg = "Sorry, the AI took too long to respond. Please try again."
            self._save_message(user_id, "assistant", error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Sorry, I encountered an error connecting to my brain. Error: {str(e)}"
            self._save_message(user_id, "assistant", error_msg)
            return error_msg
