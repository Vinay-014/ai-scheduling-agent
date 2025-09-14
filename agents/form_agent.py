# agents/form_agent.py
from adk_core import Agent
from utils.email_utils import send_email_with_attachment
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

class FormAgent(Agent):
    def run(self, context):
        # If confirmation already sent and PDF exists, send a separate intake form email (backup)
        pdf_path = TEMPLATES / "intake_form.pdf"
        if pdf_path.exists():
            send_email_with_attachment(
                to_addr=context.get("contact_email"),
                subject="Patient Intake Form",
                body="Please fill the attached intake form before your appointment.",
                attachment_path=str(pdf_path)
            )
            print("[INTAKE FORM SENT]")
        else:
            print("[NO INTAKE FORM PDF FOUND in templates/]")
        # mark forms_sent in appointment using db_utils if needed (not mandatory)
        return context
