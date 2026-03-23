from flask import Flask, request, jsonify, render_template
import hashlib
import sqlite3
import os
from datetime import datetime, timedelta

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

# ================= CHECK (SOFTWARE USE) =================
@app.route("/check", methods=["POST"])
def check():
    data = request.get_json()
    key = data.get("key")
    machine = data.get("machine")

    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT expiry, status FROM licenses WHERE license_key=? AND machine_id=?", (key, machine))
    row = cur.fetchone()

    if not row:
        return jsonify({"status": "invalid"})

    expiry, status = row

    if status != "active":
        return jsonify({"status": "blocked"})

    if datetime.strptime(expiry, "%Y-%m-%d") < datetime.now():
        return jsonify({"status": "expired"})

    return jsonify({"status": "ok"})

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

# ================= ACTIONS =================
@app.route("/deactivate/<int:id>", methods=["POST"])
def deactivate(id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE licenses SET status='inactive' WHERE id=?", (id,))
    db.commit()
    return jsonify({"status": "done"})

@app.route("/activate_license/<int:id>", methods=["POST"])
def activate_license(id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE licenses SET status='active' WHERE id=?", (id,))
    db.commit()
    return jsonify({"status": "done"})

@app.route("/mark_paid/<int:id>", methods=["POST"])
def mark_paid(id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE licenses SET payment='paid' WHERE id=?", (id,))
    db.commit()
    return jsonify({"status": "done"})

@app.route("/extend/<int:id>", methods=["POST"])
def extend(id):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT expiry FROM licenses WHERE id=?", (id,))
    row = cur.fetchone()

    if row:
        expiry = datetime.strptime(row[0], "%Y-%m-%d")
        new_expiry = expiry + timedelta(days=30)

        cur.execute("UPDATE licenses SET expiry=? WHERE id=?", (new_expiry.strftime("%Y-%m-%d"), id))
        db.commit()

    return jsonify({"status": "done"})

# ================= PORT =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)