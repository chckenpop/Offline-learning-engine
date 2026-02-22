import os
import json
import sqlite3
import io
import sys
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
PUNE_CONTENT_DIR = os.path.join(PROJECT_DIR, 'pune_content')
DB_PATH = os.path.join(PUNE_CONTENT_DIR, 'metadata.db')
UI_DIR = os.path.join(PROJECT_DIR, 'UI')
LESSONS_DIR = os.path.join(PUNE_CONTENT_DIR, 'lessons')
CONCEPTS_DIR = os.path.join(PUNE_CONTENT_DIR, 'concepts')
VIDEOS_DIR = os.path.join(PUNE_CONTENT_DIR, 'assets', 'videos')

from updater import preview_updates, run_update, get_db, download_specific_item, SUPABASE_URL, HEADERS, LESSONS_ENDPOINT, CONCEPTS_ENDPOINT, VIDEOS_ENDPOINT, SUPABASE_KEY
from adaptive import AdaptiveService
from ai_gen import AIGenService
from ai_tutor import AITutorService

adaptive_service = AdaptiveService(SUPABASE_URL, SUPABASE_KEY)
ai_service = AIGenService()
ai_tutor_service = AITutorService(DB_PATH)

class Handler(BaseHTTPRequestHandler):
    def _set_json(self, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def _send_json(self, data, code=200):
        try:
            self._set_json(code)
            self.wfile.write(json.dumps(data).encode('utf-8'))
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass # Client disconnected prematurely

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Static Pages & Health
        if path == '/' or path == '/index.html':
            self._serve_static('index.html', 'text/html; charset=utf-8')
            return
        if path == '/health':
            self._send_json({'status': 'ok'})
            return

        # 2. Adaptive & Progress APIs
        if path.startswith('/api/user_profile/'):
            user_id = path.split('/')[-1]
            self._send_json({'profile_data': adaptive_service.get_user_profile(user_id)})
            return
        
        if path == '/api/lessons':
            self._send_json({'lessons': self._get_lessons()})
            return
            
        if path == '/api/videos':
            self._send_json({'videos': self._get_videos()})
            return

        if path == '/api/installed':
            self._send_json(self._get_installed())
            return

        # 3. Search & Speedtest
        if path.startswith('/api/speedtest'):
            self._serve_speedtest()
            return

        if path.startswith('/api/search_cloud'):
            self._handle_search_cloud(parsed)
            return

        # 4. Auth & Database (Partial Proxy)
        if path == '/api/saved_courses':
            self._handle_proxy_get(f"{SUPABASE_URL}/rest/v1/added_courses?select=id,title,description,thumbnail_url,subjects&order=created_at.desc")
            return

        if path == '/api/courses':
            self._handle_courses_search(parsed)
            return

        if path.startswith('/api/courses/') and path.endswith('/curriculum'):
            course_id = path.split('/')[3]
            self._handle_course_curriculum(course_id)
            return

        if path.startswith('/api/search_videos'):
            self._handle_search_videos(parsed)
            return

        if path.startswith('/api/ai_tutor/history/'):
            user_id = path.split('/')[-1]
            self._send_json({'history': ai_tutor_service.get_history(user_id)})
            return

        # 5. Static Fallback (CSS, JS, Assets)
        self._serve_static_fallback(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(length)
        data = json.loads(body.decode('utf-8')) if length > 0 else {}

        if path == '/api/login':
            self._handle_login(data)
        elif path == '/api/signup':
            self._handle_signup(data)
        elif path == '/api/progress':
            self._handle_progress(data)
        elif path == '/api/log_event':
            self._handle_log_event(data)
        elif path == '/api/reset_progress':
            self._handle_reset_progress(data)
        elif path == '/api/generate_adaptive_lesson':
            self._handle_ai_generate(data)
        elif path == '/api/download':
            self._handle_download(data)
        elif path == '/api/apply':
            self._handle_apply_updates()
        elif path == '/api/add_course':
            self._handle_add_course(data)
        elif path == '/api/ai_tutor/chat':
            self._handle_ai_tutor_chat(data)
        elif path == '/api/scheduler/save':
            self._handle_scheduler_save(data)
        else:
            self.send_response(404)
            self.end_headers()

    # --- GET Handlers ---

    def _get_lessons(self):
        lessons_out = []
        if os.path.exists(LESSONS_DIR):
            for f in sorted(os.listdir(LESSONS_DIR)):
                if not f.endswith('.json'): continue
                try:
                    with open(os.path.join(LESSONS_DIR, f), 'r', encoding='utf-8') as jf:
                        lesson = json.load(jf)
                    concepts_out = []
                    for c in lesson.get('concepts', []):
                        if isinstance(c, dict): concepts_out.append(c)
                        else:
                            cpath = os.path.join(CONCEPTS_DIR, f"{c}.json")
                            if os.path.exists(cpath):
                                with open(cpath, 'r', encoding='utf-8') as cf:
                                    concepts_out.append(json.load(cf))
                    lesson['lesson_id'] = lesson.get('lesson_id') or lesson.get('id') or f.replace('.json', '')
                    lesson['concepts'] = concepts_out
                    lessons_out.append(lesson)
                except: continue
        return lessons_out

    def _get_videos(self):
        videos_out = []
        if os.path.exists(VIDEOS_DIR):
            for f in os.listdir(VIDEOS_DIR):
                if not f.endswith('.json'): continue
                try:
                    with open(os.path.join(VIDEOS_DIR, f), 'r', encoding='utf-8') as jf:
                        vdata = json.load(jf)
                        meta = vdata.get('metadata') 
                        if isinstance(meta, str): meta = json.loads(meta)
                        videos_out.append({
                            'title': vdata.get('title', 'Untitled Video'),
                            'id': vdata.get('id'),
                            'thumb': vdata.get('local_thumb', ''),
                            'url': vdata.get('local_video', ''),
                            'length': (meta or {}).get('length', '0:00')
                        })
                except: continue
        return videos_out

    def _get_installed(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute('SELECT id, type, version FROM cached_content')
            rows = cur.fetchall()
            conn.close()
            return [{'content_id': r[0], 'type': r[1], 'version': r[2]} for r in rows]
        except: return []

    def _handle_search_cloud(self, parsed):
        import requests
        query = urllib.parse.parse_qs(parsed.query).get('q', [''])[0].lower()
        matches = []
        try:
            # Lessons
            res = requests.get(LESSONS_ENDPOINT + "?select=lesson_id,json_data,version", headers=HEADERS)
            if res.ok:
                for rl in res.json():
                    j = rl.get('json_data')
                    if isinstance(j, str): j = json.loads(j)
                    title = (j or {}).get('title', rl['lesson_id'])
                    if query in title.lower() or query in rl['lesson_id'].lower():
                        matches.append({'title': title, 'type': 'Lesson', 'id': rl['lesson_id'], 'version': rl['version']})
            self._send_json({'results': matches})
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_courses_search(self, parsed):
        import requests
        q = urllib.parse.parse_qs(parsed.query).get('q', [''])[0].lower().strip()
        try:
            res = requests.get(f"{SUPABASE_URL}/rest/v1/delivery_courses?select=id,json_data", headers=HEADERS)
            if res.ok:
                out = []
                seen_titles = set()
                for row in res.json():
                    jd = row.get('json_data', {})
                    if isinstance(jd, str): jd = json.loads(jd)
                    title = jd.get('title', 'Unknown Course')
                    
                    # Deduplicate by title for a cleaner UI
                    if title.lower() in seen_titles:
                        continue
                    
                    if not q or q in title.lower():
                        seen_titles.add(title.lower())
                        out.append({
                            'id': row['id'], 
                            'title': title, 
                            'description': jd.get('description', ''), 
                            'thumbnail_url': jd.get('thumbnail_url')
                        })
                self._send_json({'courses': out})
            else: self._send_json({'error': res.text}, res.status_code)
        except Exception as e: self._send_json({'error': str(e)}, 500)

    def _handle_proxy_get(self, url):
        import requests
        try:
            res = requests.get(url, headers=HEADERS)
            self._send_json(res.json() if res.ok else {'error': res.text}, res.status_code)
        except Exception as e: self._send_json({'error': str(e)}, 500)

    def _handle_course_curriculum(self, course_id):
        import requests
        try:
            # We need to fetch subjects and lessons for this course
            # This is a bit complex as we might need to join tables
            # For now, let's try to fetch delivery_subjects linked to this course
            url = f"{SUPABASE_URL}/rest/v1/delivery_subjects?course_id=eq.{course_id}&select=id,title,order,lessons:delivery_lessons(lesson_id,title,order_index,json_data)&order=order.asc"
            res = requests.get(url, headers=HEADERS)
            if res.ok:
                subjects = res.json()
                # Format to match frontend expectations
                curriculum = []
                for s in subjects:
                    lessons = []
                    for l in s.get('lessons', []):
                        jd = l.get('json_data', {})
                        if isinstance(jd, str): jd = json.loads(jd)
                        lessons.append({
                            'lesson_id': l['lesson_id'],
                            'title': l['title'],
                            'order': l['order_index'],
                            'concepts': jd.get('concepts', [])
                        })
                    curriculum.append({
                        'id': s['id'],
                        'title': s['title'],
                        'order': s['order'],
                        'lessons': lessons
                    })
                self._send_json({'curriculum': curriculum})
            else:
                self._send_json({'error': res.text}, res.status_code)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_search_videos(self, parsed):
        import requests
        q = urllib.parse.parse_qs(parsed.query).get('q', [''])[0].lower().strip()
        try:
            # Search in delivery_videos table
            url = f"{SUPABASE_URL}/rest/v1/videos?select=id,title,thumbnail_url,url,metadata&order=created_at.desc"
            res = requests.get(url, headers=HEADERS)
            if res.ok:
                results = []
                for v in res.json():
                    if not q or q in v['title'].lower():
                        meta = v.get('metadata', {})
                        if isinstance(meta, str): meta = json.loads(meta)
                        results.append({
                            'id': v['id'],
                            'title': v['title'],
                            'thumb': v['thumbnail_url'],
                            'url': v['url'],
                            'length': meta.get('length', '0:00'),
                            'resolution': meta.get('resolution', 'HD')
                        })
                self._send_json({'results': results})
            else:
                self._send_json({'error': res.text}, res.status_code)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_add_course(self, data):
        import requests, uuid
        try:
            source_id = data.get('source_id')
            course_id = source_id 
            user_id = int(data.get('created_by') or 1)
            
            # 1. Catalog Check/Creation (delivery_courses)
            if not course_id:
                # Check for existing course by title to avoid duplicates in catalog
                q_url = f"{SUPABASE_URL}/rest/v1/delivery_courses?title=eq.{urllib.parse.quote(data.get('title', ''))}&select=id"
                q_res = requests.get(q_url, headers=HEADERS)
                if q_res.ok and q_res.json():
                    course_id = q_res.json()[0]['id']
                else:
                    # Create new catalog entry
                    course_id = str(uuid.uuid4())
                    course_payload = {
                        "id": course_id,
                        "title": data.get('title'),
                        "json_data": {
                            "title": data.get('title'),
                            "description": data.get('description'),
                            "thumbnail_url": data.get('thumbnail_url'),
                        }
                    }
                    res = requests.post(f"{SUPABASE_URL}/rest/v1/delivery_courses", headers={**HEADERS, "Prefer": "return=minimal"}, json=course_payload)
                    if not res.ok:
                        self._send_json({'error': f"Failed to create catalog entry: {res.text}"}, res.status_code)
                        return

            # 2. User List Check/Creation (added_courses)
            # Check if user already has this course saved
            check_url = f"{SUPABASE_URL}/rest/v1/added_courses?created_by=eq.{user_id}&original_course_id=eq.{course_id}&select=id"
            check_res = requests.get(check_url, headers=HEADERS)
            if check_res.ok and check_res.json():
                self._send_json({'status': 'ok', 'message': 'Already saved', 'course_id': course_id})
                return

            added_payload = {
                "id": str(uuid.uuid4()),
                "created_by": user_id,
                "title": data.get('title'),
                "description": data.get('description'),
                "thumbnail_url": data.get('thumbnail_url'),
                "subjects": data.get('subjects', []), 
                "original_course_id": course_id
            }
            res2 = requests.post(f"{SUPABASE_URL}/rest/v1/added_courses", headers=HEADERS, json=added_payload)
            
            if res2.ok:
                self._send_json({'status': 'ok', 'course_id': course_id})
            else:
                self._send_json({'error': f"Failed to add to user list: {res2.text}"}, res2.status_code)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    # --- POST Handlers ---

    def _handle_login(self, data):
        import hashlib, requests
        email = data.get('email', '')
        pw_hash = hashlib.sha256(data.get('password', '').encode()).hexdigest()
        try:
            res = requests.get(f"{SUPABASE_URL}/rest/v1/delivery_users?email=eq.{email}&password_hash=eq.{pw_hash}&select=id,name", headers=HEADERS)
            if res.ok and len(res.json()) > 0:
                user = res.json()[0]
                self._send_json({'status': 'ok', 'user_id': user['id'], 'name': user['name']})
            else: self._send_json({'error': 'Invalid credentials'}, 401)
        except Exception as e: self._send_json({'error': str(e)}, 500)

    def _handle_signup(self, data):
        import hashlib, requests
        pw_hash = hashlib.sha256(data.get('password', '').encode()).hexdigest()
        payload = {
            "email": data.get('email'),
            "password_hash": pw_hash,
            "name": data.get('name'),
            "age": data.get('age'),
            "phone": data.get('phone')
        }
        try:
            post_res = requests.post(f"{SUPABASE_URL}/rest/v1/delivery_users", headers=HEADERS, json=payload)
            if post_res.ok: self._send_json({'status': 'ok'})
            else: self._send_json({'error': post_res.text}, 400)
        except Exception as e: self._send_json({'error': str(e)}, 500)

    def _handle_progress(self, data):
        user_id = data.get('user_id') or 'local_user'
        item_id = data.get('lesson_id') or data.get('concept_id')
        status = data.get('status', 'completed')
        item_type = 'lesson' if 'lesson_id' in data else 'concept'
        if item_id:
            adaptive_service.save_progress(user_id, item_id, status, item_type)
        self._send_json({'status': 'ok'})

    def _handle_log_event(self, data):
        try:
            result = adaptive_service.log_interaction(data)
            self._send_json(result)
        except Exception as e: self._send_json({'error': str(e)}, 500)

    def _handle_reset_progress(self, data):
        uid = data.get('user_id')
        if adaptive_service.reset_mastery(uid): self._send_json({'status': 'ok'})
        else: self._send_json({'error': 'Reset failed'}, 500)

    def _handle_ai_generate(self, data):
        lesson_id = data.get('lesson_id')
        mode = data.get('mode')
        lesson_path = os.path.join(LESSONS_DIR, f"{lesson_id}.json")
        if not os.path.exists(lesson_path):
            self._send_json({'error': 'Not found'}, 404)
            return
        with open(lesson_path, 'r', encoding='utf-8') as f:
            original = json.load(f)
        new_lesson = ai_service.generate_adaptive_lesson(original, mode)
        if new_lesson:
            new_id = f"{lesson_id}_{mode.lower()}"
            new_lesson['lesson_id'] = new_id
            with open(os.path.join(LESSONS_DIR, f"{new_id}.json"), 'w', encoding='utf-8') as f:
                json.dump(new_lesson, f, indent=2)
            self._send_json({'status': 'ok', 'lesson_id': new_id})
        else: self._send_json({'error': 'AI failed'}, 500)

    def _handle_download(self, data):
        threading.Thread(target=download_specific_item, args=(data.get('id'), data.get('type'))).start()
        self._send_json({'status': 'queued'})

    def _handle_apply_updates(self):
        try:
            run_update()
            self._send_json({'status': 'success'})
        except Exception as e: self._send_json({'error': str(e)}, 500)

    def _handle_ai_tutor_chat(self, data):
        try:
            user_id = data.get('user_id')
            prompt = data.get('prompt')
            lesson_context = data.get('lesson_context')
            file_text = data.get('file_text')
            
            if not user_id or not prompt:
                self._send_json({'error': 'Missing user_id or prompt'}, 400)
                return

            reply = ai_tutor_service.chat(user_id, prompt, lesson_context, file_text)
            self._send_json({'status': 'ok', 'reply': reply})
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _handle_scheduler_save(self, data):
        import requests, uuid
        try:
            # Save to 'study_schedules' table in Supabase
            payload = {
                "id": str(uuid.uuid4()),
                "user_id": data.get('user_id'),
                "subjects": data.get('subjects'),
                "exam_dates": data.get('exam_dates'),
                "daily_hours": data.get('daily_hours'),
                "priority_levels": data.get('priority_levels'),
                "break_time": data.get('break_time'),
                "generated_timetable": data.get('generated_timetable')
            }
            res = requests.post(f"{SUPABASE_URL}/rest/v1/study_schedules", headers=HEADERS, json=payload)
            if res.ok:
                self._send_json({'status': 'ok'})
            else:
                self._send_json({'error': res.text}, res.status_code)
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    # --- Static File Helpers ---

    def _serve_static(self, filename, content_type):
        path = os.path.join(UI_DIR, filename)
        if os.path.exists(path):
            with open(path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                self.wfile.write(content)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                pass

    def _handle_scheduler_save(self, data):
        import requests as req_lib, uuid
        try:
            payload = {
                "id": str(uuid.uuid4()),
                "user_id": data.get('user_id', 'anonymous'),
                "subjects": json.dumps(data.get('subjects', [])),
                "exam_dates": json.dumps(data.get('exam_dates', {})),
                "daily_hours": data.get('daily_hours', 0),
                "priority_levels": json.dumps(data.get('priority_levels', {})),
                "break_time": data.get('break_time', 15),
                "generated_timetable": json.dumps(data.get('generated_timetable', {}))
            }

            # Try Supabase first
            try:
                res = req_lib.post(
                    f"{SUPABASE_URL}/rest/v1/study_schedules",
                    headers=HEADERS,
                    json=payload,
                    timeout=8
                )
                if res.status_code in (200, 201):
                    self._send_json({'status': 'ok', 'storage': 'cloud'})
                    return
            except Exception as cloud_err:
                print(f"[Scheduler] Supabase unavailable: {cloud_err}. Falling back to SQLite.")

            # Fallback: save locally in SQLite
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS study_schedules (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    subjects TEXT,
                    exam_dates TEXT,
                    daily_hours INTEGER,
                    priority_levels TEXT,
                    break_time INTEGER,
                    generated_timetable TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            cur.execute("""
                INSERT INTO study_schedules
                    (id, user_id, subjects, exam_dates, daily_hours, priority_levels, break_time, generated_timetable)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload['id'], payload['user_id'], payload['subjects'],
                payload['exam_dates'], payload['daily_hours'],
                payload['priority_levels'], payload['break_time'],
                payload['generated_timetable']
            ))
            conn.commit()
            conn.close()
            self._send_json({'status': 'ok', 'storage': 'local'})

        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def _serve_static_fallback(self, path):
        # Clean path and search in UI or pune_content
        clean_path = path.lstrip('/')
        for base in [UI_DIR, PUNE_CONTENT_DIR]:
            full_path = os.path.join(base, clean_path)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                with open(full_path, 'rb') as f: content = f.read()
                self.send_response(200)
                ext = os.path.splitext(full_path)[1].lower()
                mime = {'.js': 'application/javascript', '.css': 'text/css', '.mp4': 'video/mp4', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}.get(ext, 'application/octet-stream')
                self.send_header('Content-Type', mime)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                try:
                    self.wfile.write(content)
                except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                    pass
                return
        self.send_response(404)
        self.end_headers()

    def _serve_speedtest(self):
        data = os.urandom(1024 * 1024)
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

def background_sync():
    try: run_update()
    except: pass

def run_server(port=8000):
    os.makedirs(UI_DIR, exist_ok=True)
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"🚀 BrightStudy Engine running on http://localhost:{port}")
    threading.Thread(target=background_sync, daemon=True).start()
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()

if __name__ == '__main__':
    run_server(8000)
