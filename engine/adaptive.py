import requests
import json
import os
import sqlite3
from datetime import datetime

# BKT Constants (Standard Defaults)
LEARNING_RATE = 0.2  # P(T) - Probability of transition from unlearned to learned
SLIP_RATE = 0.1      # P(S) - Probability of answering incorrectly despite knowing
GUESS_RATE = 0.2     # P(G) - Probability of answering correctly without knowing

class BKTModel:
    @staticmethod
    def update_mastery(p_old, is_correct):
        """
        Updates the probability of knowledge based on a single interaction.
        Formula:
        P(Known|Result) = P(Known|Result) / [P(Known)*P(Result|Known) + P(Unknown)*P(Result|Unknown)]
        """
        if is_correct:
            # P(Result|Known) = 1 - Slip
            # P(Result|Unknown) = Guess
            p_known_given_result = (p_old * (1 - SLIP_RATE)) / (p_old * (1 - SLIP_RATE) + (1 - p_old) * GUESS_RATE)
        else:
            # P(Result|Known) = Slip
            # P(Result|Unknown) = 1 - Guess
            p_known_given_result = (p_old * SLIP_RATE) / (p_old * SLIP_RATE + (1 - p_old) * (1 - GUESS_RATE))
        
        # Transition to new state (learned)
        p_new = p_known_given_result + (1 - p_known_given_result) * LEARNING_RATE
        return min(max(p_new, 0.0), 1.0)

    @staticmethod
    def simple_update(p_old, result, learning_rate=0.2):
        """Alternative simple update: P_new = P_old + LR * (result - P_old)"""
        p_new = p_old + learning_rate * (float(result) - p_old)
        return min(max(p_new, 0.0), 1.0)

class AdaptiveService:
    def __init__(self, supabase_url, supabase_key):
        self.url = supabase_url
        self.headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        # Local fallback DB
        self.local_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pune_content", "adaptive_mastery.db")
        self._init_local_db()

    def _init_local_db(self):
        conn = sqlite3.connect(self.local_db)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS local_mastery (
                user_id TEXT,
                concept_id TEXT,
                mastery_probability REAL,
                last_updated TEXT,
                PRIMARY KEY (user_id, concept_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id TEXT,
                item_id TEXT,
                item_type TEXT,
                status TEXT,
                last_updated TEXT,
                PRIMARY KEY (user_id, item_id)
            )
        """)
        conn.commit()
        conn.close()

    def _save_local(self, user_id, concept_id, mastery):
        conn = sqlite3.connect(self.local_db)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO local_mastery (user_id, concept_id, mastery_probability, last_updated)
            VALUES (?, ?, ?, ?)
        """, (str(user_id), str(concept_id), mastery, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def _get_local(self, user_id, concept_id):
        conn = sqlite3.connect(self.local_db)
        cur = conn.cursor()
        cur.execute("SELECT mastery_probability FROM local_mastery WHERE user_id=? AND concept_id=?", (str(user_id), str(concept_id)))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else 0.1

    def get_mastery(self, user_id, concept_id):
        try:
            res = requests.get(
                f"{self.url}/rest/v1/delivery_user_profiles?user_id=eq.{user_id}&concept_id=eq.{concept_id}&select=mastery_probability",
                headers=self.headers,
                timeout=2
            )
            if res.ok and res.json():
                mastery = res.json()[0]['mastery_probability']
                self._save_local(user_id, concept_id, mastery)
                return mastery
        except Exception as e:
            print(f"📡 [Adaptive] Cloud unavailable, switching to Local storage.")
        
        return self._get_local(user_id, concept_id)

    def log_interaction(self, event):
        print(f"🚀 [Adaptive] Logging interaction: {event.get('event_type')}")
        
        # 1. Try to Save Log to Cloud
        try:
            log_res = requests.post(
                f"{self.url}/rest/v1/delivery_interaction_logs",
                headers=self.headers,
                json=event,
                timeout=2
            )
            if not log_res.ok:
                print(f"⚠️ [Adaptive] Cloud Log failed: {log_res.text}")
        except Exception:
            print(f"📡 [Adaptive] Offline: Interaction log saved locally only (concept mastery update will follow).")

        # 2. Update Mastery for questions
        if event.get('event_type') == 'answer' and 'concept_id' in event:
            user_id = event['user_id']
            concept_id = event['concept_id']
            is_correct = event.get('correct', False)
            
            p_old = self.get_mastery(user_id, concept_id)
            p_new = BKTModel.simple_update(p_old, is_correct)
            
            # 1. Always Save Locally First (Offline-Ready)
            self._save_local(user_id, concept_id, p_new)

            # 2. Try to sync to Supabase
            try:
                upsert_payload = {
                    "user_id": str(user_id),
                    "concept_id": str(concept_id),
                    "mastery_probability": p_new,
                    "last_updated": "now()"
                }
                
                m_res = requests.post(
                    f"{self.url}/rest/v1/delivery_user_profiles",
                    headers={**self.headers, "Prefer": "resolution=merge-duplicates"},
                    json=upsert_payload,
                    timeout=2
                )
                
                if m_res.ok:
                    print(f"☁️ [Adaptive] Cloud sync successful for {concept_id}")
                else:
                    print(f"❌ [Adaptive] Cloud sync failed: {m_res.text}")
            except Exception:
                print(f"📡 [Adaptive] No internet connection. Mastery saved locally only.")

            return {"status": "ok", "new_mastery": p_new}

    def reset_mastery(self, user_id):
        """Wipe all local mastery records for a user."""
        try:
            conn = sqlite3.connect(self.local_db)
            cur = conn.cursor()
            cur.execute("DELETE FROM local_mastery WHERE user_id=?", (str(user_id),))
            conn.commit()
            conn.close()
            print(f"🧹 [Adaptive] Local mastery reset for user {user_id}")
            return True
        except Exception as e:
            print(f"❌ [Adaptive] Failed to reset mastery: {e}")
            return False
            
    def save_progress(self, user_id, item_id, status, item_type='concept'):
        """Save lesson or concept progress locally."""
        try:
            conn = sqlite3.connect(self.local_db)
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO user_progress (user_id, item_id, item_type, status, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (str(user_id), str(item_id), item_type, status, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            print(f"💾 [Adaptive] Progress saved: {item_id} -> {status}")
            return True
        except Exception as e:
            print(f"❌ [Adaptive] Failed to save progress: {e}")
            return False

    def get_user_profile(self, user_id):
        """Get full profile: mastery and progress."""
        profile = {
            "mastery": {},
            "progress": {}
        }
        try:
            conn = sqlite3.connect(self.local_db)
            cur = conn.cursor()
            
            # Mastery
            cur.execute("SELECT concept_id, mastery_probability FROM local_mastery WHERE user_id=?", (str(user_id),))
            for cid, m in cur.fetchall():
                profile["mastery"][cid] = m
                
            # Progress
            cur.execute("SELECT item_id, status FROM user_progress WHERE user_id=?", (str(user_id),))
            for iid, status in cur.fetchall():
                profile["progress"][iid] = status
                
            conn.close()
        except Exception as e:
            print(f"❌ [Adaptive] Failed to fetch full profile: {e}")
            
        return profile
