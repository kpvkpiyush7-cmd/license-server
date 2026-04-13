from flask import Flask, request, jsonify, render_template, redirect, session
import hashlib
import os
from datetime import datetime, timedelta
import razorpay

# 🔥 NEW IMPORT (POSTGRESQL)
import psycopg2
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = "SUPER_SECRET_ADMIN_123"

SECRET = "GST_SECURE_2026_ULTRA"
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def admin_required():
    if not session.get("admin"):
        return False
    return True


# =========================
# DATABASE CONNECTION (POSTGRESQL)
# =========================
def get_conn():
    db_url = os.environ.get("DATABASE_URL")

    if not db_url:
        raise Exception("DATABASE_URL NOT FOUND ❌")

    
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

    # EXISTING TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        id SERIAL PRIMARY KEY,
        key TEXT UNIQUE,
        machine TEXT,
        status TEXT DEFAULT 'active',
        expiry TEXT
    )
    """)

    # ===== LICENSE EXTRA COLUMNS =====
    try:
        cur.execute("ALTER TABLE licenses ADD COLUMN customer_name TEXT")
    except:
        pass

    try:
        cur.execute("ALTER TABLE licenses ADD COLUMN customer_mobile TEXT")
    except:
        pass

    try:
        cur.execute("ALTER TABLE licenses ADD COLUMN reseller_id INTEGER")
    except:
        pass

    cur.execute("""
    CREATE TABLE IF NOT EXISTS resellers (
        id SERIAL PRIMARY KEY,
        name TEXT,
        mobile TEXT UNIQUE,
        password TEXT,
        balance REAL DEFAULT 0,
        status TEXT DEFAULT 'active'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reseller_licenses (
        id SERIAL PRIMARY KEY,
        reseller_id INTEGER,
        license_key TEXT,
        machine TEXT,
        expiry TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS wallet_transactions (
        id SERIAL PRIMARY KEY,
        reseller_id INTEGER,
        amount REAL,
        type TEXT,
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

    

    
try:
    init_db()
except Exception as e:
    print("DB INIT ERROR:", e)


import os
from flask import send_file

@app.route("/download")
def download():
    return redirect("https://github.com/kpvkpiyush7-cmd/license-server/releases/download/v2.7.1/ABS_Setup.exe")


@app.route("/create_order", methods=["POST"])
def create_order():
    data = request.get_json() or {}

    amount = int(data.get("amount", 999))
    plan = data.get("plan", "yearly")

    if amount <= 0:
        return jsonify({"status": "fail", "msg": "Invalid amount"}), 400

    order = client.order.create({
        "amount": amount * 100,
        "currency": "INR",
        "payment_capture": 1,
        "notes": {
            "plan": plan
        }
    })

    return jsonify({
        "status": "success",
        "id": order["id"],
        "amount": order["amount"],
        "plan": plan,
        "key": RAZORPAY_KEY_ID
    })
@app.route("/verify_payment", methods=["POST"])
def verify_payment():
    data = request.get_json() or {}

    payment_id = (data.get("payment_id") or "").strip()
    order_id = (data.get("order_id") or "").strip()
    signature = (data.get("signature") or "").strip()
    machine = (data.get("machine") or "").strip().upper()
    plan = (data.get("plan") or "").strip().lower()
    name = (data.get("name") or "").strip()
    mobile = (data.get("mobile") or "").strip()

    if not payment_id or not order_id or not signature or not machine:
        return jsonify({"status": "fail", "msg": "Missing payment details"}), 400

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        })
    except Exception:
        return jsonify({"status": "fail", "msg": "Payment signature invalid"}), 400

    try:
        payment = client.payment.fetch(payment_id)
    except Exception:
        return jsonify({"status": "fail", "msg": "Payment fetch failed"}), 400

    if payment.get("status") != "captured":
        return jsonify({"status": "fail", "msg": "Payment not captured"}), 400

    if plan == "monthly":
        expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    elif plan == "lifetime":
        expiry = "2099-12-31"
    else:
        expiry = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")

    raw = f"{machine}|{expiry}|{SECRET}"
    key = expiry.replace("-", "")[:6] + "-" + hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

    conn = get_conn()
    cur = conn.cursor()

    # duplicate payment save na ho
    cur.execute("SELECT key FROM licenses WHERE machine=%s AND expiry=%s", (machine, expiry))
    existing = cur.fetchone()

    if not existing:
        cur.execute("""
            INSERT INTO licenses 
            (key, machine, expiry, customer_name, customer_mobile)
            VALUES (%s, %s, %s, %s, %s)
        """, (key, machine, expiry, name, mobile))
        conn.commit()

    conn.close()

    return jsonify({
        "status": "success",
        "key": key,
        "expiry": expiry
    })

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/admin/add_reseller", methods=["POST"])
def add_reseller():

    if not admin_required():
        return jsonify({"status":"unauthorized"}), 401

    data = request.json

    name = data["name"]
    mobile = data["mobile"]
    password = data["password"]
    balance = float(data.get("balance", 0))

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO resellers (name, mobile, password, balance)
        VALUES (%s, %s, %s, %s)
    """, (name, mobile, password, balance))

    conn.commit()
    conn.close()

    return jsonify({"status":"success"})

@app.route("/admin/add_balance", methods=["POST"])
def add_balance():

    if not admin_required():
        return jsonify({"status":"unauthorized"}), 401

    data = request.json

    reseller_id = data["reseller_id"]
    amount = float(data["amount"])

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE resellers SET balance = balance + %s WHERE id=%s
    """, (amount, reseller_id))

    cur.execute("""
        INSERT INTO wallet_transactions (reseller_id, amount, type, note)
        VALUES (%s, %s, 'credit', 'Admin Recharge')
    """, (reseller_id, amount))

    conn.commit()
    conn.close()

    return jsonify({"status":"success"})

