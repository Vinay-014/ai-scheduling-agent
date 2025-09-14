# agents/confirmation_agent.py
from adk_core import Agent
from utils.email_utils import send_email_with_attachment
from utils.db_utils import update_appointment_confirmation
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

class ConfirmationAgent(Agent):
    def run(self, context):
        print("\n=== Confirmation / Notification ===")
        # Build message from simple template
        subject = f"Appointment CONFIRMED: {context.get('date')} {context.get('time')}"
        body = (f"Hello {context.get('first_name')} {context.get('last_name')},\n\n"
                f"Your appointment is confirmed.\nDate: {context.get('date')}\nTime: {context.get('time')}\n"
                f"Doctor: {context.get('doctor_name')}\nLocation: {context.get('location')}\n"
                f"Duration: {context.get('duration_minutes')} minutes\n\nThanks,\nClinic")
        # send confirmation email + attach intake_form.pdf if available
        pdf_path = TEMPLATES / "intake_form.pdf"
        send_email_with_attachment(
            to_addr=context.get('contact_email'),
            subject=subject,
            body=body,
            attachment_path=str(pdf_path) if pdf_path.exists() else None
        )
        # send_sms via sms_utils optionally (sms_utils writes to outbox)
        # mark appointment confirmed in appointments sheet
        update_appointment_confirmation(context.get('appointment_id'))
        print("[CONFIRMATION SENT]")
        return context
