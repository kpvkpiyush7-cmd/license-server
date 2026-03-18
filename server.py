from flask import Flask, request, jsonify
import hashlib

app = Flask(__name__)

SECRET = "GST_SECURE_2026_ULTRA"

def generate_key(machine_id, expiry):

    machine_id = machine_id.upper()

    raw = f"{machine_id}|{expiry}|{SECRET}"
    hash_part = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

    key = f"{machine_id[:4]}-{expiry.replace('-', '')[:6]}-{hash_part}"
    return key



@app.route("/activate", methods=["POST"])
def activate():

    data = request.get_json()

    key = data.get("key", "").strip()
    machine_id = data.get("machine", "").strip().upper()

    if not key or not machine_id:
        return jsonify({"status": "error"})

    parts = key.split("-")
    if len(parts) != 2:
        return jsonify({"status": "error"})

    expiry_part, hash_part = parts

    year = expiry_part[:4]
    month = expiry_part[4:6]
    expiry = f"{year}-{month}-01"

    raw = f"{machine_id}|{expiry}|{SECRET}"
    expected_hash = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

    if hash_part == expected_hash:
        return jsonify({"status": "success", "expiry": expiry})

    return jsonify({"status": "error"})