@app.route("/admin/resellers")
def get_resellers():

    if not admin_required():
        return jsonify({"status":"unauthorized"}), 401

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, name, mobile, balance, status FROM resellers")
    rows = cur.fetchall()

    conn.close()

    data = []
    for r in rows:
        data.append({
            "id": r[0],
            "name": r[1],
            "mobile": r[2],
            "balance": r[3],
            "status": r[4]
        })

    return jsonify(data)

# =========================
# GET RESELLER BALANCE
# =========================
@app.route("/reseller/balance/<int:rid>")
def reseller_balance(rid):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT balance FROM resellers WHERE id=%s", (rid,))
    row = cur.fetchone()

    conn.close()

    if not row:
        return jsonify({"balance": 0})

    return jsonify({"balance": row[0]})
# =========================
# RESELLER LOGIN
# =========================
@app.route("/reseller/login", methods=["POST"])
def reseller_login():
    data = request.json

    mobile = data.get("mobile")
    password = data.get("password")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name FROM resellers
        WHERE mobile=%s AND password=%s AND status='active'
    """, (mobile, password))

    row = cur.fetchone()
    conn.close()

    if row:
        session["reseller"] = True
        session["reseller_id"] = row[0]
        session["reseller_name"] = row[1]
        return jsonify({
            "status": "success",
            "id": row[0],
            "name": row[1]
        })

    # 🔥 VERY IMPORTANT (missing tha)
    return jsonify({"status": "fail"})


# =========================
# =========================
# HOME (WEBSITE)
# =========================
@app.route("/")
def home():
    return render_template("index.html")


# =========================
# LOGIN (ADMIN)
# =========================
@app.route("/secure-login-749874", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == "admin" and request.form.get("password") == "1@amnsdbpoi":
            session["admin"] = True
            return redirect("/secure-admin-749874")
    return render_template("login.html")


# =========================
# ADMIN DASHBOARD
# =========================
@app.route("/secure-admin-749874")
def dashboard():
    if not session.get("admin"):
        return redirect("/secure-login-749874")
    return render_template("dashboard.html")


# =========================
# RESELLER LOGIN PAGE
# =========================
@app.route("/reseller")
def reseller_login_page():
    return render_template("reseller_login.html")


# =========================
# RESELLER DASHBOARD
# =========================
@app.route("/reseller/dashboard")
def reseller_dashboard_page():
    if not session.get("reseller"):
        return redirect("/reseller")
    return render_template("reseller_dashboard.html")


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

    conn = get_conn()
    cur = conn.cursor()

    # 🔥 DB CHECK
    cur.execute("SELECT status, expiry FROM licenses WHERE key=%s", (key,))
    row = cur.fetchone()

    conn.close()

    if not row:
        return jsonify({"status": "invalid"})

    status, expiry = row

    if status != "active":
        return jsonify({"status": "blocked"})

    # 🔥 HASH VALIDATION
    try:
        expiry_part, hash_part = key.split("-")

        raw = f"{machine}|{expiry}|{SECRET}"
        expected = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

        if hash_part == expected:
            return jsonify({"status": "success", "expiry": expiry})

    except:
        pass

    return jsonify({"status": "invalid"})

# =========================
# NEW CHECK (CONTROL)
# =========================
@app.route("/check", methods=["POST"])
def check():
    data = request.get_json()

    key = data.get("key")
    machine = data.get("machine", "").strip().upper()

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

    # 🔥 HASH VALIDATION ADD
    try:
        expiry_part, hash_part = key.split("-")

        raw = f"{machine}|{expiry}|{SECRET}"
        expected = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

        if hash_part == expected:
            return jsonify({"status": "success", "expiry": expiry})

    except:
        pass

    return jsonify({"status": "invalid"})


# =========================
# ADD KEY (FROM KEYGEN)
# =========================
@app.route("/add_key", methods=["POST"])
def add_key():
    data = request.get_json()

    key = data.get("key")
    machine = data.get("machine")
    expiry = data.get("expiry")
    customer_name = data.get("customer_name", "")
    customer_mobile = data.get("customer_mobile", "")
    reseller_id = data.get("reseller_id", None)

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO licenses 
            (key, machine, expiry, customer_name, customer_mobile, reseller_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (key, machine, expiry, customer_name, customer_mobile, reseller_id))

        conn.commit()
    except Exception as e:
        print("ADD KEY ERROR:", e)

    conn.close()
    return jsonify({"status": "saved"})
# =========================
# RESELLER GENERATE KEY
# =========================
# PRICE CONFIG
PRICE = {
    1: 50,
    12: 499,
    999: 2499   # lifetime
}
@app.route("/reseller/generate", methods=["POST"])
def reseller_generate():

    data = request.json

    reseller_id = int(data["reseller_id"])   # 🔥 FIX
    machine = data["machine"].upper()
    months = int(data["months"])
    customer_name = data.get("customer_name", "").strip()
    customer_mobile = data.get("customer_mobile", "").strip()

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT balance FROM resellers WHERE id=%s", (reseller_id,))
    
    row = cur.fetchone()   # 🔥 FIX
    if not row:
        return jsonify({"status": "error", "msg": "Reseller not found"})
    
    balance = row[0]

    price = PRICE.get(months, 50)

    if balance < price:
        return jsonify({"status": "no_balance"})

    if months == 999:
        expiry = "2099-12-31"
    else:
        expiry = (datetime.now() + timedelta(days=30*months)).strftime("%Y-%m-%d")

    raw = f"{machine}|{expiry}|{SECRET}"
    key = expiry.replace("-", "")[:6] + "-" + hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

    cur.execute("""
        INSERT INTO licenses 
        (key, machine, expiry, customer_name, customer_mobile, reseller_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        key,
        machine,
        expiry,
        customer_name,
        customer_mobile,
        reseller_id
    ))

    cur.execute("""
        INSERT INTO reseller_licenses (reseller_id, license_key, machine, expiry)
        VALUES (%s, %s, %s, %s)
    """, (reseller_id, key, machine, expiry))

    cur.execute("UPDATE resellers SET balance = balance - %s WHERE id=%s", (price, reseller_id))

    cur.execute("""
        INSERT INTO wallet_transactions (reseller_id, amount, type, note)
        VALUES (%s, %s, 'debit', 'License Generated')
    """, (reseller_id, price))

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "key": key, "expiry": expiry})

