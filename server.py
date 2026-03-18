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

    try:
        # key split karo
        parts = key.split("-")

        if len(parts) != 3:
            return jsonify({"status": "error"})

        expiry_part = parts[1]

        # expiry decode
        expiry = f"20{expiry_part[:2]}-{expiry_part[2:4]}-{expiry_part[4:6]}"

    except:
        return jsonify({"status": "error"})

    # verify
    if verify_key(key, machine_id, expiry):
        return jsonify({
            "status": "success",
            "expiry": expiry
        })

    return jsonify({"status": "error"})
