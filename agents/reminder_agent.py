# agents/reminder_agent.py
from adk_core import Agent
from utils.db_utils import load_appointments_df
from utils.email_utils import send_email_with_attachment
from utils.sms_utils import send_sms_outbox
import pandas as pd
from datetime import datetime

class ReminderAgent(Agent):
    def run(self, context=None, attachment_path=None):
        """
        Runs reminders for upcoming appointments.

        :param context: Optional agent context
        :param attachment_path: Path to a file (PDF/Excel) to attach with reminder emails
        """
        print("=== Reminder Agent ===")
        appts = load_appointments_df()
        if appts is None or appts.empty:
            print("No appointments to remind.")
            return context

        now = datetime.now()

        # Ensure 'date' and 'time' columns exist
        if 'date' not in appts.columns or 'time' not in appts.columns:
            print("Appointments CSV missing 'date' or 'time' columns.")
            return context

        # Combine date & time columns into a datetime
        appts['dt'] = pd.to_datetime(appts['date'].astype(str) + " " + appts['time'].astype(str), errors='coerce')

        for _, row in appts.iterrows():
            if str(row.get("status", "")).lower() == "cancelled":
                continue

            appt_dt = row.get("dt")
            if pd.isna(appt_dt):
                continue

            hours_to_go = (appt_dt - now).total_seconds() / 3600.0
            due = None
            if 71 <= hours_to_go <= 73:
                due = 1
            elif 23 <= hours_to_go <= 25:
                due = 2
            elif 1.5 <= hours_to_go <= 2.5:
                due = 3
            if not due:
                continue

            if due == 1:
                msg = f"Reminder: appointment on {row.get('date')} {row.get('time')} with {row.get('doctor_name')}. Reply YES to confirm."
            elif due == 2:
                forms = "YES" if row.get("forms_filled") else "NO"
                msg = f"Reminder 2: forms filled? {forms}. Reply YES to confirm visit, or C to cancel (give reason)."
            else:
                msg = f"Final reminder: your appointment is in ~2 hours. Reply YES to confirm or C to cancel (reason)."

            # SMS notification
            send_sms_outbox(str(row.get("contact_phone", "")), msg)

            # Email notification with optional attachment
            if row.get("contact_email"):
                send_email_with_attachment(
                    to_addr=str(row.get("contact_email", "")),
                    subject=f"Reminder {due}",
                    body=msg,
                    attachment_path=attachment_path
                )

            print(f"[REMINDER queued] {row.get('appointment_id')}")

        print("Reminders processed based on current time window.")
        return context


# Convenience function for Streamlit UI
def run_reminders(attachment_path=None):
    agent = ReminderAgent()
    agent.run(context=None, attachment_path=attachment_path)