@app.route("/reseller/logout")
def reseller_logout():
    session.clear()
    return redirect("/reseller")


@app.route("/renew_key", methods=["POST"])
def renew_key():

    if not admin_required():
        return jsonify({"status":"unauthorized"}), 401

    data = request.get_json()
    key = data.get("key")
    months = int(data.get("months", 1))

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT machine FROM licenses WHERE key=%s", (key,))
    row = cur.fetchone()

    if not row:
        return jsonify({"status":"error","msg":"Key not found"})

    machine = row[0]

    new_expiry_date = datetime.now() + timedelta(days=30*months)
    expiry_str = new_expiry_date.strftime("%Y-%m-%d")

    expiry_part = new_expiry_date.strftime("%Y%m")

    raw = f"{machine}|{expiry_str}|{SECRET}"
    new_hash = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

    new_key = f"{expiry_part}-{new_hash}"

    cur.execute("""
        UPDATE licenses 
        SET key=%s, expiry=%s, status='active'
        WHERE key=%s
    """, (new_key, expiry_str, key))

    conn.commit()
    conn.close()

    return jsonify({"status":"success","new_key":new_key,"expiry":expiry_str})

@app.route("/delete_key", methods=["POST"])
def delete_key():

    if not admin_required():
        return jsonify({"status":"unauthorized"}), 401

    data = request.get_json()
    key = data.get("key")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM licenses WHERE key=%s", (key,))
    cur.execute("DELETE FROM reseller_licenses WHERE license_key=%s", (key,))

    conn.commit()
    conn.close()

    return jsonify({"status":"deleted"})

