# agents/greeting_agent.py
from adk_core import Agent
import datetime as dt

class GreetingAgent(Agent):
    def run(self, context):
        print("=== Patient Greeting ===")
        first = input("First name: ").strip()
        last = input("Last name: ").strip()
        dob = input("DOB (YYYY-MM-DD): ").strip()
        doctor = input("Preferred doctor (e.g., Dr. Priya Rao): ").strip()
        location = input("Preferred location (MG Road Clinic / HSR Layout Clinic / Indiranagar Clinic): ").strip()
        email = input("Email: ").strip()
        phone = input("Phone (10 digits): ").strip()

        # basic validation
        if not first or not last:
            raise ValueError("Name required")
        try:
            _ = dt.date.fromisoformat(dob)
        except Exception:
            raise ValueError("DOB must be YYYY-MM-DD")
        if len(phone) < 10 or not phone.isdigit():
            raise ValueError("Phone must be 10 digits")

        context.update({
            "first_name": first,
            "last_name": last,
            "dob": dob,
            "doctor_name": doctor,
            "location": location,
            "contact_email": email,
            "contact_phone": phone,
        })
        return context
