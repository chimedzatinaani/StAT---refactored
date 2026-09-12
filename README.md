# StAT (Student Attendance Tracker) - NFC-Based Attendance System

A lightweight, real-world Student Attendance Tracking system that supports two powerful NFC workflows:
1. **Lecturer Podium Tag (Recommended)**: The lecturer has 1 pre-programmed NFC tag on their desk. Students tap their phones against it to open the check-in portal and submit their details into the register.
2. **Student NFC Cards**: Students have individual NFC tags and tap the lecturer's phone scanner.

Real-time date, time, and programme stamps are recorded and persisted into an SQLite database with an interactive live dashboard and admin authentication.

---

## 🚀 Features

- **Actual Web NFC Integration (`NDEFReader`)**: Interacts directly with NFC tags and stickers from Chrome/Edge on NFC-enabled Android devices without needing third-party native apps.
- **Lecturer Podium Tag Programmer**: Easily program 1 classroom desk/podium tag with the check-in URL (`/checkin`) so students can tap their own phones to log attendance instantly.
- **Student Details Caching (`localStorage`)**: Students enter their name, registration number, and programme once; subsequent taps auto-fill or check them in with a single click.
- **Built-in Student Tag Writer Tool**: Program individual NTAG213/215/216 stickers with student Name, Registration Number, and Programme.
- **Admin Authentication**: Secure PIN protection (default: `admin123`) for lecturers and administrators to access scanner, tag programmer, and database clearing tools.
- **SQLite Database Persistence**: Stores complete records (`id`, `student_name`, `reg_number`, `programme`, `timestamp`) safely in `attendance.db`.
- **Zero External Dependencies**: Server built using Python's standard library (`http.server` + `sqlite3`). Runs out-of-the-box on any machine with Python 3.
- **Export to CSV**: Easily export logged attendance sheets for records and reports.

---

## 📁 Project Structure

```
StAT base/
├── server.py              # Zero-dependency Python HTTP & SQLite API backend
├── attendance.db          # SQLite database storing attendance records
├── templates/
│   └── index.html         # Frontend with Student Check-in, Scanner, & Writer dashboard
├── test_system.py         # Automated test suite for backend API & DB verification
├── requirements.txt       # Information regarding Python standard library usage
└── README.md              # Documentation and guide
```

---

## 🛠️ How to Run

### 1. Start the Server
Run the backend server using Python:
```bash
python3 server.py
```

The server listens on `http://0.0.0.0:5000` (all interfaces), making it accessible locally and over your local Wi-Fi network.

### 2. Open on your Phone or Computer
- **On the Host Machine**: Open [http://localhost:5000](http://localhost:5000)
- **On your Smartphone**: 
  1. Make sure your phone and computer are on the same Wi-Fi network.
  2. Find your computer's IP address (e.g. `ip addr show` or `ifconfig`).
  3. Open `http://<YOUR_COMPUTER_IP>:5000` in Google Chrome on your Android phone.
  *(Note: Web NFC requires a secure origin like `localhost` or an HTTPS connection, or enabling `#unsafely-treat-insecure-origin-as-secure` in `chrome://flags` on your mobile browser for local IP development).*

---

## 🏷️ How to Program & Use NFC Tags

### Workflow (Lecturer Podium Tag - Recommended)
1. Navigate to the **"Tag Programmer"** tab in the StAT web interface (requires admin PIN authentication).
2. Click **"Program Lecturer Check-In Tag"** and hold a blank NFC sticker against your phone.
3. Place this programmed tag on your desk/podium in the classroom.
4. When students walk into class, they tap their phones against your desk tag. Their phone automatically opens the StAT Student Check-in portal (`/checkin`), where their details are remembered for one-tap check-ins!
5. Attendance is recorded instantly in the SQLite database and displayed on your live feed.

### Alternative Workflow (Student NFC Cards)
1. Use the **Tag Programmer** tab to write each student's Name, Registration Number, and Programme onto their personal NFC card/sticker.
2. Open the **Lecturer Scanner** tab on the lecturer's phone, authenticate as admin, and click **Start Scanning**.
3. Students tap their personal cards to the lecturer's phone to check in.

---

## 🧪 Testing the System

You can run the end-to-end automated verification script anytime:
```bash
python3 test_system.py
```
This tests:
- HTML interface delivery (200 OK for `/` and `/checkin`)
- POST attendance API (`/api/attendance`) with Programme
- GET attendance API
- Admin authentication API (`/api/admin/auth`)
- SQLite database persistence and data integrity
