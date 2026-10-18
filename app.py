import re
import sqlite3
import sys
import webbrowser
import winsound
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

try:
    from plyer import notification
except ImportError:
    notification = None


# ---------- COLOURS ----------

BG = "#F4F7FC"
WHITE = "#FFFFFF"
DARK = "#15213B"
BLUE = "#2864E8"
PURPLE = "#5938D9"
GREEN = "#009E73"
RED = "#E53935"
ORANGE = "#F4A300"
MUTED = "#667894"
LIGHT_BLUE = "#EAF1FF"
LIGHT_GREEN = "#E6F8F1"
BORDER = "#DCE5F3"


# ---------- FILE PATHS ----------

if getattr(sys, "frozen", False):
    PROJECT_FOLDER = Path(sys.executable).resolve().parent
else:
    PROJECT_FOLDER = Path(__file__).resolve().parent

DATABASE_FILE = PROJECT_FOLDER / "data" / "medicine_reminder.db"
CUSTOM_ALARM_FILE = (
    PROJECT_FOLDER / "assets" / "sounds" / "medicine_alarm.wav"
)


# ---------- DATABASE ----------

def get_connection():
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def normalise_12_hour_time(value):
    """Return a time as HH:MM AM/PM, for example 07:30 PM."""
    return datetime.strptime(
        value.strip().upper(),
        "%I:%M %p",
    ).strftime("%I:%M %p")


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
                last_reminded_date TEXT DEFAULT ''
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS emergency_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                contact_type TEXT NOT NULL,
                address TEXT DEFAULT ''
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
        """)

        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(emergency_contacts)"
            ).fetchall()
        }

        if "contact_type" not in columns:
            connection.execute("""
                ALTER TABLE emergency_contacts
                ADD COLUMN contact_type TEXT DEFAULT 'Emergency Contact'
            """)

        if "address" not in columns:
            connection.execute("""
                ALTER TABLE emergency_contacts
                ADD COLUMN address TEXT DEFAULT ''
            """)

        # Convert older 24-hour times (for example 21:30) to the 12-hour
        # format used everywhere in this app: 09:30 PM.
        medicines = connection.execute("""
            SELECT id, reminder_time
            FROM medicines
        """).fetchall()

        for medicine in medicines:
            try:
                normalized_time = normalise_12_hour_time(
                    medicine["reminder_time"]
                )
            except ValueError:
                try:
                    normalized_time = datetime.strptime(
                        medicine["reminder_time"].strip(),
                        "%H:%M",
                    ).strftime("%I:%M %p")
                except ValueError:
                    continue

            if normalized_time != medicine["reminder_time"]:
                connection.execute("""
                    UPDATE medicines
                    SET reminder_time = ?
                    WHERE id = ?
                """, (normalized_time, medicine["id"]))


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
        """, (name,))


# ---------- APP ----------

