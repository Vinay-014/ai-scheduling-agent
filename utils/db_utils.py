import pandas as pd
import os

# Paths for data files
PATIENTS_FILE = "data/patients.csv"
APPOINTMENTS_FILE = "data/appointments.csv"

# ---------------- Patients ----------------
def load_patients_df():
    os.makedirs(os.path.dirname(PATIENTS_FILE), exist_ok=True)
    if not os.path.exists(PATIENTS_FILE):
        df = pd.DataFrame(columns=[
            "id", "first_name", "last_name", "dob", "doctor_name", "location", "email", "phone", "forms_filled"
        ])
        df.to_csv(PATIENTS_FILE, index=False)
    else:
        df = pd.read_csv(PATIENTS_FILE)
    return df

def append_patient_row(row):
    df = load_patients_df()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(PATIENTS_FILE, index=False)
    print(f"✅ Patient saved: {row['first_name']} {row['last_name']}")

# ---------------- Appointments ----------------
def load_appointments_df():
    os.makedirs(os.path.dirname(APPOINTMENTS_FILE), exist_ok=True)
    if not os.path.exists(APPOINTMENTS_FILE):
        df = pd.DataFrame(columns=[
            "appointment_id", "patient_id", "doctor", "location", "time", "new_patient", "status"
        ])
        df.to_csv(APPOINTMENTS_FILE, index=False)
    else:
        df = pd.read_csv(APPOINTMENTS_FILE)
    return df

def save_appointment(appt_id, patient_id, doctor, location, appt_time, new_patient=False):
    df = load_appointments_df()
    new_row = {
        "appointment_id": appt_id,
        "patient_id": patient_id,
        "doctor": doctor,
        "location": location,
        "time": appt_time,
        "new_patient": new_patient,
        "status": "scheduled"
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(APPOINTMENTS_FILE, index=False)
    print(f"✅ Appointment saved with ID {appt_id}")

# ---------------- Forms / Status ----------------
def mark_forms_filled(appt_id, filled=True):
    # Mark forms filled for the patient linked to this appointment
    appts = load_appointments_df()
    if appt_id not in appts["appointment_id"].values:
        print(f"⚠️ Appointment {appt_id} not found")
        return
    patient_id = appts.loc[appts["appointment_id"] == appt_id, "patient_id"].values[0]
    patients = load_patients_df()
    patients.loc[patients["id"] == patient_id, "forms_filled"] = filled
    patients.to_csv(PATIENTS_FILE, index=False)
    print(f"✅ Forms marked filled for patient ID {patient_id}")
