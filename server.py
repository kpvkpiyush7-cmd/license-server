from flask import Flask, request, jsonify
import hashlib
import os

app = Flask(__name__)

SECRET = "GST_SECURE_2026_ULTRA"


# =========================
# GENERATE KEY (SAME AS SOFTWARE)
# =========================
def generate_key(machine_id, expiry):

    raw = f"{machine_id}|{expiry}|{SECRET}"
    hash_part = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

    key = f"{machine_id[:4]}-{expiry.replace('-', '')[:6]}-{hash_part}"
    return key


# =========================
# VERIFY KEY
# =========================
def verify_key(key, machine_id, expiry):

    expected = generate_key(machine_id, expiry)
    return key == expected


# =========================
# API
# =========================
@app.route("/activate", methods=["POST"])
def activate():

    try:
        data = request.get_json(force=True)

        key = data.get("key", "").strip()
        machine_id = data.get("machine", "").strip().upper()

        if not key or not machine_id:
            return jsonify({"status": "error"})

        parts = key.split("-")

        if len(parts) != 3:
            return jsonify({"status": "error"})

        expiry_part = parts[1]

        expiry = f"20{expiry_part[:2]}-{expiry_part[2:4]}-{expiry_part[4:6]}"

        if verify_key(key, machine_id, expiry):
            return jsonify({
                "status": "success",
                "expiry": expiry
            })

        return jsonify({"status": "error"})

    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


# =========================
# HOME CHECK
# =========================
@app.route("/")
def home():
    return "Server Running"


# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
