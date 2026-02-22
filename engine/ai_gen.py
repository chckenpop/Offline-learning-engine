import requests
import json
import os

# Configuration from User
# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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").strip()
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-3.5-turbo"

class AIGenService:
    @staticmethod
    def generate_adaptive_lesson(original_lesson, mode):
        """
        Generates a new lesson JSON based on the original lesson and the requested mode.
        Modes: 'Beginner' (Simplified) or 'Advance' (Challenging)
        """
        
        prompt = f"""
        You are an expert tutor. I will give you a JSON representation of a lesson.
        Your task is to generate a new version of this lesson intended for a student in '{mode}' mode.

        RULES for 'Beginner':
        1. Simplify explanations. Use analogies and very clear language.
        2. Focus on foundational concepts.
        3. Make questions easier but still testing core concepts.
        4. Append ' (Beginner)' to the title.
        5. Keywords must be in lowercase.

        RULES for 'Advance':
        1. Add deeper technical details or more complex applications.
        2. Introduce 1-2 new, related 'Advanced Concepts'.
        3. Make questions significantly more challenging (multi-step or critical thinking).
        4. Append ' (Advance)' to the title.
        5. Keywords must be in lowercase.

        OUTPUT FORMAT:
        Return ONLY valid JSON. The structure must match exactly:
        {{
            "title": "...",
            "intro": "...",
            "outro": "...",
            "concepts": [
                {{
                    "id": "concept_unique_id",
                    "name": "Concept Name",
                    "explain": "...",
                    "example": "...",
                    "check": {{
                        "question": "...",
                        "desired_answer": "...",
                        "keywords": ["lowercase_key1", "lowercase_key2"]
                    }}
                }}
            ]
        }}

        ORIGINAL LESSON JSON:
        {json.dumps(original_lesson, indent=2)}
        """

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://bright-study1.onrender.com/",
            "Referer": "https://bright-study1.onrender.com/",
            "X-Title": "Bright Study Offline",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are a specialized educational content generator. You output only structured JSON."},
                {"role": "user", "content": prompt}
            ]
        }

        try:
            response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            
            # Clean possible markdown wrap
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
        except Exception as e:
            print(f"❌ AI Generation Error: {e}")
            return None
