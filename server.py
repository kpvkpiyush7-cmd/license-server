from flask import Flask, request, jsonify
import hashlib
import sqlite3

app = Flask(__name__)

SECRET = "GST_SECURE_2026_ULTRA"

def init_db():
    conn = sqlite3.connect("admin.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE,
        machine TEXT,
        status TEXT DEFAULT 'active',
        expiry TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

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
            return jsonify({"status": "success", "expiry": expiry})

    except:
        pass

    return jsonify({"status": "error"})

@app.route("/check", methods=["POST"])
def check():
    data = request.get_json()

    key = data.get("key")

    conn = sqlite3.connect("admin.db")
    cur = conn.cursor()

    cur.execute("SELECT status, expiry FROM licenses WHERE key=?", (key,))
    row = cur.fetchone()

    conn.close()

    if not row:
        return jsonify({"status": "invalid"})

    status, expiry = row

    if status != "active":
        return jsonify({"status": "blocked"})

    return jsonify({"status": "success", "expiry": expiry})

@app.route("/deactivate", methods=["POST"])
def deactivate():
    data = request.get_json()
    key = data.get("key")

    conn = sqlite3.connect("admin.db")
    cur = conn.cursor()

    cur.execute("UPDATE licenses SET status='blocked' WHERE key=?", (key,))
    conn.commit()
    conn.close()

    return jsonify({"status": "done"})

@app.route("/all_keys")
def all_keys():
    conn = sqlite3.connect("admin.db")
    cur = conn.cursor()

    cur.execute("SELECT key, machine, status, expiry FROM licenses")
    rows = cur.fetchall()

    conn.close()

    data = []
    for r in rows:
        data.append({
            "key": r[0],
            "machine": r[1],
            "status": r[2],
            "expiry": r[3]
        })

    return jsonify(data)

@app.route("/add_key", methods=["POST"])
def add_key():
    data = request.get_json()

    key = data.get("key")
    machine = data.get("machine")
    expiry = data.get("expiry")

    conn = sqlite3.connect("admin.db")
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO licenses (key, machine, expiry)
            VALUES (?, ?, ?)
        """, (key, machine, expiry))
        conn.commit()
    except:
        pass

    conn.close()
    return jsonify({"status": "saved"})

@app.route("/version", methods=["GET"])
def version():
    return jsonify({
        "version": "2.5.2",
        "url": "https://github.com/kpvkpiyush7-cmd/license-server/releases/download/v2.5.2/ABS.exe"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


