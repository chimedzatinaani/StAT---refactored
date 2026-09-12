import time
import json
import sqlite3
import threading
import urllib.request
import urllib.parse
from server import run, ThreadingHTTPServer, AttendanceHandler, init_db

def run_test():
    init_db()
    # Clear tables for fresh test run
    conn = sqlite3.connect("attendance.db")
    c = conn.cursor()
    c.execute("DELETE FROM attendance")
    c.execute("DELETE FROM device_bindings")
    conn.commit()
    conn.close()

    server = ThreadingHTTPServer(('127.0.0.1', 5055), AttendanceHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print("Server started on port 5055 for testing...")
    time.sleep(0.5)

    base_url = "http://127.0.0.1:5055"

    # 1. Test GET / and GET /checkin
    print("\n[1] Testing GET / and GET /checkin (HTML Interface)...")
    req = urllib.request.Request(f"{base_url}/")
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8')
        assert resp.status == 200
        assert "Student Attendance Tracker" in html or "StAT" in html
        assert "NDEFReader" in html
        print("✓ GET / returned 200 OK with correct HTML content.")

    req_checkin = urllib.request.Request(f"{base_url}/checkin")
    with urllib.request.urlopen(req_checkin) as resp:
        html_checkin = resp.read().decode('utf-8')
        assert resp.status == 200
        assert "Classroom Attendance Check-in" in html_checkin
        print("✓ GET /checkin returned 200 OK with Student Check-in view.")

    # 2. Test POST /api/attendance with Programme
    print("\n[2] Testing POST /api/attendance with Programme (Tap NFC / Log student)...")
    payload = json.dumps({"name": "Tinaani Moyo", "reg": "H240188B", "programme": "BSc Computer Science"}).encode('utf-8')
    req = urllib.request.Request(
        f"{base_url}/api/attendance",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        assert resp.status == 201
        assert data["record"]["name"] == "Tinaani Moyo"
        assert data["record"]["reg"] == "H240188B"
        assert data["record"]["programme"] == "BSc Computer Science"
        assert "timestamp" in data["record"]
        print(f"✓ Recorded: {data['record']['name']} ({data['record']['programme']}) at {data['record']['timestamp']}")

    # 3. Test GET /api/attendance
    print("\n[3] Testing GET /api/attendance (Retrieve logged attendance)...")
    req = urllib.request.Request(f"{base_url}/api/attendance")
    with urllib.request.urlopen(req) as resp:
        records = json.loads(resp.read().decode('utf-8'))
        assert resp.status == 200
        assert len(records) >= 1
        assert records[0]["name"] == "Tinaani Moyo"
        assert records[0]["programme"] == "BSc Computer Science"
        print(f"✓ Retrieved {len(records)} record(s) successfully with Programme.")

    # 4. Test database direct persistence check
    print("\n[4] Verifying SQLite database file with Programme...")
    conn = sqlite3.connect("attendance.db")
    c = conn.cursor()
    c.execute("SELECT id, student_name, reg_number, programme, timestamp FROM attendance WHERE reg_number = ?", ("H240188B",))
    row = c.fetchone()
    conn.close()
    assert row is not None
    assert row[3] == "BSc Computer Science"
    print(f"✓ SQLite Verified Row: ID={row[0]}, Name={row[1]}, Reg={row[2]}, Programme={row[3]}, Timestamp={row[4]}")

    # 5. Test Admin Authentication API
    print("\n[5] Testing Admin Authentication API (/api/admin/auth)...")
    auth_payload = json.dumps({"password": "admin123"}).encode('utf-8')
    auth_req = urllib.request.Request(
        f"{base_url}/api/admin/auth",
        data=auth_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(auth_req) as resp:
        auth_data = json.loads(resp.read().decode('utf-8'))
        assert resp.status == 200
        assert auth_data["success"] is True
        assert "token" in auth_data
        print(f"✓ Admin authentication successful. Token received: {auth_data['token']}")

    # 5. Test Duplicate Prevention (same student checking in twice on the same day)
    print("\n[5] Testing Duplicate Attendance Prevention...")
    payload = json.dumps({"name": "Tinaani Moyo", "reg": "H240188B", "device_id": "dev_test_123"}).encode('utf-8')
    req = urllib.request.Request(
        f"{base_url}/api/attendance",
        data=payload,
        headers={"Content-Type": "application/json", "X-Device-ID": "dev_test_123"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            assert False, "Should have failed with 400 due to duplicate attendance"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        err_body = json.loads(e.read().decode('utf-8'))
        assert "already recorded" in err_body["error"].lower()
        print(f"✓ Duplicate attendance correctly blocked: {err_body['error']}")

    # 6. Test Avoid 1 Device Entering 2 Accounts
    print("\n[6] Testing '1 Device Entering 2 Accounts' Prevention...")
    # Register Device X with Student 1 (Alice Smith)
    payload1 = json.dumps({"name": "Alice Smith", "reg": "STU001", "device_id": "device_x"}).encode('utf-8')
    req1 = urllib.request.Request(
        f"{base_url}/api/attendance",
        data=payload1,
        headers={"Content-Type": "application/json", "X-Device-ID": "device_x"},
        method="POST"
    )
    with urllib.request.urlopen(req1) as resp:
        assert resp.status == 201

    # Now try to use Device X with Student 2 (Bob Jones)
    payload2 = json.dumps({"name": "Bob Jones", "reg": "STU002", "device_id": "device_x"}).encode('utf-8')
    req2 = urllib.request.Request(
        f"{base_url}/api/attendance",
        data=payload2,
        headers={"Content-Type": "application/json", "X-Device-ID": "device_x"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req2) as resp:
            assert False, "Should have failed with 403 due to device restriction (1 device entering 2 accounts)"
    except urllib.error.HTTPError as e:
        assert e.code == 403
        err_body = json.loads(e.read().decode('utf-8'))
        assert "bound" in err_body["error"].lower() or "device" in err_body["error"].lower()
        print(f"✓ 1 device entering 2 accounts correctly blocked: {err_body['error']}")

    # 7. Shutdown server
    server.shutdown()
    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    run_test()
