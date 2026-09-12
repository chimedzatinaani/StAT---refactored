import os
import json
import sqlite3
import uuid
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'attendance.db')
TEMPLATE_FILE = os.path.join(BASE_DIR, 'templates', 'index.html')
ADMIN_PASSWORD = os.environ.get('STAT_ADMIN_PASSWORD', 'admin123')

def init_db():
    """Initializes the SQLite database with sessions and attendance support."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            lecturer_name TEXT,
            start_time TEXT,
            end_time TEXT,
            session_key TEXT UNIQUE,
            is_active BOOLEAN NOT NULL DEFAULT 1
        )
    ''')

    # Ensure columns exist if table was already created earlier
    for col, col_type in [('lecturer_name', 'TEXT'), ('start_time', 'TEXT'), ('end_time', 'TEXT'), ('session_key', 'TEXT UNIQUE')]:
        try:
            cursor.execute(f"ALTER TABLE sessions ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass

    # Updated Attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            student_name TEXT NOT NULL,
            reg_number TEXT NOT NULL,
            programme TEXT NOT NULL DEFAULT 'N/A',
            timestamp TEXT NOT NULL
        )
    ''')
    try:
        cursor.execute("ALTER TABLE attendance ADD COLUMN session_id INTEGER")
    except sqlite3.OperationalError:
        pass
    
    # Existing device_bindings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_bindings (
            device_id TEXT PRIMARY KEY,
            reg_number TEXT NOT NULL,
            student_name TEXT NOT NULL,
            programme TEXT
        )
    ''')
    
    conn.commit()
    conn.close()


class AttendanceHandler(BaseHTTPRequestHandler):
    def send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_DELETE(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path.startswith('/api/sessions/delete/'):
            try:
                session_id = path.split('/')[-1]
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                # Delete attendance records associated with the session first
                cursor.execute('DELETE FROM attendance WHERE session_id = ?', (session_id,))
                # Delete the session itself
                cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
                conn.commit()
                conn.close()
                self.send_json(200, {'message': 'Session and associated attendance deleted successfully.'})
            except Exception as e:
                self.send_json(500, {'error': str(e)})
        else:
            self.send_error(404, "Endpoint not found.")

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return

        if path == '/' or path == '/index.html' or path == '/checkin':
            if os.path.exists(TEMPLATE_FILE):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                with open(TEMPLATE_FILE, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Template index.html not found.")
        elif path.startswith('/static/'):
            static_file = os.path.join(BASE_DIR, path.lstrip('/'))
            if os.path.exists(static_file):
                self.send_response(200)
                if path.endswith('.css'):
                    self.send_header('Content-Type', 'text/css')
                elif path.endswith('.woff2'):
                    self.send_header('Content-Type', 'font/woff2')
                elif path.endswith('.ttf'):
                    self.send_header('Content-Type', 'font/ttf')
                self.end_headers()
                with open(static_file, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                print(f"DEBUG: File not found: {static_file}")
                self.send_error(404, "File not found.")
        elif path == '/api/attendance':
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                
                # Fetch all sessions
                cursor.execute('SELECT id, title, lecturer_name, start_time, end_time, session_key FROM sessions ORDER BY id DESC')
                sessions = cursor.fetchall()
                
                sessions_data = []
                for s in sessions:
                    s_id, title, lecturer_name, start_time, end_time, session_key = s
                    
                    # Fetch attendance for this session
                    cursor.execute('SELECT student_name, reg_number, programme, timestamp FROM attendance WHERE session_id = ? ORDER BY id ASC', (s_id,))
                    att_records = cursor.fetchall()
                    
                    att_list = []
                    for idx, ar in enumerate(att_records, start=1):
                        att_list.append({
                            'id': idx,
                            'name': ar[0],
                            'reg': ar[1],
                            'programme': ar[2],
                            'timestamp': ar[3]
                        })
                    
                    sessions_data.append({
                        'session_id': s_id,
                        'title': title or 'Untitled Class',
                        'lecturer_name': lecturer_name or 'Unknown Lecturer',
                        'start_time': start_time or '',
                        'end_time': end_time or '',
                        'session_key': session_key or '',
                        'attendance': att_list
                    })
                
                conn.close()
                self.send_json(200, sessions_data)
            except Exception as e:
                self.send_json(500, {'error': str(e)})

        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        if self.path == '/api/attendance':
            try:
                data = json.loads(post_data.decode('utf-8'))
                name = data.get('name', '').strip()
                reg = data.get('reg', '').strip()
                programme = data.get('programme', '').strip() or 'N/A'
                device_id = data.get('device_id', '').strip() or self.headers.get('X-Device-ID', '').strip()

                if not name or not reg:
                    self.send_json(400, {'error': 'Missing name or reg number'})
                    return

                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()

                # 1. Avoid 1 device entering 2 accounts
                if device_id:
                    cursor.execute('SELECT reg_number, student_name FROM device_bindings WHERE device_id = ?', (device_id,))
                    binding = cursor.fetchone()
                    if binding:
                        bound_reg, bound_name = binding
                        if bound_reg != reg:
                            conn.close()
                            self.send_json(403, {'error': f'Device restriction: This device is already bound to account {bound_name} ({bound_reg}). 1 device cannot enter 2 accounts.'})
                            return
                    else:
                        cursor.execute(
                            'INSERT OR IGNORE INTO device_bindings (device_id, reg_number, student_name, programme) VALUES (?, ?, ?, ?)',
                            (device_id, reg, name, programme)
                        )

                # 2. Avoid duplication (prevent duplicate attendance for the same student on the same day)
                today_prefix = datetime.now().strftime('%Y-%m-%d')
                session_key = data.get('session_id') # Can be session_key UUID
                session_id = None
                if session_key:
                    cursor.execute('SELECT id FROM sessions WHERE session_key = ?', (session_key,))
                    s_row = cursor.fetchone()
                    if s_row:
                        session_id = s_row[0]
                
                if not session_id:
                    # Fallback or error if session is required. For now, let's allow a default or return error.
                    # Actually, the user wants sessions to be required for the new flow.
                    # Let's find the latest active session if none provided, or error.
                    cursor.execute('SELECT id FROM sessions ORDER BY id DESC LIMIT 1')
                    s_row = cursor.fetchone()
                    if s_row:
                        session_id = s_row[0]
                    else:
                        conn.close()
                        self.send_json(400, {'error': 'No active class session found. Please use a valid class NFC tag.'})
                        return

                # Check for existing attendance in this specific session
                cursor.execute(
                    'SELECT id FROM attendance WHERE reg_number = ? AND session_id = ?',
                    (reg, session_id)
                )
                existing = cursor.fetchone()
                if existing:
                    conn.close()
                    self.send_json(400, {'error': 'Attendance already recorded for this student in this session.'})
                    return

                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute(
                    'INSERT INTO attendance (session_id, student_name, reg_number, programme, timestamp) VALUES (?, ?, ?, ?, ?)',
                    (session_id, name, reg, programme, timestamp)
                )
                conn.commit()
                record_id = cursor.lastrowid
                conn.close()

                self.send_json(201, {
                    'message': 'Attendance recorded successfully',
                    'record': {
                        'id': record_id,
                        'name': name,
                        'reg': reg,
                        'programme': programme,
                        'timestamp': timestamp
                    }
                })
            except Exception as e:
                self.send_json(500, {'error': str(e)})

        elif self.path == '/api/attendance/clear':
            try:
                token = self.headers.get('X-Admin-Token', '')
                if not token:
                    try:
                        body_json = json.loads(post_data.decode('utf-8'))
                        token = body_json.get('token', '')
                    except:
                        pass
                
                if token != 'admin_secret_token':
                    self.send_json(401, {'error': 'Unauthorized: Admin authentication required to clear records.'})
                    return

                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM attendance')
                cursor.execute('DELETE FROM device_bindings')
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='attendance'")
                conn.commit()
                conn.close()
                self.send_json(200, {'message': 'All attendance records and device bindings have been cleared.'})
            except Exception as e:
                self.send_json(500, {'error': str(e)})

        elif self.path == '/api/sessions/create':
            try:
                data = json.loads(post_data.decode('utf-8'))
                session_key = str(uuid.uuid4())
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO sessions (title, start_time, end_time, lecturer_name, session_key) VALUES (?, ?, ?, ?, ?)',
                    (data['title'], data['start_time'], data['end_time'], data['lecturer'], session_key)
                )
                conn.commit()
                conn.close()
                self.send_json(201, {'session_key': session_key})
            except Exception as e:
                self.send_json(500, {'error': str(e)})

        elif self.path == '/api/admin/auth':
            try:
                data = json.loads(post_data.decode('utf-8'))
                password = data.get('password', '').strip()
                if password == ADMIN_PASSWORD:
                    self.send_json(200, {'success': True, 'token': 'admin_secret_token', 'message': 'Admin authentication successful'})
                else:
                    self.send_json(401, {'success': False, 'error': 'Invalid admin password/PIN'})
            except Exception as e:
                self.send_json(500, {'error': str(e)})
        else:
            self.send_error(404, "Not Found")

def run(port=5000):
    init_db()
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, AttendanceHandler)
    print(f"==================================================")
    print(f" StAT (Student Attendance Tracker) Backend Ready  ")
    print(f" Local Access:   http://localhost:{port}          ")
    print(f" Network Access: http://0.0.0.0:{port}            ")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down gracefully.")
        httpd.server_close()

if __name__ == '__main__':
    run()

