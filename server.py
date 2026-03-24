from flask import Flask, request, jsonify, render_template, redirect, session
import hashlib
import os

# 🔥 NEW IMPORT (POSTGRESQL)
import psycopg2
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = "SUPER_SECRET_ADMIN_123"

SECRET = "GST_SECURE_2026_ULTRA"


# =========================
# DATABASE CONNECTION (POSTGRESQL)
# =========================
def get_conn():
    db_url = os.environ.get("DATABASE_URL")

    if not db_url:
        raise Exception("DATABASE_URL NOT FOUND ❌")

    from urllib.parse import urlparse
    import psycopg2

    url = urlparse(db_url)

    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )

    return conn


# =========================
# DATABASE INIT
# =========================
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        id SERIAL PRIMARY KEY,
        key TEXT UNIQUE,
        machine TEXT,
        status TEXT DEFAULT 'active',
        expiry TEXT
    )
    """)

    conn.commit()
    conn.close()
try:
    init_db()
except Exception as e:
    print("DB INIT ERROR:", e)
# =========================
# LOGIN SYSTEM
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect("/")

        return render_template("login.html", error="Invalid Login")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# DASHBOARD (PROTECTED)
# =========================
@app.route("/")
def dashboard():
    if not session.get("admin"):
        return redirect("/login")
    return render_template("dashboard.html")


# =========================
# OLD ACTIVATE (KEEP SAFE)
# =========================
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


# =========================
# NEW CHECK (CONTROL)
# =========================
@app.route("/check", methods=["POST"])
def check():
    data = request.get_json()

    key = data.get("key")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT status, expiry FROM licenses WHERE key=%s", (key,))
    row = cur.fetchone()

    conn.close()

    if not row:
        return jsonify({"status": "invalid"})

    status, expiry = row

    if status != "active":
        return jsonify({"status": "blocked"})

    return jsonify({"status": "success", "expiry": expiry})


# =========================
# ADD KEY (FROM KEYGEN)
# =========================
@app.route("/add_key", methods=["POST"])
def add_key():
    data = request.get_json()

    key = data.get("key")
    machine = data.get("machine")
    expiry = data.get("expiry")

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO licenses (key, machine, expiry)
            VALUES (%s, %s, %s)
        """, (key, machine, expiry))
        conn.commit()
    except:
        pass

    conn.close()
    return jsonify({"status": "saved"})


# =========================
# ALL KEYS
# =========================
@app.route("/all_keys")
def all_keys():
    conn = get_conn()
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


# =========================
# DEACTIVATE
# =========================
@app.route("/deactivate", methods=["POST"])
def deactivate():
    data = request.get_json()
    key = data.get("key")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("UPDATE licenses SET status='blocked' WHERE key=%s", (key,))
    conn.commit()
    conn.close()

    return jsonify({"status": "done"})


# =========================
# ACTIVATE AGAIN
# =========================
@app.route("/activate_key", methods=["POST"])
def activate_key():
    data = request.get_json()
    key = data.get("key")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("UPDATE licenses SET status='active' WHERE key=%s", (key,))
    conn.commit()
    conn.close()

    return jsonify({"status": "done"})


# =========================
# VERSION
# =========================
@app.route("/version", methods=["GET"])
def version():
    return jsonify({
        "version": "2.5.2",
        "url": "https://github.com/kpvkpiyush7-cmd/license-server/releases/download/v2.5.2/ABS.exe"
    })


# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
