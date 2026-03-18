from flask import Flask, request, jsonify
import hashlib
import uuid
from datetime import datetime

app = Flask(__name__)

SECRET = "GST_SECURE_2026_ULTRA"

# =========================
# MACHINE ID
# =========================
def get_machine_id():
    mac = uuid.getnode()
    return hashlib.sha256(str(mac).encode()).hexdigest()[:12].upper()

# =========================
# GENERATE KEY (same logic)
# =========================
def generate_key(machine_id, expiry):
    raw = f"{machine_id}|{expiry}|{SECRET}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

# =========================
# VERIFY
# =========================
def verify_key(key, machine_id, expiry):
    expected = generate_key(machine_id, expiry)
    return key == expected

# =========================
# API
# =========================
@app.route("/activate", methods=["POST"])
def activate():

    data = request.json
    key = data.get("key")
    machine_id = data.get("machine")

    # expiry decode nahi — tum keygen se control karoge
    expiries = [
        "2026-04-10",
        "2027-03-10",
        "2099-12-31"
    ]

    for exp in expiries:
        if verify_key(key, machine_id, exp):
            return jsonify({
                "status": "success",
                "expiry": exp
            })

    return jsonify({"status": "error"})


# =========================
# RUN
# =========================
import os
port = int(os.environ.get("PORT", 5000))

app.run(host="0.0.0.0", port=port)