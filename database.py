from pathlib import Path
import sqlite3
import sys

if getattr(sys, "frozen", False):
    PROJECT_FOLDER = Path(sys.executable).resolve().parent
else:
    PROJECT_FOLDER = Path(__file__).resolve().parent

DATABASE_FILE = PROJECT_FOLDER / "data" / "medicine_reminder.db"


def get_connection():
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS medicines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dosage TEXT NOT NULL,
                reminder_time TEXT NOT NULL,
                start_date TEXT NOT NULL,
                repeat_daily INTEGER NOT NULL DEFAULT 1,
                notes TEXT DEFAULT '',
                enabled INTEGER NOT NULL DEFAULT 1,
                last_reminded_date TEXT DEFAULT '',
                last_taken_date TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS emergency_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                relationship TEXT DEFAULT '',
                phone_number TEXT NOT NULL,
                contact_type TEXT NOT NULL DEFAULT 'Emergency Contact',
                address TEXT DEFAULT ''
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Seed default user if empty
        user_count = connection.execute("SELECT count(*) as c FROM users").fetchone()["c"]
        if user_count == 0:
            import hashlib
            default_hash = hashlib.sha256("password123".encode("utf-8")).hexdigest()
            connection.execute("""
                INSERT OR IGNORE INTO users (username, name, email, password_hash)
                VALUES ('yogesh', 'Yogesh', 'yogesh@medremind.com', ?)
            """, (default_hash,))

        # Migration check for emergency_contacts columns
        contact_cols = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(emergency_contacts)"
            ).fetchall()
        }

        if "contact_type" not in contact_cols:
            connection.execute("""
                ALTER TABLE emergency_contacts
                ADD COLUMN contact_type TEXT NOT NULL
                DEFAULT 'Emergency Contact'
            """)

        if "address" not in contact_cols:
            connection.execute("""
                ALTER TABLE emergency_contacts
                ADD COLUMN address TEXT DEFAULT ''
            """)

        if "relationship" not in contact_cols:
            connection.execute("""
                ALTER TABLE emergency_contacts
                ADD COLUMN relationship TEXT DEFAULT ''
            """)

        # Migration check for medicines columns
        med_cols = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(medicines)"
            ).fetchall()
        }

        if "last_taken_date" not in med_cols:
            connection.execute("""
                ALTER TABLE medicines
                ADD COLUMN last_taken_date TEXT DEFAULT ''
            """)

        if "enabled" not in med_cols:
            connection.execute("""
                ALTER TABLE medicines
                ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1
            """)

        if "notes" not in med_cols:
            connection.execute("""
                ALTER TABLE medicines
                ADD COLUMN notes TEXT DEFAULT ''
            """)

        if "last_reminded_date" not in med_cols:
            connection.execute("""
                ALTER TABLE medicines
                ADD COLUMN last_reminded_date TEXT DEFAULT ''
            """)


def get_patient_name():
    with get_connection() as connection:
        row = connection.execute("""
            SELECT setting_value
            FROM app_settings
            WHERE setting_key = 'patient_name'
        """).fetchone()
    return row["setting_value"] if row else "Patient"


def save_patient_name(name):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO app_settings (setting_key, setting_value)
            VALUES ('patient_name', ?)
            ON CONFLICT(setting_key)
            DO UPDATE SET setting_value = excluded.setting_value
        """, (name.strip(),))


def get_setting(key, default=""):
    with get_connection() as connection:
        row = connection.execute("""
            SELECT setting_value
            FROM app_settings
            WHERE setting_key = ?
        """, (key,)).fetchone()
    return row["setting_value"] if row else default


def save_setting(key, value):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO app_settings (setting_key, setting_value)
            VALUES (?, ?)
            ON CONFLICT(setting_key)
            DO UPDATE SET setting_value = excluded.setting_value
        """, (key, str(value).strip()))


def get_medicines():
    with get_connection() as connection:
        return connection.execute("""
            SELECT * FROM medicines
            ORDER BY reminder_time, name
        """).fetchall()


def add_medicine(name, dosage, reminder_time, start_date, repeat_daily, notes):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO medicines
            (name, dosage, reminder_time, start_date, repeat_daily, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            dosage,
            reminder_time,
            start_date,
            repeat_daily,
            notes,
        ))

        return cursor.lastrowid


def delete_medicine(medicine_id):
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM medicines WHERE id = ?",
            (medicine_id,),
        )


def get_contacts():
    with get_connection() as connection:
        return connection.execute("""
            SELECT * FROM emergency_contacts
            ORDER BY
                CASE contact_type
                    WHEN 'Doctor' THEN 1
                    WHEN 'Ambulance' THEN 2
                    WHEN 'Nearby Medicine Store' THEN 3
                    ELSE 4
                END,
                name
        """).fetchall()


def get_first_contact_by_type(contact_type):
    with get_connection() as connection:
        return connection.execute("""
            SELECT * FROM emergency_contacts
            WHERE contact_type = ?
            ORDER BY id
            LIMIT 1
        """, (contact_type,)).fetchone()


def add_contact(name, relationship, phone_number, contact_type, address):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO emergency_contacts
            (name, relationship, phone_number, contact_type, address)
            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            relationship,
            phone_number,
            contact_type,
            address,
        ))

        return cursor.lastrowid


def delete_contact(contact_id):
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM emergency_contacts WHERE id = ?",
            (contact_id,),
        )


