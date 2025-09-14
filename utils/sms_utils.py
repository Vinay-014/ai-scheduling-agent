# utils/sms_utils.py
import os
from pathlib import Path
OUTBOX = Path(__file__).resolve().parent.parent / "outbox"
(OUTBOX / "sms").mkdir(parents=True, exist_ok=True)

def send_sms_outbox(to_phone, text):
    # Save SMS to outbox (so you can see messages)
    ts = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = to_phone or "no_phone"
    fname = OUTBOX / "sms" / f"{ts}_{safe}.txt"
    fname.write_text(text, encoding="utf-8")
    print(f"[sms queued] {fname}")
    # Optional real Twilio send could be added here, but kept optional
    return True