@app.route("/reseller/my_keys/<int:rid>")
def reseller_my_keys(rid):

    if not session.get("reseller"):
        return jsonify([])

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT rl.license_key, l.expiry, l.status, l.customer_name, l.customer_mobile, l.machine
        FROM reseller_licenses rl
        JOIN licenses l ON rl.license_key = l.key
        WHERE rl.reseller_id=%s
        ORDER BY rl.id DESC
    """, (rid,))

    data = cur.fetchall()
    conn.close()

    result = []
    for r in data:
        result.append({
            "key": r[0],
            "expiry": r[1],
            "status": r[2],
            "customer_name": r[3],
            "customer_mobile": r[4],
            "machine": r[5]
        })

    return jsonify(result)


# =========================
# ALL KEYS
# =========================
@app.route("/all_keys")
def all_keys():

    # 🔒 ADMIN SECURITY ADD HERE
    if not admin_required():
        return jsonify({"status":"unauthorized"}), 401

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            l.key, l.machine, l.status, l.expiry,
            l.customer_name, l.customer_mobile,
            r.name
        FROM licenses l
        LEFT JOIN resellers r ON l.reseller_id = r.id
        ORDER BY l.id DESC
    """)

    rows = cur.fetchall()

    conn.close()

    data = []
    for r in rows:
        data.append({
            "key": r[0],
            "machine": r[1],
            "status": r[2],
            "expiry": r[3],
            "customer_name": r[4],
            "customer_mobile": r[5],
            "reseller": r[6]
        })

    return jsonify(data)


# =========================
# DEACTIVATE
# =========================
@app.route("/deactivate", methods=["POST"])
def deactivate():
    if not admin_required():
        return jsonify({"status":"unauthorized"}), 401
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
    if not admin_required():
        return jsonify({"status":"unauthorized"}), 401
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
        "version": "2.7.1",
        "url": "https://github.com/kpvkpiyush7-cmd/license-server/releases/download/v2.7.1/update.zip"
    })


# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
