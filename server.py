from flask import Flask, request, jsonify, render_template
import hashlib
import sqlite3

app = Flask(__name__)

SECRET = "GST_SECURE_2026_ULTRA"

# ================= DB =================
def get_db():
    return sqlite3.connect("licenses.db")

def create_table():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_key TEXT,
        machine_id TEXT,
        expiry TEXT,
        status TEXT DEFAULT 'active',
        payment TEXT DEFAULT 'pending'
    )
    """)
    db.commit()

create_table()

# ================= UI =================
@app.route("/")
def login_page():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

# ================= LOGIN =================
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if data.get("username") == "admin" and data.get("password") == "1234":
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

# ================= ACTIVATE =================
@app.route("/activate", methods=["POST"])
def activate():

    data = request.get_json()
    key = data.get("key", "").strip()
    machine = data.get("machine", "").strip().upper()

    if not key or not machine:
        return jsonify({"status": "error"})

    try:
        expiry_part, hash_part = key.split("-")

        year = expiry_part[:4]
        month = expiry_part[4:6]
        expiry = f"{year}-{month}-01"

        raw = f"{machine}|{expiry}|{SECRET}"
        expected = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

        if hash_part == expected:

            db = get_db()
            cur = db.cursor()

            cur.execute("SELECT * FROM licenses WHERE license_key=?", (key,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO licenses (license_key, machine_id, expiry) VALUES (?, ?, ?)",
                    (key, machine, expiry)
                )
                db.commit()

            return jsonify({"status": "success", "expiry": expiry})

    except:
        pass

    return jsonify({"status": "error"})

# ================= GET LICENSES =================
@app.route("/licenses")
def get_licenses():

    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT id, license_key, machine_id, expiry, status, payment FROM licenses ORDER BY id DESC")

    data = []
    for row in cur.fetchall():
        data.append({
            "id": row[0],
            "key": row[1],
            "machine": row[2],
            "expiry": row[3],
            "status": row[4],
            "payment": row[5]
        })

    return jsonify(data)

# ================= DEACTIVATE =================
@app.route("/deactivate/<int:id>", methods=["POST"])
def deactivate(id):

    db = get_db()
    cur = db.cursor()

    cur.execute("UPDATE licenses SET status='inactive' WHERE id=?", (id,))
    db.commit()

    return jsonify({"status": "done"})
