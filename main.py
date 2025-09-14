#!/usr/bin/env python3
"""AI Scheduling Agent (MVP-1) - Full Implementation (updated)"""

import os
import sys
import uuid
import json
import datetime as dt
from pathlib import Path
import re

import pandas as pd

# dotenv to load .env automatically
from dotenv import load_dotenv
load_dotenv()  # loads .env from project root if present

# Email / attachment imports
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from utils import nlp_utils


# Optional Twilio (SMS) support
try:
    from twilio.rest import Client as TwilioClient
    _TWILIO_AVAILABLE = True
except Exception:
    _TWILIO_AVAILABLE = False

# --- Paths & constants ---
BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
OUTBOX = BASE / "outbox"
TEMPLATES = BASE / "templates"

PATIENTS_CSV = DATA / "patients.csv"
DOCTORS_XLSX = DATA / "doctors.xlsx"
APPTS_XLSX = DATA / "appointments.xlsx"

NEW_PATIENT_MIN = 60
RETURNING_MIN = 30

# Ensure base directories exist
DATA.mkdir(parents=True, exist_ok=True)
OUTBOX.mkdir(parents=True, exist_ok=True)
TEMPLATES.mkdir(parents=True, exist_ok=True)
(OUTBOX / "emails").mkdir(parents=True, exist_ok=True)
(OUTBOX / "sms").mkdir(parents=True, exist_ok=True)
(DATA / "calendly_bookings").mkdir(parents=True, exist_ok=True)

# --- Email (Gmail) & Twilio config ---
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))

# Defaults (kept to allow previous quick tests) - you should set via .env
DEFAULT_SMTP_USER = os.environ.get("DEFAULT_SMTP_USER", "vinayks705@gmail.com")
DEFAULT_SMTP_PASS = os.environ.get("DEFAULT_SMTP_PASS", "orcktbihudzvroju")

# Primary values: prefer .env / env vars
SMTP_USER = os.environ.get("SMTP_USER", DEFAULT_SMTP_USER)
SMTP_PASS = os.environ.get("SMTP_PASS", DEFAULT_SMTP_PASS)

# Twilio config (optional)
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_AUTH = os.environ.get("TWILIO_AUTH")
TWILIO_PHONE = os.environ.get("TWILIO_PHONE")  # e.g. +1234567890

# ---------- Utilities ----------
def load_df(path: Path, empty_cols=None) -> pd.DataFrame:
    """Load CSV or XLSX safely. Return empty DataFrame with provided columns if missing."""
    try:
        if path.suffix.lower() == ".xlsx":
            if path.exists():
                return pd.read_excel(path)
            return pd.DataFrame(columns=empty_cols or [])
        else:
            if path.exists():
                return pd.read_csv(path)
            return pd.DataFrame(columns=empty_cols or [])
    except Exception:
        return pd.DataFrame(columns=empty_cols or [])

def save_df_xlsx(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False)

def now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def normalize(s) -> str:
    return str(s).strip().lower()