def update_contact(contact_id, name, relationship, phone_number, contact_type, address):
    with get_connection() as connection:
        connection.execute("""
            UPDATE emergency_contacts
            SET name = ?, relationship = ?, phone_number = ?, contact_type = ?, address = ?
            WHERE id = ?
        """, (
            name,
            relationship,
            phone_number,
            contact_type,
            address,
            contact_id,
        ))


def toggle_medicine_enabled(medicine_id):
    with get_connection() as connection:
        connection.execute("""
            UPDATE medicines
            SET enabled = CASE WHEN enabled = 1 THEN 0 ELSE 1 END
            WHERE id = ?
        """, (medicine_id,))


def mark_medicine_taken(medicine_id, is_taken):
    from datetime import date
    today = date.today().isoformat()
    value = today if is_taken else ""
    with get_connection() as connection:
        connection.execute("""
            UPDATE medicines
            SET last_taken_date = ?
            WHERE id = ?
        """, (value, medicine_id))


def mark_medicine_reminded(medicine_id, today_iso):
    with get_connection() as connection:
        connection.execute("""
            UPDATE medicines
            SET last_reminded_date = ?
            WHERE id = ?
        """, (today_iso, medicine_id))


def normalise_12_hour_time(value):
    from datetime import datetime
    val = value.strip().upper()
    try:
        return datetime.strptime(val, "%I:%M %p").strftime("%I:%M %p")
    except ValueError:
        return datetime.strptime(val, "%H:%M").strftime("%I:%M %p")


def get_today_medicines():
    from datetime import date
    today = date.today().isoformat()
    with get_connection() as connection:
        return connection.execute("""
            SELECT * FROM medicines
            WHERE (repeat_daily = 1 OR start_date = ?)
            ORDER BY
                (CASE WHEN substr(reminder_time, 7, 2) = 'PM' THEN 12 ELSE 0 END
                 + CASE WHEN substr(reminder_time, 1, 2) = '12' THEN 0
                        ELSE CAST(substr(reminder_time, 1, 2) AS INTEGER) END) * 60
                + CAST(substr(reminder_time, 4, 2) AS INTEGER)
        """, (today,)).fetchall()


def get_due_medicines(current_time_12h, today_iso):
    with get_connection() as connection:
        return connection.execute("""
            SELECT * FROM medicines
            WHERE enabled = 1
              AND reminder_time = ?
              AND (repeat_daily = 1 OR start_date = ?)
              AND COALESCE(last_reminded_date, '') != ?
        """, (current_time_12h, today_iso, today_iso)).fetchall()


def get_stats():
    from datetime import date
    today = date.today().isoformat()
    with get_connection() as connection:
        all_meds = connection.execute("SELECT count(*) as c FROM medicines").fetchone()["c"]
        contacts = connection.execute("SELECT count(*) as c FROM emergency_contacts").fetchone()["c"]
        today_meds = connection.execute("""
            SELECT count(*) as total,
                   SUM(CASE WHEN last_taken_date = ? THEN 1 ELSE 0 END) as taken
            FROM medicines
            WHERE enabled = 1 AND (repeat_daily = 1 OR start_date = ?)
        """, (today, today)).fetchone()

        total_today = today_meds["total"] or 0
        taken_today = today_meds["taken"] or 0
        pending_today = max(0, total_today - taken_today)

        return {
            "all_medicines": all_meds,
            "today_total": total_today,
            "today_taken": taken_today,
            "today_pending": pending_today,
            "contacts_count": contacts,
        }


# ---------- AUTHENTICATION ----------

def hash_password(password):
    import hashlib
    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()


def register_user(username, name, email, password):
    username = username.strip().lower()
    email = email.strip().lower()
    name = name.strip()

    if not username or not email or not password or not name:
        return None, "All fields (Full Name, Username, Email, Password) are required."

    pwd_hash = hash_password(password)

    try:
        with get_connection() as connection:
            cursor = connection.execute("""
                INSERT INTO users (username, name, email, password_hash)
                VALUES (?, ?, ?, ?)
            """, (username, name, email, pwd_hash))
            user_id = cursor.lastrowid
            connection.execute("""
                INSERT INTO app_settings (setting_key, setting_value)
                VALUES ('patient_name', ?)
                ON CONFLICT(setting_key)
                DO UPDATE SET setting_value = excluded.setting_value
            """, (name.strip(),))
            
        return {
            "id": user_id,
            "username": username,
            "name": name,
            "email": email,
        }, None
    except sqlite3.IntegrityError as e:
        err_msg = str(e).lower()
        if "username" in err_msg:
            return None, "Username is already taken. Please choose another."
        elif "email" in err_msg:
            return None, "An account with this email already exists."
        return None, "Account already exists with this username or email."


def authenticate_user(identifier, password):
    identifier = identifier.strip().lower()
    pwd_hash = hash_password(password)

    with get_connection() as connection:
        user = connection.execute("""
            SELECT id, username, name, email, password_hash
            FROM users
            WHERE (LOWER(username) = ? OR LOWER(email) = ?)
              AND password_hash = ?
        """, (identifier, identifier, pwd_hash)).fetchone()

    if user:
        d = dict(user)
        del d["password_hash"]
        return d
    return None


def get_user_by_id(user_id):
    with get_connection() as connection:
        user = connection.execute("""
            SELECT id, username, name, email
            FROM users
            WHERE id = ?
        """, (user_id,)).fetchone()
    return dict(user) if user else None


if __name__ == "__main__":
    initialize_database()
    print(f"Database ready: {DATABASE_FILE}")