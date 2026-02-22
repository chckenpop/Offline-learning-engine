import os
import json
import sqlite3
from dotenv import load_dotenv

# Try to load openai, but handle if it's not installed yet in some environments
try:
    import openai
except ImportError:
    openai = None

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', '.env')
load_dotenv(dotenv_path=env_path)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo").strip()

class AITutorService:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()
        self.client = None
        if openai and OPENROUTER_API_KEY:
            self.client = openai.OpenAI(
                api_key=OPENROUTER_API_KEY,
                base_url=OPENROUTER_API_URL
            )
            key_preview = OPENROUTER_API_KEY[:8] + "..." if OPENROUTER_API_KEY else "None"
            print(f"🤖 AITutorService initialized with OpenRouter. Key preview: {key_preview}")
        else:
            print("⚠️ AITutorService: OpenRouter API key or package not found. AI Tutor will be disabled or mock responses.")

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
        Process a chat message. 
        lesson_context is a snippet of text from the currently viewed lesson.
        file_text is the content of any uploaded text document.
        """
        # Save user message
        self._save_message(user_id, "user", prompt)

        if not self.client:
            # Fallback if no API key
            fallback_msg = "Please set up your OpenRouter API key in the .env file to use the AI Tutor."
            self._save_message(user_id, "assistant", fallback_msg)
            return fallback_msg

        # Retrieve prior history
        # To save tokens, we might want to truncate this in a real high-volume app, but we'll fetch all for now
        history = self.get_history(user_id)

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

        # Construct messages payload for OpenAI
        messages = [{"role": "system", "content": system_msg}]
        
        # Append history (ensure we only pass recent context to limit tokens)
        MAX_HISTORY_TOKENS_APPROX = 20 # Roughly 20 messages max
        recent_history = history[-(MAX_HISTORY_TOKENS_APPROX):] 
        # Don't duplicate the user's latest prompt we just appended to DB
        for msg in recent_history[:-1]:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        # Add the actual latest prompt
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=600,
                extra_headers={
                    "HTTP-Referer": "https://bright-study1.onrender.com",
                    "X-Title": "Bright Study"
                }
            )
            
            ai_reply = response.choices[0].message.content.strip()
            
            # Save AI response
            self._save_message(user_id, "assistant", ai_reply)
            
            return ai_reply
            
        except Exception as e:
            error_msg = f"Sorry, I encountered an error connecting to my brain. Error: {str(e)}"
            self._save_message(user_id, "assistant", error_msg)
            return error_msg
