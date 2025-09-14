# agents/admin_agent.py
from adk_core import Agent
from utils.db_utils import load_appointments_df
from pathlib import Path

class AdminAgent(Agent):
    def run(self, context):
        print("=== Admin Report Agent ===")
        df = load_appointments_df()
        if df is None or df.empty:
            print("No appointments to report.")
            return context
        out = Path(__file__).resolve().parent.parent / "data" / "admin_report.xlsx"
        # select columns safely
        cols = [c for c in ["appointment_id","patient_name","doctor_name","location","date","time","new_or_returning","status","forms_filled","insurance_carrier","member_id","group_id"] if c in df.columns]
        df[cols].to_excel(out, index=False)
        print(f"Admin report saved to: {out}")
        return context