def normalize_phone_digits(phone: str) -> str:
    """Return last 10 digits (useful for matching local Indian numbers)."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    return digits[-10:] if len(digits) >= 10 else digits

# ---------- CLI flow (unchanged behavior) ----------
def greet_collect():
    print("=== Patient Greeting ===")
    first = input("First name: ").strip()
    last = input("Last name: ").strip()
    dob = input("DOB (YYYY-MM-DD): ").strip()
    doctor = input("Preferred doctor (e.g., Dr. Priya Rao): ").strip()
    location = input("Preferred location (MG Road Clinic / HSR Layout Clinic / Indiranagar Clinic): ").strip()
    email = input("Email: ").strip()
    phone = input("Phone (10 digits): ").strip()

    if not first or not last:
        raise ValueError("Name required")
    try:
        _ = dt.date.fromisoformat(dob)
    except Exception:
        raise ValueError("DOB must be YYYY-MM-DD")
    if len(re.sub(r"\D", "", phone)) < 10:
        raise ValueError("Phone must be at least 10 digits")
    return {
        "first_name": first,
        "last_name": last,
        "dob": dob,
        "doctor_name": doctor,
        "location": location,
        "email": email,
        "phone": phone,
    }

def lookup_patient(info):
    patient_cols = [
        "patient_id", "first_name", "last_name", "dob", "email", "phone",
        "preferred_location", "insurance_carrier", "member_id", "group_id"
    ]
    df = load_df(PATIENTS_CSV, empty_cols=patient_cols)
    if df.empty:
        return {"new_or_returning": "new"}
    mask = (
        (df["first_name"].astype(str).str.lower() == normalize(info["first_name"])) &
        (df["last_name"].astype(str).str.lower() == normalize(info["last_name"])) &
        (df["dob"].astype(str) == info["dob"])
    )
    matches = df[mask]
    if not matches.empty:
        row = matches.iloc[0].to_dict()
        row["new_or_returning"] = "returning"
        return row
    return {
        "patient_id": None,
        "first_name": info["first_name"],
        "last_name": info["last_name"],
        "dob": info["dob"],
        "email": info["email"],
        "phone": info["phone"],
        "preferred_location": info["location"],
        "insurance_carrier": "",
        "member_id": "",
        "group_id": "",
        "new_or_returning": "new",
    }

def find_available_slots(doctor_name, location):
    """Return list of available (date, time) pairs for doctor+location."""
    appt_cols = [
        "appointment_id","patient_id","patient_name","dob","doctor_id","doctor_name",
        "location","date","time","duration_minutes","status","insurance_carrier",
        "member_id","group_id","forms_sent","forms_filled","confirmation_sent",
        "created_at","updated_at","contact_email","contact_phone","new_or_returning",
        "cancellation_reason"
    ]
    appts = load_df(APPTS_XLSX, empty_cols=appt_cols)

    try:
        if not DOCTORS_XLSX.exists():
            return []
        xls = pd.ExcelFile(DOCTORS_XLSX)
    except Exception:
        return []

    merged = []
    for sheet in xls.sheet_names:
        try:
            df = pd.read_excel(DOCTORS_XLSX, sheet_name=sheet)
            merged.append(df)
        except Exception:
            continue
    if not merged:
        return []

    avail = pd.concat(merged, ignore_index=True)
    if not {"doctor_name","location","date","time"}.issubset(set(avail.columns)):
        return []

    avail = avail[
        (avail["doctor_name"].astype(str).str.lower() == normalize(doctor_name)) &
        (avail["location"].astype(str).str.lower() == normalize(location))
    ]

    if avail.empty:
        return []

    if not appts.empty:
        booked = appts[
            (appts["doctor_name"].astype(str).str.lower() == normalize(doctor_name)) &
            (appts["location"].astype(str).str.lower() == normalize(location)) &
            (appts["status"].astype(str).str.lower() != "cancelled")
        ]
        booked_pairs = set((str(d), str(t)) for d, t in zip(booked.get("date", []), booked.get("time", [])))
    else:
        booked_pairs = set()

    open_slots = []
    for _, row in avail.iterrows():
        pair = (str(row["date"]), str(row["time"]))
        if pair not in booked_pairs:
            open_slots.append(pair)
    open_slots = sorted(open_slots)
    return open_slots

def select_slot(doctor_name, location, duration_min):
    open_slots = find_available_slots(doctor_name, location)
    if not open_slots:
        print("No availability found for that doctor/location.")
        return None
    open_slots = open_slots[:15]
    print('\n=== Next Available Slots ===')
    for i, (d,t) in enumerate(open_slots, start=1):
        print(f"{i}. {d} at {t} ({duration_min} min)")
    choice = input('Pick slot # (or press Enter to cancel): ').strip()
    if not choice:
        return None
    try:
        idx = int(choice) - 1
    except ValueError:
        print("Invalid choice.")
        return None
    if idx < 0 or idx >= len(open_slots):
        print("Invalid choice.")
        return None
    return {'date': open_slots[idx][0], 'time': open_slots[idx][1]}

def capture_insurance(existing):
    print('\n=== Insurance Collection ===')
    carrier = input(f"Carrier [{existing.get('insurance_carrier','')}]: ").strip() or existing.get("insurance_carrier", "")
    member = input(f"Member ID [{existing.get('member_id','')}]: ").strip() or existing.get("member_id", "")
    group = input(f"Group ID [{existing.get('group_id','')}]: ").strip() or existing.get("group_id", "")
    return carrier, member, group

# ----------------- Outbox logging + senders -----------------
def _write_outbox_email(to_addr, subject, body, attachment_name=None):
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = (to_addr or "no_email").replace("@", "_at_")
    fname = OUTBOX / "emails" / f"{ts}_{safe}.txt"
    extra = f"\n\n[ATTACHMENT: {attachment_name}]" if attachment_name else ""
    content = f"TO: {to_addr}\nSUBJECT: {subject}\n\n{body}{extra}"
    fname.write_text(content, encoding="utf-8")
    print(f"[email queued] {fname}")

def _write_outbox_sms(to_phone, text):
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = to_phone or "no_phone"
    fname = OUTBOX / "sms" / f"{ts}_{safe}.txt"
    fname.write_text(text, encoding="utf-8")
    print(f"[sms queued] {fname}")

def send_email(to_addr, subject, body, attachment_path=None):
    try:
        # Always log to outbox
        attachment_name = Path(attachment_path).name if attachment_path else None
        _write_outbox_email(to_addr, subject, body, attachment_name=attachment_name)
    except Exception as e:
        print(f"[outbox email write failed] {e}")

    if SMTP_USER and SMTP_PASS and SMTP_PASS != "REPLACE_WITH_GOOGLE_APP_PASSWORD" and to_addr:
        try:
            if attachment_path:
                print("PDF exists?", attachment_path, os.path.exists(attachment_path))
                msg = MIMEMultipart()
                msg.attach(MIMEText(body, "plain"))

                filename = os.path.basename(str(attachment_path))
                with open(attachment_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={filename}")
                    print(f"[debug] attaching file: {attachment_path}")
                    msg.attach(part)
            else:
                msg = MIMEText(body, "plain")

            msg["From"] = SMTP_USER
            msg["To"] = to_addr
            msg["Subject"] = subject

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_USER, [to_addr], msg.as_string())

            print(f"[email sent] to {to_addr}")
            return True
        except Exception as e:
            print(f"[email failed] {e}")
            return False
    else:
        print("[email not sent] SMTP credentials unavailable; saved to outbox only.")
        return False

def send_sms(to_phone, text):
    # Always log
    try:
        _write_outbox_sms(to_phone, text)
    except Exception as e:
        print(f"[outbox sms write failed] {e}")

    # Attempt Twilio send if configured
    if _TWILIO_AVAILABLE and TWILIO_SID and TWILIO_AUTH and TWILIO_PHONE and to_phone:
        try:
            client = TwilioClient(TWILIO_SID, TWILIO_AUTH)
            dest = to_phone if to_phone.startswith("+") else "+91" + to_phone
            msg = client.messages.create(body=text, from_=TWILIO_PHONE, to=dest)
            print(f"[sms sent] to {to_phone} SID:{msg.sid}")
            return True
        except Exception as e:
            print(f"[sms failed] {e}")
            return False
    else:
        if not _TWILIO_AVAILABLE:
            print("[sms not sent] Twilio library not installed; saved to outbox only.")
        elif not (TWILIO_SID and TWILIO_AUTH and TWILIO_PHONE):
            print("[sms not sent] Twilio credentials unavailable; saved to outbox only.")
        return False

def load_template(name):
    path = TEMPLATES / name
    if not path.exists():
        # sensible defaults
        if name == "email_template.txt":
            return ("Hello {name},\n\nYour appointment is {status_lower}.\n"
                    "Date: {date}\nTime: {time}\nDoctor: {doctor}\nLocation: {location}\n"
                    "Duration: {duration} minutes\n\nThanks.")
        if name == "sms_template.txt":
            return "Appt {status} {date} {time} with {doctor} at {location} ({duration} min)."
        if name == "intake_form.txt":
            return "Please fill your intake form before visit. Thank you."
        return ""
    return path.read_text(encoding="utf-8")

# ----------------- Confirm + message sending -----------------
def confirm_and_send(appt_row):
    email_t = load_template("email_template.txt")
    sms_t = load_template("sms_template.txt")
    status = "CONFIRMED"

    body = email_t.format(
        status=status,
        status_lower=status.lower(),
        date=appt_row["date"],
        time=appt_row["time"],
        doctor=appt_row["doctor_name"],
        location=appt_row["location"],
        name=appt_row["patient_name"],
        duration=appt_row["duration_minutes"],
    )

    pdf_path = TEMPLATES / "intake_form.pdf"
    send_email(
        appt_row["contact_email"],
        f"Appointment {status}",
        body,
        attachment_path=str(pdf_path) if pdf_path.exists() else None
    )

    sms = sms_t.format(
        status="CONFIRMED",
        date=appt_row["date"],
        time=appt_row["time"],
        doctor=appt_row["doctor_name"],
        location=appt_row["location"],
        duration=appt_row["duration_minutes"],
    )
    send_sms(appt_row["contact_phone"], sms)

# ----------------- Programmatic booking (used by Streamlit/UI) -----------------
def book_appointment(params: dict, pick_first_slot=True):
    """
    Programmatic booking helper.
    params keys: first_name, last_name, dob, doctor_name, location, email, phone, (optional) carrier, member_id, group_id
    If pick_first_slot True -> will auto-pick the first available slot and book it.
    Returns appt_row dict on success, or {'error': '...'} on failure.
    """
    try:
        # Validation
        required = ["first_name","last_name","dob","doctor_name","location","email","phone"]
        for k in required:
            if not params.get(k):
                return {"error": f"Missing {k}"}

        # [NLP] Normalize fields (doctor, location, dob)
        from utils import nlp_utils
        doctor_norm = nlp_utils.normalize_doctor(params["doctor_name"])
        if not doctor_norm:
            return {"error": f"Doctor not recognized: {params['doctor_name']}"}
        location_norm = nlp_utils.normalize_location(params["location"])
        if not location_norm:
            return {"error": f"Location not recognized: {params['location']}"}
        dob_norm = nlp_utils.parse_dob(params["dob"])
        if not dob_norm:
            return {"error": f"Could not parse DOB: {params['dob']}"}

        info = {
            "first_name": params["first_name"],
            "last_name": params["last_name"],
            "dob": dob_norm,                       # [NLP] normalized DOB
            "doctor_name": doctor_norm,            # [NLP] normalized doctor
            "location": location_norm,             # [NLP] normalized location
            "email": params["email"],
            "phone": params["phone"],
        }

        pat = lookup_patient(info)
        new_or_ret = pat.get("new_or_returning","new")
        duration = NEW_PATIENT_MIN if new_or_ret == "new" else RETURNING_MIN

        # pick a slot automatically
        slots = find_available_slots(info["doctor_name"], info["location"])
        if not slots:
            return {"error": "No open slots found for doctor/location"}
        slot = slots[0]  # first available
        slot_dict = {"date": slot[0], "time": slot[1]}

        # insurance fields:
        carrier = params.get("carrier","")
        member = params.get("member_id","")
        group = params.get("group_id","")

        # ensure patient saved
        patients = load_df(PATIENTS_CSV)
        if pat.get("patient_id") is None:
            new_id = int(patients["patient_id"].max()) + 1 if (not patients.empty and "patient_id" in patients.columns) else 1
            pat["patient_id"] = int(new_id)
            pat["insurance_carrier"] = carrier
            pat["member_id"] = member
            pat["group_id"] = group
            patients = pd.concat([patients, pd.DataFrame([pat])], ignore_index=True)
            patients.to_csv(PATIENTS_CSV, index=False)
        else:
            # update insurance if provided
            if carrier: pat["insurance_carrier"] = carrier
            if member: pat["member_id"] = member
            if group: pat["group_id"] = group
            # write back (update existing)
            if not patients.empty and "patient_id" in patients.columns:
                patients.loc[patients["patient_id"] == pat["patient_id"], ["insurance_carrier","member_id","group_id"]] = [pat.get("insurance_carrier",""), pat.get("member_id",""), pat.get("group_id","")]
                patients.to_csv(PATIENTS_CSV, index=False)

        # create appointment
        appts = load_df(APPTS_XLSX, empty_cols=[])
        appt_id = str(uuid.uuid4())[:8]
        appt_row = {
            "appointment_id": appt_id,
            "patient_id": pat["patient_id"],
            "patient_name": f"{pat['first_name']} {pat['last_name']}",
            "dob": pat["dob"],
            "doctor_id": None,
            "doctor_name": info["doctor_name"],
            "location": info["location"],
            "date": slot_dict["date"],
            "time": slot_dict["time"],
            "duration_minutes": duration,
            "status": "booked",
            "insurance_carrier": carrier,
            "member_id": member,
            "group_id": group,
            "forms_sent": True,
            "forms_filled": False,
            "confirmation_sent": True,
            "created_at": now_str(),
            "updated_at": now_str(),
            "contact_email": info["email"],
            "contact_phone": info["phone"],
            "new_or_returning": new_or_ret,
            "cancellation_reason": "",
        }
        appts = pd.concat([appts, pd.DataFrame([appt_row])], ignore_index=True)
        save_df_xlsx(appts, APPTS_XLSX)

        # save calendar file
        cal_dir = DATA / "calendly_bookings"
        cal_dir.mkdir(exist_ok=True)
        (cal_dir / f"{appt_id}.txt").write_text(json.dumps(appt_row, indent=2), encoding="utf-8")

        # send confirmation (email + PDF)
        confirm_and_send(appt_row)
        return {"appointment": appt_row}
    except Exception as e:
        return {"error": str(e)}

# ----------------- Reminders (returns logs) -----------------
def run_reminders(today=None):
    logs = []
    if today:
        base_dt = dt.datetime.fromisoformat(today + " 09:00:00")
    else:
        base_dt = dt.datetime.now()

    appt_cols = [
        "appointment_id","patient_id","patient_name","dob","doctor_id","doctor_name",
        "location","date","time","duration_minutes","status","insurance_carrier",
        "member_id","group_id","forms_sent","forms_filled","confirmation_sent",
        "created_at","updated_at","contact_email","contact_phone","new_or_returning",
        "cancellation_reason"
    ]
    appts = load_df(APPTS_XLSX, empty_cols=appt_cols)
    if appts.empty:
        logs.append("No appointments.")
        print("No appointments.")
        return logs

    appts["dt"] = pd.to_datetime(appts["date"].astype(str) + " " + appts["time"].astype(str), errors="coerce")
    for _, row in appts.iterrows():
        if str(row.get("status", "")).lower() == "cancelled":
            continue
        appt_dt = row.get("dt")
        if pd.isna(appt_dt):
            continue

        hours_to_go = (appt_dt - base_dt).total_seconds() / 3600.0
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
            msg = f"Reminder: appt on {row['date']} {row['time']} with {row['doctor_name']}. Reply YES to confirm."
        elif due == 2:
            forms = "YES" if row.get("forms_filled") else "NO"
            msg = f"Reminder 2: forms filled? {forms}. Reply YES to confirm visit, or C to cancel (give reason)."
        else:
            msg = f"Final reminder: your appt is in ~2 hours. Reply YES to confirm or C to cancel (reason)."

        send_sms(str(row.get("contact_phone", "")), msg)
        send_email(str(row.get("contact_email", "")), f"Reminder {due}", msg)
        logs.append(f"Sent reminder {due} to {row.get('appointment_id')} -> {row.get('contact_email')} / {row.get('contact_phone')}")
    logs.append("Reminders processed based on current time window.")
    print("Reminders processed based on current time window.")
    return logs

# ----------------- Inbound-reply processing (simulate or webhook) -----------------
def process_inbound_reply(from_phone: str, text: str):
    """
    Process an inbound reply text from a phone number. 
    Texts starting with YES/Y -> confirm.
    Texts starting with C / CANCEL -> cancel and extract reason.
    Returns dict {'ok': True, 'msg': '...'} or {'ok': False, 'error': '...'}
    """
    try:
        if not from_phone or not text:
            return {"ok": False, "error": "Missing phone or text"}

        appts = load_df(APPTS_XLSX)
        if appts.empty:
            return {"ok": False, "error": "No appointments in DB"}

        norm = normalize_phone_digits(from_phone)
        # match by last 10 digits
        appts["phone_norm"] = appts.get("contact_phone","").astype(str).apply(normalize_phone_digits)
        candidates = appts[appts["phone_norm"] == norm]
        if candidates.empty:
            return {"ok": False, "error": "No appointment found for that phone"}

        # choose the upcoming appointment (closest future) or last booked
        candidates["dt"] = pd.to_datetime(candidates["date"].astype(str) + " " + candidates["time"].astype(str), errors="coerce")
        now = dt.datetime.now()
        future = candidates[candidates["dt"] >= now]
        if not future.empty:
            chosen = future.sort_values("dt").iloc[0]
        else:
            chosen = candidates.sort_values("dt", ascending=False).iloc[0]

        appt_id = chosen["appointment_id"]
        appts_idx = appts["appointment_id"] == appt_id
        body = text.strip().lower()
        if body.startswith("y") or body.startswith("yes"):
            appts.loc[appts_idx, "confirmation_sent"] = True
            appts.loc[appts_idx, "status"] = "confirmed"
            appts.loc[appts_idx, "updated_at"] = now_str()
            save_df_xlsx(appts, APPTS_XLSX)
            return {"ok": True, "msg": f"Appointment {appt_id} marked confirmed."}
        if body.startswith("c") or body.startswith("cancel"):
            # extract reason after 'c' or 'cancel'
            reason = text.strip()[1:].strip() if len(text.strip())>1 else "Cancelled via SMS"
            appts.loc[appts_idx, "status"] = "cancelled"
            appts.loc[appts_idx, "cancellation_reason"] = reason
            appts.loc[appts_idx, "updated_at"] = now_str()
            save_df_xlsx(appts, APPTS_XLSX)
            return {"ok": True, "msg": f"Appointment {appt_id} cancelled (reason: {reason})."}
        # If reply about forms: e.g., "FORM YES"
        if "form" in body and ("yes" in body or "done" in body):
            appts.loc[appts_idx, "forms_filled"] = True
            appts.loc[appts_idx, "updated_at"] = now_str()
            save_df_xlsx(appts, APPTS_XLSX)
            return {"ok": True, "msg": f"Appointment {appt_id} forms_filled=True."}

        return {"ok": False, "error": "Unrecognized reply format. Use YES to confirm or C to cancel."}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ----------------- Admin / helper -----------------
def mark_forms_filled(appt_id: str, filled: bool = True):
    appts = load_df(APPTS_XLSX, empty_cols=["appointment_id","forms_filled","updated_at"])
    if appts.empty:
        print("No appointments.")
        return
    mask = appts["appointment_id"] == appt_id
    if not mask.any():
        print("Appointment not found.")
        return
    appts.loc[mask, "forms_filled"] = bool(filled)
    appts.loc[mask, "updated_at"] = now_str()
    save_df_xlsx(appts, APPTS_XLSX)
    print(f"Updated forms_filled={filled} for {appt_id}.")

def cancel_appointment(appt_id: str, reason: str):
    appts = load_df(APPTS_XLSX, empty_cols=["appointment_id","status","cancellation_reason","updated_at"])
    mask = appts["appointment_id"] == appt_id if not appts.empty else pd.Series([], dtype=bool)
    if appts.empty or not mask.any():
        print("Appointment not found.")
        return
    appts.loc[mask, "status"] = "cancelled"
    appts.loc[mask, "cancellation_reason"] = reason
    appts.loc[mask, "updated_at"] = now_str()
    save_df_xlsx(appts, APPTS_XLSX)
    print(f"Cancelled {appt_id} (reason: {reason}).")

def report_admin():
    appts = load_df(APPTS_XLSX)
    if appts.empty:
        print("No appointments yet.")
        return
    cols = [
        "appointment_id", "patient_name", "doctor_name", "location",
        "date", "time", "new_or_returning", "status", "forms_filled",
        "insurance_carrier", "member_id", "group_id",
    ]
    cols = [c for c in cols if c in appts.columns]
    report = appts[cols].copy()
    out = DATA / "admin_report.xlsx"
    report.to_excel(out, index=False)
    print(f"Admin report saved to: {out}")

# ----------------- CLI menu (added simulate reply option) -----------------
def menu():
    print(
        """