class MedicineReminderApp:
    CONTACT_TYPES = (
        "Doctor",
        "Ambulance",
        "Nearby Medicine Store",
        "Emergency Contact",
    )

    def __init__(self, root):
        self.root = root
        self.root.title("MedRemind - Smart Health")
        self.root.geometry("1150x720")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG)

        self.alarm_window = None
        self.alarm_active = False
        self.current_page = "schedule"
        self.nav_buttons = {}

        initialize_database()
        self.patient_name = get_patient_name()

        self.create_header()
        self.create_navigation()

        self.content = tk.Frame(self.root, bg=BG)
        self.content.pack(fill="both", expand=True, padx=28, pady=20)

        self.status = tk.Label(
            self.root,
            text="Medicine Reminder is running.",
            bg=WHITE,
            fg=GREEN,
            anchor="w",
            padx=28,
            pady=9,
            font=("Segoe UI", 9),
        )
        self.status.pack(fill="x", side="bottom")

        self.show_schedule()
        self.update_clock()
        self.check_reminders()

    # ---------- UI HELPERS ----------

    def button(self, parent, text, command, bg=BLUE, fg=WHITE):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=bg,
            activeforeground=fg,
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=16,
            pady=9,
        )

    def card(self, parent, bg=WHITE):
        return tk.Frame(
            parent,
            bg=bg,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

    def set_status(self, text, color=GREEN):
        self.status.config(text=text, fg=color)

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    # ---------- HEADER ----------

    def create_header(self):
        header = tk.Frame(self.root, bg=WHITE, height=82)
        header.pack(fill="x")
        header.pack_propagate(False)

        left = tk.Frame(header, bg=WHITE)
        left.pack(side="left", padx=30, pady=14)

        tk.Label(
            left,
            text="MR",
            bg=BLUE,
            fg=WHITE,
            font=("Segoe UI", 16, "bold"),
            width=4,
            height=2,
        ).pack(side="left")

        title = tk.Frame(left, bg=WHITE)
        title.pack(side="left", padx=12)

        tk.Label(
            title,
            text="MedRemind",
            bg=WHITE,
            fg=DARK,
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")

        tk.Label(
            title,
            text="Medicine Reminder & Emergency Assistant",
            bg=WHITE,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        right = tk.Frame(header, bg=WHITE)
        right.pack(side="right", padx=30, pady=12)

        self.clock_label = tk.Label(
            right,
            bg=WHITE,
            fg=DARK,
            font=("Segoe UI", 16, "bold"),
        )
        self.clock_label.pack()

        self.date_label = tk.Label(
            right,
            bg=WHITE,
            fg=MUTED,
            font=("Segoe UI", 9),
        )
        self.date_label.pack()

        self.patient_name_button = tk.Button(
            header,
            text=f"Patient: {self.patient_name}",
            command=self.open_patient_name_form,
            bg=LIGHT_BLUE,
            fg=BLUE,
            activebackground=LIGHT_BLUE,
            activeforeground=BLUE,
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=8,
        )
        self.patient_name_button.pack(side="right", padx=(0, 16), pady=20)

    def update_clock(self):
        now = datetime.now()
        self.clock_label.config(text=now.strftime("%I:%M:%S %p"))
        self.date_label.config(text=now.strftime("%A, %d %B %Y"))
        self.root.after(1000, self.update_clock)

    def create_navigation(self):
        nav = tk.Frame(self.root, bg=WHITE)
        nav.pack(fill="x")

        items = [
            ("Today's Schedule", self.show_schedule, "schedule"),
            ("Medicines", self.show_medicines, "medicines"),
            ("Doctor & Emergency", self.show_contacts, "contacts"),
        ]

        for text, command, page in items:
            button = tk.Button(
                nav,
                text=text,
                command=command,
                bg=WHITE,
                fg=DARK,
                activebackground=LIGHT_BLUE,
                activeforeground=BLUE,
                relief="flat",
                cursor="hand2",
                font=("Segoe UI", 10, "bold"),
                padx=22,
                pady=12,
            )
            button.pack(side="left", padx=(28 if page == "schedule" else 4, 4))
            self.nav_buttons[page] = button

        self.update_navigation()

    def update_navigation(self):
        for page, button in self.nav_buttons.items():
            if page == self.current_page:
                button.config(bg=BLUE, fg=WHITE)
            else:
                button.config(bg=WHITE, fg=DARK)

    # ---------- SCHEDULE PAGE ----------

    def show_schedule(self):
        self.current_page = "schedule"
        self.update_navigation()
        self.clear_content()

        banner = tk.Frame(self.content, bg=PURPLE, height=155)
        banner.pack(fill="x", pady=(0, 20))
        banner.pack_propagate(False)

        left = tk.Frame(banner, bg=PURPLE)
        left.pack(side="left", padx=28, pady=25)

        tk.Label(
            left,
            text="PERSONAL HEALTH DASHBOARD",
            bg=PURPLE,
            fg="#DDE7FF",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        tk.Label(
            left,
            text=f"Welcome, {self.patient_name}",
            bg=PURPLE,
            fg=WHITE,
            font=("Segoe UI", 27, "bold"),
        ).pack(anchor="w", pady=(8, 2))

        tk.Label(
            left,
            text="Your medicines are scheduled on time. Stay healthy.",
            bg=PURPLE,
            fg=WHITE,
            font=("Segoe UI", 11),
        ).pack(anchor="w")

        buttons = tk.Frame(banner, bg=PURPLE)
        buttons.pack(side="right", padx=25, pady=52)

        self.button(
            buttons,
            "Test Alarm Now",
            self.test_alarm,
            ORANGE,
            DARK,
        ).pack(side="right", padx=5)

        self.button(
            buttons,
            "Test Notification",
            self.test_notification,
            GREEN,
        ).pack(side="right", padx=5)

        self.button(
            buttons,
            "+ Add Medicine",
            self.open_medicine_form,
            BLUE,
        ).pack(side="right", padx=5)

        self.button(
            buttons,
            "Edit Patient Name",
            self.open_patient_name_form,
            WHITE,
            PURPLE,
        ).pack(side="right", padx=5)

        medicines = self.get_today_medicines()

        stats = tk.Frame(self.content, bg=BG)
        stats.pack(fill="x", pady=(0, 18))

        self.stat_card(
            stats,
            "TODAY'S DOSES",
            str(len(medicines)),
            "Medicine reminders today",
            BLUE,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.stat_card(
            stats,
            "ALARM",
            "ON",
            "Custom ringtone enabled",
            GREEN,
        ).pack(side="left", fill="x", expand=True, padx=8)

        self.stat_card(
            stats,
            "EMERGENCY",
            "SOS",
            "Doctor and ambulance contacts",
            RED,
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

        heading = tk.Frame(self.content, bg=BG)
        heading.pack(fill="x", pady=(0, 10))

        tk.Label(
            heading,
            text="Today's Medication Timeline",
            bg=BG,
            fg=DARK,
            font=("Segoe UI", 18, "bold"),
        ).pack(side="left")

        if not medicines:
            empty = self.card(self.content)
            empty.pack(fill="x", pady=10)

            tk.Label(
                empty,
                text="No medicines scheduled. Click Add Medicine to begin.",
                bg=WHITE,
                fg=MUTED,
                font=("Segoe UI", 13),
                pady=35,
            ).pack()
            return

        for medicine in medicines:
            row = self.card(self.content)
            row.pack(fill="x", pady=6)

            tk.Label(
                row,
                text=medicine["reminder_time"],
                bg=LIGHT_BLUE,
                fg=BLUE,
                font=("Segoe UI", 12, "bold"),
                padx=16,
                pady=12,
            ).pack(side="left", padx=15, pady=12)

            info = tk.Frame(row, bg=WHITE)
            info.pack(side="left", fill="x", expand=True, pady=12)

            tk.Label(
                info,
                text=medicine["name"],
                bg=WHITE,
                fg=DARK,
                font=("Segoe UI", 14, "bold"),
            ).pack(anchor="w")

            tk.Label(
                info,
                text=f"Dosage: {medicine['dosage']}",
                bg=WHITE,
                fg=MUTED,
                font=("Segoe UI", 10),
            ).pack(anchor="w")

    def stat_card(self, parent, title, value, subtitle, color):
        card = self.card(parent)

        tk.Label(
            card,
            text=title,
            bg=WHITE,
            fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=18, pady=(16, 5))

        tk.Label(
            card,
            text=value,
            bg=WHITE,
            fg=color,
            font=("Segoe UI", 25, "bold"),
        ).pack(anchor="w", padx=18)

        tk.Label(
            card,
            text=subtitle,
            bg=WHITE,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=18, pady=(4, 16))

        return card

    # ---------- MEDICINE PAGE ----------

    def show_medicines(self):
        self.current_page = "medicines"
        self.update_navigation()
        self.clear_content()

        top = tk.Frame(self.content, bg=BG)
        top.pack(fill="x", pady=(0, 16))

        tk.Label(
            top,
            text="Medicines & Dosage",
            bg=BG,
            fg=DARK,
            font=("Segoe UI", 22, "bold"),
        ).pack(side="left")

        self.button(
            top,
            "+ Add Medicine",
            self.open_medicine_form,
        ).pack(side="right")

        medicines = self.get_all_medicines()

        if not medicines:
            tk.Label(
                self.content,
                text="No medicines added yet.",
                bg=BG,
                fg=MUTED,
                font=("Segoe UI", 13),
            ).pack(pady=40)
            return

        for medicine in medicines:
            row = self.card(self.content)
            row.pack(fill="x", pady=6)

            text = tk.Frame(row, bg=WHITE)
            text.pack(side="left", fill="x", expand=True, padx=20, pady=15)

            tk.Label(
                text,
                text=medicine["name"],
                bg=WHITE,
                fg=DARK,
                font=("Segoe UI", 14, "bold"),
            ).pack(anchor="w")

            repeat = "Daily" if medicine["repeat_daily"] else "One Time"

            tk.Label(
                text,
                text=(
                    f"Dosage: {medicine['dosage']}  |  "
                    f"Time: {medicine['reminder_time']}  |  {repeat}"
                ),
                bg=WHITE,
                fg=MUTED,
                font=("Segoe UI", 10),
            ).pack(anchor="w", pady=(4, 0))

            self.button(
                row,
                "Delete",
                lambda medicine_id=medicine["id"]: self.delete_medicine(
                    medicine_id
                ),
                RED,
            ).pack(side="right", padx=18, pady=15)

    # ---------- CONTACT PAGE ----------

    def show_contacts(self):
        self.current_page = "contacts"
        self.update_navigation()
        self.clear_content()

        tk.Label(
            self.content,
            text="Doctor & Emergency Contacts",
            bg=BG,
            fg=DARK,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w", pady=(0, 14))

        emergency = tk.Frame(self.content, bg=RED)
        emergency.pack(fill="x", pady=(0, 18))

        tk.Label(
            emergency,
            text="SOS Emergency Quick Calls",
            bg=RED,
            fg=WHITE,
            font=("Segoe UI", 16, "bold"),
            padx=20,
            pady=18,
        ).pack(side="left")

        call_buttons = tk.Frame(emergency, bg=RED)
        call_buttons.pack(side="right", padx=18, pady=12)

        self.button(
            call_buttons,
            "Call Doctor",
            lambda: self.call_category("Doctor"),
            WHITE,
            RED,
        ).pack(side="left", padx=4)

        self.button(
            call_buttons,
            "Call Ambulance",
            lambda: self.call_category("Ambulance"),
            WHITE,
            RED,
        ).pack(side="left", padx=4)

        self.button(
            call_buttons,
            "Call Medicine Store",
            lambda: self.call_category("Nearby Medicine Store"),
            WHITE,
            RED,
        ).pack(side="left", padx=4)

        top = tk.Frame(self.content, bg=BG)
        top.pack(fill="x", pady=(0, 10))

        tk.Label(
            top,
            text="Saved Contacts",
            bg=BG,
            fg=DARK,
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        self.button(
            top,
            "+ Add Contact",
            self.open_contact_form,
        ).pack(side="right")

        contacts = self.get_contacts()

        if not contacts:
            tk.Label(
                self.content,
                text="Add doctor, ambulance, and nearby medicine store numbers.",
                bg=BG,
                fg=MUTED,
                font=("Segoe UI", 12),
                pady=30,
            ).pack()
            return

        for contact in contacts:
            row = self.card(self.content)
            row.pack(fill="x", pady=6)

            text = tk.Frame(row, bg=WHITE)
            text.pack(side="left", fill="x", expand=True, padx=20, pady=14)

            tk.Label(
                text,
                text=f"{contact['name']} - {contact['contact_type']}",
                bg=WHITE,
                fg=DARK,
                font=("Segoe UI", 13, "bold"),
            ).pack(anchor="w")

            tk.Label(
                text,
                text=f"{contact['phone_number']}   {contact['address']}",
                bg=WHITE,
                fg=MUTED,
                font=("Segoe UI", 10),
            ).pack(anchor="w", pady=(4, 0))

            self.button(
                row,
                "Call",
                lambda name=contact["name"], number=contact["phone_number"]:
                    self.confirm_and_call(name, number),
                GREEN,
            ).pack(side="right", padx=5, pady=14)

            self.button(
                row,
                "Delete",
                lambda contact_id=contact["id"]: self.delete_contact(
                    contact_id
                ),
                RED,
            ).pack(side="right", padx=(5, 18), pady=14)

    # ---------- POPUP FORMS ----------

    def open_patient_name_form(self):
        window = tk.Toplevel(self.root)
        window.title("Patient Name")
        window.geometry("400x240")
        window.configure(bg=BG)
        window.transient(self.root)
        window.grab_set()

        tk.Label(
            window,
            text="Patient Name",
            bg=BG,
            fg=DARK,
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(25, 10))

        tk.Label(
            window,
            text="Enter the patient's name for the dashboard.",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack()

        name_var = tk.StringVar(value=self.patient_name)
        name_entry = tk.Entry(
            window,
            textvariable=name_var,
            font=("Segoe UI", 12),
        )
        name_entry.pack(fill="x", padx=38, pady=18, ipady=7)
        name_entry.focus_set()

        def save_name():
            name = name_var.get().strip()

            if not name:
                messagebox.showerror(
                    "Name required",
                    "Enter the patient name.",
                )
                return

            self.patient_name = name
            save_patient_name(name)
            self.patient_name_button.config(text=f"Patient: {name}")
            window.destroy()
            self.show_schedule()
            self.set_status(f"Patient name saved: {name}")

        self.button(
            window,
            "Save Patient Name",
            save_name,
            BLUE,
        ).pack(padx=38, fill="x")

    def open_medicine_form(self):
        window = tk.Toplevel(self.root)
        window.title("Add Medicine")
        window.geometry("450x510")
        window.minsize(450, 510)
        window.configure(bg=BG)
        window.transient(self.root)
        window.grab_set()

        tk.Label(
            window,
            text="Add Medicine",
            bg=BG,
            fg=DARK,
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(20, 12))

        form = tk.Frame(window, bg=WHITE, padx=24, pady=14)
        form.pack(fill="x", padx=22, pady=(0, 10))

        name = tk.StringVar()
        dosage = tk.StringVar()
        reminder_time = tk.StringVar()
        start_date = tk.StringVar(value=date.today().isoformat())
        daily = tk.IntVar(value=1)

        for label, variable in [
            ("Medicine Name", name),
            ("Dosage", dosage),
            ("Time (HH:MM AM/PM)", reminder_time),
            ("Start Date (YYYY-MM-DD)", start_date),
        ]:
            tk.Label(
                form,
                text=label,
                bg=WHITE,
                fg=DARK,
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w", pady=(6, 2))

            tk.Entry(
                form,
                textvariable=variable,
                font=("Segoe UI", 11),
            ).pack(fill="x", ipady=5)

        tk.Checkbutton(
            form,
            text="Repeat Every Day",
            variable=daily,
            bg=WHITE,
            activebackground=WHITE,
        ).pack(anchor="w", pady=10)

        def save():
            try:
                normalized_time = normalise_12_hour_time(
                    reminder_time.get()
                )
                datetime.strptime(start_date.get().strip(), "%Y-%m-%d")
            except ValueError:
                messagebox.showerror(
                    "Invalid Format",
                    "Use 12-hour time, for example 07:30 PM,\n"
                    "and date YYYY-MM-DD.",
                )
                return

            if not name.get().strip() or not dosage.get().strip():
                messagebox.showerror(
                    "Missing Details",
                    "Enter medicine name and dosage.",
                )
                return

            with get_connection() as connection:
                connection.execute("""
                    INSERT INTO medicines
                    (name, dosage, reminder_time, start_date, repeat_daily)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    name.get().strip(),
                    dosage.get().strip(),
                    normalized_time,
                    start_date.get().strip(),
                    daily.get(),
                ))

            window.destroy()
            self.show_schedule()
            self.set_status("Medicine added successfully.")

        self.button(window, "Save Medicine", save).pack(
            fill="x",
            padx=44,
            pady=(0, 20),
        )

    def open_contact_form(self):
        window = tk.Toplevel(self.root)
        window.title("Add Contact")
        window.geometry("450x430")
        window.configure(bg=BG)
        window.transient(self.root)
        window.grab_set()

        tk.Label(
            window,
            text="Add Emergency Contact",
            bg=BG,
            fg=DARK,
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(20, 12))

        form = tk.Frame(window, bg=WHITE, padx=24, pady=18)
        form.pack(fill="both", expand=True, padx=22, pady=(0, 22))

        name = tk.StringVar()
        phone = tk.StringVar()
        contact_type = tk.StringVar(value="Doctor")
        address = tk.StringVar()

        for label, variable in [
            ("Name", name),
            ("Phone Number", phone),
            ("Nearby Area / Address", address),
        ]:
            tk.Label(
                form,
                text=label,
                bg=WHITE,
                fg=DARK,
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w", pady=(6, 2))

            tk.Entry(
                form,
                textvariable=variable,
                font=("Segoe UI", 11),
            ).pack(fill="x", ipady=5)

        tk.Label(
            form,
            text="Contact Type",
            bg=WHITE,
            fg=DARK,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(8, 2))

        tk.OptionMenu(
            form,
            contact_type,
            *self.CONTACT_TYPES,
        ).pack(fill="x")

        def save():
            if not name.get().strip() or not phone.get().strip():
                messagebox.showerror(
                    "Missing Details",
                    "Enter contact name and phone number.",
                )
                return

            with get_connection() as connection:
                connection.execute("""
                    INSERT INTO emergency_contacts
                    (name, phone_number, contact_type, address)
                    VALUES (?, ?, ?, ?)
                """, (
                    name.get().strip(),
                    phone.get().strip(),
                    contact_type.get(),
                    address.get().strip(),
                ))

            window.destroy()
            self.show_contacts()
            self.set_status("Contact added successfully.")

        self.button(form, "Save Contact", save).pack(
            fill="x",
            pady=(12, 0),
        )

    # ---------- DATABASE FUNCTIONS ----------

    def get_today_medicines(self):
        today = date.today().isoformat()

        with get_connection() as connection:
            return connection.execute("""
                SELECT * FROM medicines
                WHERE repeat_daily = 1 OR start_date = ?
                ORDER BY
                    (CASE WHEN substr(reminder_time, 7, 2) = 'PM'
                          THEN 12 ELSE 0 END
                     + CASE WHEN substr(reminder_time, 1, 2) = '12'
                            THEN 0
                            ELSE CAST(substr(reminder_time, 1, 2) AS INTEGER)
                       END) * 60
                    + CAST(substr(reminder_time, 4, 2) AS INTEGER)
            """, (today,)).fetchall()

    def get_all_medicines(self):
        with get_connection() as connection:
            return connection.execute("""
                SELECT * FROM medicines
                ORDER BY
                    (CASE WHEN substr(reminder_time, 7, 2) = 'PM'
                          THEN 12 ELSE 0 END
                     + CASE WHEN substr(reminder_time, 1, 2) = '12'
                            THEN 0
                            ELSE CAST(substr(reminder_time, 1, 2) AS INTEGER)
                       END) * 60
                    + CAST(substr(reminder_time, 4, 2) AS INTEGER)
            """).fetchall()

    def get_contacts(self):
        with get_connection() as connection:
            return connection.execute("""
                SELECT * FROM emergency_contacts
                ORDER BY contact_type, name
            """).fetchall()

    def delete_medicine(self, medicine_id):
        if messagebox.askyesno(
            "Delete Medicine",
            "Do you want to delete this medicine?",
        ):
            with get_connection() as connection:
                connection.execute(
                    "DELETE FROM medicines WHERE id = ?",
                    (medicine_id,),
                )

            self.show_medicines()
            self.set_status("Medicine deleted.", RED)

    def delete_contact(self, contact_id):
        if messagebox.askyesno(
            "Delete Contact",
            "Do you want to delete this contact?",
        ):
            with get_connection() as connection:
                connection.execute(
                    "DELETE FROM emergency_contacts WHERE id = ?",
                    (contact_id,),
                )

            self.show_contacts()
            self.set_status("Contact deleted.", RED)

    # ---------- CALL FUNCTIONS ----------

    def call_category(self, contact_type):
        with get_connection() as connection:
            contact = connection.execute("""
                SELECT * FROM emergency_contacts
                WHERE contact_type = ?
                LIMIT 1
            """, (contact_type,)).fetchone()

        if not contact:
            messagebox.showwarning(
                "Contact Missing",
                f"Add a {contact_type} contact first.",
            )
            return

        self.confirm_and_call(
            contact["name"],
            contact["phone_number"],
        )

    def confirm_and_call(self, name, number):
        if not messagebox.askyesno(
            "Confirm Call",
            f"Open calling application for {name}?\n\n{number}",
        ):
            return

        number = re.sub(r"[^0-9+]", "", number)

        try:
            webbrowser.open(f"tel:{number}")
            self.set_status(f"Calling application opened for {name}.")
        except Exception as error:
            messagebox.showerror("Call Error", str(error))

    # ---------- ALARM ----------

    def check_reminders(self):
        current_time = datetime.now().strftime("%I:%M %p")
        today = date.today().isoformat()

        with get_connection() as connection:
            due_medicines = connection.execute("""
                SELECT * FROM medicines
                WHERE reminder_time = ?
                  AND (repeat_daily = 1 OR start_date = ?)
                  AND COALESCE(last_reminded_date, '') != ?
            """, (
                current_time,
                today,
                today,
            )).fetchall()

            for medicine in due_medicines:
                connection.execute("""
                    UPDATE medicines
                    SET last_reminded_date = ?
                    WHERE id = ?
                """, (
                    today,
                    medicine["id"],
                ))

        if due_medicines:
            self.show_notification(due_medicines)
            self.show_alarm(due_medicines)

        self.root.after(15000, self.check_reminders)

    def show_notification(self, medicines):
        if notification is None:
            return False

        names = ", ".join(medicine["name"] for medicine in medicines)

        try:
            notification.notify(
                title="Medicine Reminder",
                message=f"Time to take: {names}",
                app_name="MedRemind",
                timeout=10,
            )
            return True
        except Exception as error:
            self.set_status(f"Notification error: {error}", RED)
            return False

    def test_notification(self):
        sent = self.show_notification([
            {"name": "Test Medicine"}
        ])

        if sent:
            messagebox.showinfo(
                "Notification sent",
                "Check the Windows notification area now.",
            )
        else:
            messagebox.showwarning(
                "Notification unavailable",
                "Install plyer and allow notifications for Python or MedRemind "
                "in Windows Settings.",
            )

    def test_alarm(self):
        self.show_alarm([
            {
                "name": "Test Medicine",
                "dosage": "1 tablet",
            }
        ])

    def show_alarm(self, medicines):
        if self.alarm_active:
            return

        self.alarm_active = True

        try:
            if CUSTOM_ALARM_FILE.exists():
                winsound.PlaySound(
                    str(CUSTOM_ALARM_FILE),
                    winsound.SND_FILENAME
                    | winsound.SND_ASYNC
                    | winsound.SND_LOOP,
                )
            else:
                winsound.PlaySound(
                    "SystemExclamation",
                    winsound.SND_ALIAS
                    | winsound.SND_ASYNC
                    | winsound.SND_LOOP,
                )
        except RuntimeError:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)

        self.alarm_window = tk.Toplevel(self.root)
        self.alarm_window.title("Medicine Alarm")
        self.alarm_window.geometry("500x330")
        self.alarm_window.configure(bg=ORANGE)
        self.alarm_window.attributes("-topmost", True)
        self.alarm_window.protocol(
            "WM_DELETE_WINDOW",
            self.stop_alarm,
        )

        tk.Label(
            self.alarm_window,
            text="MEDICINE REMINDER",
            bg=ORANGE,
            fg=DARK,
            font=("Segoe UI", 22, "bold"),
        ).pack(pady=(30, 10))

        tk.Label(
            self.alarm_window,
            text="Alarm will ring until you stop it.",
            bg=ORANGE,
            fg=DARK,
            font=("Segoe UI", 11),
        ).pack()

        details = "\n".join(
            f"• {medicine['name']} - {medicine['dosage']}"
            for medicine in medicines
        )

        tk.Label(
            self.alarm_window,
            text=details,
            bg=ORANGE,
            fg=DARK,
            font=("Segoe UI", 14, "bold"),
            justify="left",
        ).pack(pady=25)

        self.button(
            self.alarm_window,
            "Stop Alarm",
            self.stop_alarm,
            RED,
        ).pack(fill="x", padx=45)

    def stop_alarm(self):
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except RuntimeError:
            pass

        if self.alarm_window and self.alarm_window.winfo_exists():
            self.alarm_window.destroy()

        self.alarm_window = None
        self.alarm_active = False
        self.set_status("Alarm stopped.")


if __name__ == "__main__":
    root = tk.Tk()
    MedicineReminderApp(root)
    root.mainloop()
