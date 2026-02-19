import os
import json
import sqlite3
import io
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(PROJECT_DIR, 'database', 'progress.db')
UI_DIR = os.path.join(PROJECT_DIR, 'UI')
CONTENT_DIR = os.path.join(PROJECT_DIR, 'content')
LESSONS_DIR = os.path.join(CONTENT_DIR, 'lessons')
CONCEPTS_DIR = os.path.join(CONTENT_DIR, 'concepts')

from updater import preview_updates, run_update, get_db


class Handler(BaseHTTPRequestHandler):
    def _set_json(self, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/' or parsed.path == '/index.html':
            # serve UI/index.html
            try:
                with open(os.path.join(UI_DIR, 'index.html'), 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
            return

        if parsed.path == '/api/preview':
            try:
                data = preview_updates()
                self._set_json(200)
                self.wfile.write(json.dumps(data).encode('utf-8'))
            except Exception as e:
                self._set_json(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            return

        if parsed.path == '/api/installed':
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute('SELECT content_id, type, version FROM installed_content')
                rows = cur.fetchall()
                conn.close()
                arr = [{'content_id': r[0], 'type': r[1], 'version': r[2]} for r in rows]
                self._set_json(200)
                self.wfile.write(json.dumps(arr).encode('utf-8'))
            except Exception as e:
                self._set_json(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            return

        if parsed.path == '/api/lessons':
            try:
                index_path = os.path.join(LESSONS_DIR, 'index.json')
                if not os.path.exists(index_path):
                    self._set_json(200)
                    self.wfile.write(json.dumps({'lessons': []}).encode('utf-8'))
                    return

                with open(index_path, 'r', encoding='utf-8') as f:
                    index = json.load(f)

                lessons_out = []
                for entry in index.get('lessons', []):
                    lesson_path = os.path.join(LESSONS_DIR, entry.get('path', ''))
                    if not os.path.exists(lesson_path):
                        continue
                    with open(lesson_path, 'r', encoding='utf-8') as f:
                        lesson = json.load(f)

                    concepts_out = []
                    for cid in lesson.get('concepts', []):
                        concept_path = os.path.join(CONCEPTS_DIR, f"{cid}.json")
                        if not os.path.exists(concept_path):
                            continue
                        with open(concept_path, 'r', encoding='utf-8') as f:
                            concept = json.load(f)
                        concepts_out.append(concept)

                    lessons_out.append({
                        'lesson_id': lesson.get('lesson_id', entry.get('lesson_id')),
                        'title': lesson.get('title', entry.get('title')),
                        'intro': lesson.get('intro', ''),
                        'concepts': concepts_out
                    })

                self._set_json(200)
                self.wfile.write(json.dumps({'lessons': lessons_out}).encode('utf-8'))
            except Exception as e:
                self._set_json(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            return

        # static fallback
        static_path = os.path.join(UI_DIR, parsed.path.lstrip('/'))
        if os.path.exists(static_path) and os.path.isfile(static_path):
            with open(static_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            if static_path.endswith('.js'):
                self.send_header('Content-Type', 'application/javascript')
            elif static_path.endswith('.css'):
                self.send_header('Content-Type', 'text/css')
            else:
                self.send_header('Content-Type', 'application/octet-stream')
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/apply':
            # run update and capture output
            old_stdout = sys.stdout
            buf = io.StringIO()
            sys.stdout = buf
            try:
                run_update()
            except Exception as e:
                sys.stdout = old_stdout
                self._set_json(500)
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
                return
            sys.stdout = old_stdout
            out = buf.getvalue()
            self._set_json(200)
            self.wfile.write(json.dumps({'output': out}).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()


def run_server(port=8000):
    os.makedirs(UI_DIR, exist_ok=True)
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"Serving UI on http://localhost:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Stopping server')
        server.server_close()


if __name__ == '__main__':
    run_server(8000)
