
from flask import Flask, request, jsonify, render_template, redirect, session
import hashlib
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

SECRET = "GST_SECURE_2026_ULTRA"


# ================= DB =================
def get_db():
    return sqlite3.connect("admin.db")


# ================= EXISTING (UNCHANGED) =================
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


@app.route("/version", methods=["GET"])
def version():
    return jsonify({
        "version": "2.5.1",
        "url": "https://github.com/kpvkpiyush7-cmd/license-server/releases/download/v2.5.1/ABS.exe"
    })


# ================= NEW ADMIN PANEL =================

# 🔐 LOGIN
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "1234":
            session["admin"] = True
            return redirect("/dashboard")
    return render_template("login.html")


# 📊 DASHBOARD
@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/")

    db = get_db()
    cur = db.cursor()

    # agar table nahi ho to create ho jaye
    cur.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT,
        active INTEGER DEFAULT 1
    )
    """)

    cur.execute("SELECT id, key, active FROM licenses")
    data = cur.fetchall()

    licenses = []
    for d in data:
        licenses.append({
            "id": d[0],
            "key": d[1],
            "active": d[2]
        })

    return render_template("dashboard.html", licenses=licenses)


# 🔁 TOGGLE LICENSE
@app.route("/toggle/<int:id>")
def toggle(id):
    if not session.get("admin"):
        return redirect("/")

    db = get_db()
    cur = db.cursor()

    cur.execute("UPDATE licenses SET active = NOT active WHERE id=?", (id,))
    db.commit()

    return redirect("/dashboard")


# 🔓 LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
