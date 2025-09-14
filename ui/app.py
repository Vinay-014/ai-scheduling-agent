import sys
from pathlib import Path
import uuid
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import streamlit as st
from utils.db_utils import load_patients_df, append_patient_row, load_appointments_df, save_appointment, mark_forms_filled
from utils.excel_utils import export_admin_report
from utils.email_utils import send_email, send_email_with_attachment
from agents.reminder_agent import run_reminders

# --- Initialize Session State ---
if "step" not in st.session_state:
    st.session_state.step = 1
if "appt_id" not in st.session_state:
    st.session_state.appt_id = None
if "patient" not in st.session_state:
    st.session_state.patient = None

st.set_page_config(page_title="Medical Scheduling AI", page_icon="🩺", layout="centered")
st.title("🩺 Medical Appointment Scheduling Agent")
st.write("Streamlined patient booking & reminders with AI-powered workflow")

# ---------------- Step 1: Greeting & Patient Intake ----------------
if st.session_state.step == 1:
    st.header("Step 1: Patient Greeting")
    with st.form("patient_form"):
        fname = st.text_input("First name")
        lname = st.text_input("Last name")
        dob = st.date_input("Date of Birth")
        doctor = st.text_input("Preferred doctor (e.g., Dr. Priya Rao)")
        location = st.selectbox("Clinic Location", ["MG Road Clinic", "HSR Layout Clinic", "Indiranagar Clinic"])
        email = st.text_input("Email")
        phone = st.text_input("Phone (10 digits)")
        submit = st.form_submit_button("Continue ➡️")

    if submit:
        patients = load_patients_df()
        match = patients[
            (patients["first_name"] == fname)
            & (patients["last_name"] == lname)
            & (patients["dob"] == str(dob))
        ]
        if match.empty:
            pid = str(len(patients) + 1)
            row = {
                "id": pid,
                "first_name": fname,
                "last_name": lname,
                "dob": str(dob),
                "doctor_name": doctor,
                "location": location,
                "email": email,
                "phone": phone,
            }
            append_patient_row(row)
            st.success(f"🆕 New patient registered with ID {pid}")
            new_patient = True
        else:
            pid = match.iloc[0]["id"]
            st.info(f"👋 Welcome back, {fname}! You are a returning patient.")
            new_patient = False

        # Appointment slot
        appt_id = uuid.uuid4().hex[:8]
        appt_time = datetime.now().replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
        save_appointment(appt_id, pid, doctor, location, appt_time, new_patient)

        # Save session state and move to next step
        st.session_state.appt_id = appt_id
        st.session_state.patient = {
            "id": pid,
            "name": f"{fname} {lname}",
            "email": email,
            "phone": phone,
        }
        st.session_state.step = 2

# ---------------- Step 2: Insurance Collection ----------------
elif st.session_state.step == 2:
    st.header("Step 2: Insurance Collection")
    with st.form("insurance_form"):
        carrier = st.text_input("Insurance Carrier")
        member_id = st.text_input("Member ID")
        group_id = st.text_input("Group ID")
        submit = st.form_submit_button("Save & Continue ➡️")

    if submit:
        st.success("✅ Insurance details saved")
        st.session_state.step = 3

# ---------------- Step 3: Appointment Confirmation ----------------
elif st.session_state.step == 3:
    st.header("Step 3: Appointment Confirmation")
    appt_id = st.session_state.appt_id
    patient = st.session_state.patient
    st.write(f"**Appointment ID:** {appt_id}")
    st.write(f"**Patient:** {patient['name']}")
    st.write(f"**Email:** {patient['email']}")
    st.write(f"**Phone:** {patient['phone']}")

    if st.button("✅ Confirm & Send Forms"):
        # Send appointment confirmation email
        send_email(
            patient["email"],
            "Appointment Confirmation",
            f"Your appointment ({appt_id}) is confirmed.",
        )
        # Send intake form as attachment
        send_email_with_attachment(
            patient["email"],
            "Patient Intake Forms",
            "Please fill the attached intake form before your visit.",
            attachment_path="templates/intake_form.pdf"  # relative to app.py
        )
        st.success("📧 Confirmation + Intake form sent via email")
        st.session_state.step = 4

# ---------------- Step 4: Reminder System ----------------
elif st.session_state.step == 4:
    st.header("Step 4: Reminder System")
    st.info("3 reminders will be sent automatically before appointment.")

    if st.button("▶️ Run Reminder Agent (simulate now)"):
        run_reminders(
            attachment_path="../templates/intake_form.pdf"  # same PDF sent with reminder emails
        )
        st.success("✅ Reminders processed")

    if st.button("📨 Simulate Patient Reply (Confirmed Visit)"):
        mark_forms_filled(st.session_state.appt_id, True)
        st.success("📝 Patient confirmed & forms marked filled")

    if st.button("Next ➡️"):
        st.session_state.step = 5

# ---------------- Step 5: Admin Report ----------------
elif st.session_state.step == 5:
    st.header("Step 5: Admin Review & Reports")
    if st.button("📊 Generate Admin Excel Report"):
        path = export_admin_report()
        st.success(f"Report generated: {path}")
        with open(path, "rb") as f:
            st.download_button("⬇️ Download Report", f, file_name="admin_report.xlsx")
    st.success("🎉 Demo complete! You’ve walked through the full workflow.")
    if st.button("🔄 Start Over"):
        st.session_state.step = 1
