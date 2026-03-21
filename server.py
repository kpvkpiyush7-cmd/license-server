from flask import Flask, request, jsonify
import hashlib

app = Flask(__name__)

SECRET = "GST_SECURE_2026_ULTRA"

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
        "version": "2.0.1",
        "url": "https://github.com/kpvkpiyush7-cmd/license-server/releases/download/v2.0.1/ABS.exe"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


