from datetime import datetime

from plyer import notification

from database import get_connection, initialize_database


def show_notification(medicine):
    notification.notify(
        title="Medicine Reminder",
        message=(
            f"Time to take: {medicine['name']}\n"
            f"Dosage: {medicine['dosage']}"
        ),
        app_name="Medicine Reminder System",
        timeout=12,
    )


def check_due_reminders():
    """Return medicines due now and mark each as notified today."""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    today = now.strftime("%Y-%m-%d")

    with get_connection() as connection:
        medicines = connection.execute("""
            SELECT * FROM medicines
            WHERE enabled = 1
              AND reminder_time = ?
              AND (repeat_daily = 1 OR start_date = ?)
              AND COALESCE(last_reminded_date, '') != ?
        """, (
            current_time,
            today,
            today,
        )).fetchall()

        for medicine in medicines:
            try:
                show_notification(medicine)
            except Exception as error:
                print(f"Notification error: {error}")

            connection.execute("""
                UPDATE medicines
                SET last_reminded_date = ?
                WHERE id = ?
            """, (
                today,
                medicine["id"],
            ))

    return medicines


if __name__ == "__main__":
    initialize_database()

    due_medicines = check_due_reminders()

    if due_medicines:
        print(f"{len(due_medicines)} reminder(s) sent.")
    else:
        print("No reminders are due at the current minute.")