======= AI Scheduling Agent =======
1) Book an appointment
2) Run reminders (auto window)
3) Mark forms filled (enter appt id)
4) Cancel appointment (enter appt id + reason)
5) Generate admin Excel report
6) Show data folder path
7) Simulate patient reply (enter phone + text)
0) Exit
"""
    )
    choice = input("Choose: ").strip()
    return choice

if __name__ == "__main__":
    while True:
        c = menu()
        if c == "1":
            try:
                # use original interactive CLI booking flow
                info = greet_collect()
                pat = lookup_patient(info)
                slot = select_slot(info["doctor_name"], info["location"], NEW_PATIENT_MIN if pat.get("new_or_returning","new")=="new" else RETURNING_MIN)
                if not slot:
                    print("Booking cancelled.")
                else:
                    carrier, member, group = capture_insurance(pat)
                    # now call programmatic helper to finish booking
                    params = {
                        "first_name": info["first_name"],
                        "last_name": info["last_name"],
                        "dob": info["dob"],
                        "doctor_name": info["doctor_name"],
                        "location": info["location"],
                        "email": info["email"],
                        "phone": info["phone"],
                        "carrier": carrier,
                        "member_id": member,
                        "group_id": group,
                    }
                    res = book_appointment(params)
                    if res.get("error"):
                        print("Error booking:", res["error"])
                    else:
                        appt = res["appointment"]
                        print(f"[SCHEDULED] Appointment ID: {appt['appointment_id']} on {appt['date']} at {appt['time']}")
            except Exception as e:
                print("Error:", e)
        elif c == "2":
            run_reminders()
        elif c == "3":
            a = input("Appointment ID: ").strip()
            v = input("Filled? (y/n): ").strip().lower().startswith("y")
            mark_forms_filled(a, v)
        elif c == "4":
            a = input("Appointment ID: ").strip()
            r = input("Reason: ").strip() or "no reason given"
            cancel_appointment(a, r)
        elif c == "5":
            report_admin()
        elif c == "6":
            print(f"Data folder: {DATA}")
            print(f"Outbox folder: {OUTBOX}")
        elif c == "7":
            phone = input("From phone number (e.g. 6361006588 or +91...): ").strip()
            text = input("Reply text (YES / C reason / FORM YES): ").strip()
            res = process_inbound_reply(phone, text)
            if res.get("ok"):
                print(res.get("msg"))
            else:
                print("Reply processing error:", res.get("error"))
        elif c == "0" or c == "":
            print("Bye.")
            sys.exit(0)
        else:
            print("Invalid option.")
