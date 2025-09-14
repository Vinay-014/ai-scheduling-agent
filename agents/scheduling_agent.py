# agents/scheduling_agent.py
from adk_core import Agent
from utils.db_utils import load_doctor_schedule
from utils.db_utils import save_appointment
import uuid

NEW_PATIENT_MIN = 60
RETURNING_MIN = 30

class SchedulingAgent(Agent):
    def run(self, context):
        doctor = context.get("doctor_name")
        location = context.get("location")
        is_new = context.get("new_or_returning", "new") == "new"
        duration = NEW_PATIENT_MIN if is_new else RETURNING_MIN

        # Read doctor schedule (doctors.xlsx). If missing, create fallback slots (tomorrow 10:00)
        sched = load_doctor_schedule()
        slot = None
        if sched is not None and not sched.empty:
            # filter schedule
            matched = sched[
                (sched['doctor_name'].astype(str).str.lower() == str(doctor).strip().lower()) &
                (sched['location'].astype(str).str.lower() == str(location).strip().lower())
            ]
            # find first available not yet booked (db_utils will check)
            if not matched.empty:
                # pick first match
                r = matched.iloc[0]
                slot = {"date": str(r['date']), "time": str(r['time'])}
        if not slot:
            # fallback: choose a simple slot
            from datetime import datetime, timedelta
            s = datetime.now() + timedelta(days=1)
            slot = {"date": s.strftime("%Y-%m-%d"), "time": "10:00"}

        appt_id = str(uuid.uuid4())[:8]
        appt_row = {
            "appointment_id": appt_id,
            "patient_id": context.get("patient_id"),
            "patient_name": f"{context.get('first_name')} {context.get('last_name')}",
            "dob": context.get("dob"),
            "doctor_name": doctor,
            "location": location,
            "date": slot["date"],
            "time": slot["time"],
            "duration_minutes": duration,
            "status": "booked",
            "insurance_carrier": context.get("insurance_carrier",""),
            "member_id": context.get("member_id",""),
            "group_id": context.get("group_id",""),
            "forms_sent": False,
            "forms_filled": False,
            "confirmation_sent": False,
            "created_at": None,
            "updated_at": None,
            "contact_email": context.get("contact_email",""),
            "contact_phone": context.get("contact_phone",""),
            "new_or_returning": context.get("new_or_returning","new"),
            "cancellation_reason": ""
        }
        # persist appointment
        save_appointment(appt_row)
        context["appointment_id"] = appt_id
        context.update(appt_row)
        print(f"[SCHEDULED] Appointment ID: {appt_id} on {slot['date']} at {slot['time']}")
        return context
