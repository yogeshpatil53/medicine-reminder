from datetime import date, datetime
from pathlib import Path
import re
import socket
import sys
from flask import Flask, jsonify, request, send_from_directory, session

from database import (
    add_contact,
    add_medicine,
    authenticate_user,
    delete_contact,
    delete_medicine,
    get_connection,
    get_contacts,
    get_medicines,
    get_patient_name,
    get_setting,
    get_stats,
    get_user_by_id,
    initialize_database,
    mark_medicine_reminded,
    mark_medicine_taken,
    normalise_12_hour_time,
    register_user,
    save_patient_name,
    save_setting,
    toggle_medicine_enabled,
    update_contact,
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
app.secret_key = "medremind_secure_session_key_secret_2026"



def get_lan_ip():
    """Detect the computer's local Wi-Fi or LAN IPv4 address."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


# ---------- STATIC & PWA ROUTES ----------

@app.route("/")
def serve_index():
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/manifest.json")
def serve_manifest():
    response = send_from_directory(str(STATIC_DIR), "manifest.json")
    response.headers["Content-Type"] = "application/manifest+json"
    return response


@app.route("/MedicineReminder.apk")
@app.route("/download-apk")
def serve_apk():
    apk_path = BASE_DIR / "MedicineReminder.apk"
    if apk_path.exists():
        return send_from_directory(
            str(BASE_DIR),
            "MedicineReminder.apk",
            as_attachment=True,
            mimetype="application/vnd.android.package-archive",
        )
    return jsonify({"error": "APK file not found"}), 404



@app.route("/sw.js")
def serve_sw():
    response = send_from_directory(str(STATIC_DIR), "sw.js")
    response.headers["Content-Type"] = "application/javascript"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@app.route("/logo.png")
def serve_logo():
    logo_file = STATIC_DIR / "logo.png"
    if not logo_file.exists():
        logo_file = STATIC_DIR / "logo.jpg"
    return send_from_directory(str(STATIC_DIR), logo_file.name)


# ---------- AUTH ROUTES ----------

@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    data = request.get_json(force=True, silent=True) or {}
    username = str(data.get("username", "")).strip()
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", "")).strip()

    if not username or not password or not name:
        return jsonify({"success": False, "error": "Name, username, and password are required."}), 400

    if not email:
        email = f"{username}@example.com"

    user, err = register_user(username, name, email, password)
    if err:
        return jsonify({"success": False, "error": err}), 400

    session["user_id"] = user["id"]
    return jsonify({
        "success": True,
        "message": f"Welcome, {user['name']}! Account created successfully.",
        "user": user,
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    data = request.get_json(force=True, silent=True) or {}
    identifier = str(data.get("username", "") or data.get("identifier", "")).strip()
    password = str(data.get("password", "")).strip()

    if not identifier or not password:
        return jsonify({"success": False, "error": "Username/Email and password are required."}), 400

    user = authenticate_user(identifier, password)
    if not user:
        return jsonify({"success": False, "error": "Invalid username or password. Please try again."}), 401

    session["user_id"] = user["id"]
    save_patient_name(user["name"])
    return jsonify({
        "success": True,
        "message": f"Welcome back, {user['name']}!",
        "user": user,
    })


@app.route("/api/auth/me", methods=["GET"])
def api_auth_me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": True, "authenticated": False, "user": None})
    user = get_user_by_id(user_id)
    if not user:
        session.pop("user_id", None)
        return jsonify({"success": True, "authenticated": False, "user": None})
    return jsonify({"success": True, "authenticated": True, "user": user})


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    session.pop("user_id", None)
    return jsonify({"success": True, "message": "Logged out successfully."})


# ---------- API ROUTES ----------

@app.route("/api/status", methods=["GET"])
def api_status():
    today = date.today().isoformat()
    now_12h = datetime.now().strftime("%I:%M %p")
    stats = get_stats()
    patient = get_patient_name()
    return jsonify({
        "success": True,
        "patient_name": patient,
        "current_date": today,
        "current_time": now_12h,
        "stats": stats,
    })


@app.route("/api/medicines", methods=["GET"])
def api_get_medicines():
    today = date.today().isoformat()
    rows = get_medicines()
    medicines = []
    for r in rows:
        d = dict(r)
        d["is_today"] = bool(d.get("repeat_daily") == 1 or d.get("start_date") == today)
        d["is_taken_today"] = bool(d.get("last_taken_date") == today)
        medicines.append(d)
    return jsonify({"success": True, "medicines": medicines})


@app.route("/api/medicines", methods=["POST"])
def api_add_medicine():
    data = request.get_json(force=True, silent=True) or {}
    name = str(data.get("name", "")).strip()
    dosage = str(data.get("dosage", "")).strip()
    reminder_time_raw = str(data.get("reminder_time", "")).strip()
    start_date = str(data.get("start_date", "")).strip() or date.today().isoformat()
    repeat_daily = 1 if data.get("repeat_daily", True) else 0
    notes = str(data.get("notes", "")).strip()

    if not name or not dosage or not reminder_time_raw:
        return jsonify({
            "success": False,
            "error": "Medicine name, dosage, and reminder time are required.",
        }), 400

    try:
        reminder_time = normalise_12_hour_time(reminder_time_raw)
    except Exception:
        return jsonify({
            "success": False,
            "error": "Invalid time format. Please use format like '08:30 AM' or '20:30'.",
        }), 400

    try:
        datetime.strptime(start_date, "%Y-%m-%d")
    except Exception:
        return jsonify({
            "success": False,
            "error": "Invalid start date format. Please use YYYY-MM-DD.",
        }), 400

    new_id = add_medicine(name, dosage, reminder_time, start_date, repeat_daily, notes)
    return jsonify({
        "success": True,
        "message": f"Medicine '{name}' scheduled for {reminder_time}.",
        "id": new_id,
    }), 201


@app.route("/api/medicines/<int:medicine_id>", methods=["DELETE"])
def api_delete_medicine(medicine_id):
    delete_medicine(medicine_id)
    return jsonify({"success": True, "message": "Medicine deleted."})


@app.route("/api/medicines/<int:medicine_id>/toggle", methods=["POST"])
def api_toggle_medicine(medicine_id):
    toggle_medicine_enabled(medicine_id)
    return jsonify({"success": True, "message": "Medicine status toggled."})


@app.route("/api/medicines/<int:medicine_id>/taken", methods=["POST"])
def api_mark_taken(medicine_id):
    data = request.get_json(force=True, silent=True) or {}
    is_taken = bool(data.get("taken", True))
    mark_medicine_taken(medicine_id, is_taken)
    return jsonify({"success": True, "taken": is_taken})


@app.route("/api/medicines/due", methods=["GET"])
def api_check_due():
    current_time = datetime.now().strftime("%I:%M %p")
    today = date.today().isoformat()

    with get_connection() as connection:
        due = connection.execute("""
            SELECT * FROM medicines
            WHERE enabled = 1
              AND reminder_time = ?
              AND (repeat_daily = 1 OR start_date = ?)
              AND COALESCE(last_reminded_date, '') != ?
        """, (current_time, today, today)).fetchall()

    items = [dict(m) for m in due]
    return jsonify({
        "success": True,
        "current_time": current_time,
        "due_medicines": items,
    })


@app.route("/api/medicines/<int:medicine_id>/ack-reminder", methods=["POST"])
def api_ack_reminder(medicine_id):
    today = date.today().isoformat()
    mark_medicine_reminded(medicine_id, today)
    return jsonify({"success": True, "message": "Reminder acknowledged."})


@app.route("/api/contacts", methods=["GET"])
def api_get_contacts():
    rows = get_contacts()
    return jsonify({"success": True, "contacts": [dict(r) for r in rows]})


@app.route("/api/contacts", methods=["POST"])
def api_add_contact():
    data = request.get_json(force=True, silent=True) or {}
    name = str(data.get("name", "")).strip()
    phone_number = str(data.get("phone_number", "")).strip()
    contact_type = str(data.get("contact_type", "Emergency Contact")).strip()
    address = str(data.get("address", "")).strip()
    relationship = str(data.get("relationship", "")).strip()

    if not name or not phone_number:
        return jsonify({
            "success": False,
            "error": "Name and phone number are required.",
        }), 400

    clean_phone = re.sub(r"[^0-9+]", "", phone_number)
    new_id = add_contact(name, relationship, clean_phone, contact_type, address)
    return jsonify({
        "success": True,
        "message": f"Contact '{name}' added.",
        "id": new_id,
    }), 201


@app.route("/api/contacts/<int:contact_id>", methods=["DELETE"])
def api_delete_contact(contact_id):
    delete_contact(contact_id)
    return jsonify({"success": True, "message": "Contact removed."})


@app.route("/api/contacts/<int:contact_id>", methods=["PUT", "POST"])
def api_update_contact(contact_id):
    data = request.get_json(force=True, silent=True) or {}
    name = str(data.get("name", "")).strip()
    phone_number = str(data.get("phone_number", "")).strip()
    contact_type = str(data.get("contact_type", "Emergency Contact")).strip()
    address = str(data.get("address", "")).strip()
    relationship = str(data.get("relationship", "")).strip()

    if not name or not phone_number:
        return jsonify({
            "success": False,
            "error": "Name and phone number are required.",
        }), 400

    clean_phone = re.sub(r"[^0-9+]", "", phone_number)
    update_contact(contact_id, name, relationship, clean_phone, contact_type, address)
    return jsonify({
        "success": True,
        "message": f"Contact '{name}' updated successfully.",
    })


@app.route("/api/settings/ringtone", methods=["GET"])
def api_get_ringtone():
    ringtone = get_setting("alarm_ringtone", "gentle-chime")
    return jsonify({"success": True, "ringtone": ringtone})


@app.route("/api/settings/ringtone", methods=["POST"])
def api_save_ringtone():
    data = request.get_json(force=True, silent=True) or {}
    ringtone = str(data.get("ringtone", "gentle-chime")).strip()
    save_setting("alarm_ringtone", ringtone)
    return jsonify({
        "success": True,
        "ringtone": ringtone,
        "message": "Alarm ringtone updated successfully.",
    })


@app.route("/api/settings/patient-name", methods=["POST"])
def api_set_patient_name():
    data = request.get_json(force=True, silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"success": False, "error": "Name cannot be empty."}), 400
    save_patient_name(name)
    return jsonify({"success": True, "patient_name": name})


@app.route("/api/network-info", methods=["GET"])
def api_network_info():
    ip = get_lan_ip()
    port = 5000
    return jsonify({
        "success": True,
        "lan_ip": ip,
        "port": port,
        "mobile_url": f"http://{ip}:{port}",
        "localhost_url": f"http://localhost:{port}",
    })


if __name__ == "__main__":
    initialize_database()
    lan_ip = get_lan_ip()
    port = 5000
    print("\n" + "=" * 60)
    print("  MEDICINE REMINDER - MOBILE PWA WEB SERVER")
    print("=" * 60)
    print(f"  Mobile URL (Open on your Phone):  http://{lan_ip}:{port}")
    print(f"  Local URL (Open on this PC):      http://localhost:{port}")
    print("  Works on any Android or iPhone connected to Wi-Fi!")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False)
