import pandas as pd
import os

APPOINTMENTS_FILE = "data/appointments.csv"

def save_appointment(appt_id, patient_id, doctor, location, appt_time, new_patient=False):
    """Save an appointment into appointments.csv"""
    os.makedirs(os.path.dirname(APPOINTMENTS_FILE), exist_ok=True)

    # If file doesn't exist, create with proper columns
    if not os.path.exists(APPOINTMENTS_FILE):
        df = pd.DataFrame(columns=[
            "appointment_id", "patient_id", "doctor", "location", "time", "new_patient", "forms_filled", "status", "contact_email", "contact_phone"
        ])
    else:
        df = pd.read_csv(APPOINTMENTS_FILE)

    # Add new row
    new_row = {
        "appointment_id": appt_id,
        "patient_id": patient_id,
        "doctor": doctor,
        "location": location,
        "time": appt_time,
        "new_patient": new_patient,
        "forms_filled": False,
        "status": "scheduled",
        "contact_email": "",   # will update from patient data in app.py
        "contact_phone": ""
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(APPOINTMENTS_FILE, index=False)
    print(f"✅ Appointment saved with ID {appt_id}")
