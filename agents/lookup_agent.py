# agents/lookup_agent.py
from adk_core import Agent
from utils.db_utils import load_patients_df
from utils.db_utils import append_patient_row
from pathlib import Path

class LookupAgent(Agent):
    def run(self, context):
        df = load_patients_df()
        fname = context.get("first_name", "").strip().lower()
        lname = context.get("last_name", "").strip().lower()
        dob = context.get("dob", "")
        if df is None or df.empty:
            # no patient DB -> new
            context["new_or_returning"] = "new"
            return context

        matches = df[
            (df['first_name'].astype(str).str.lower() == fname) &
            (df['last_name'].astype(str).str.lower() == lname) &
            (df['dob'].astype(str) == dob)
        ]
        if not matches.empty:
            row = matches.iloc[0].to_dict()
            context.update(row)
            context["new_or_returning"] = "returning"
            print(f"Returning patient detected: {context.get('first_name')} {context.get('last_name')}")
            return context

        # new patient: create minimal patient_id and append
        next_id = int(df['patient_id'].max())+1 if ('patient_id' in df.columns and not df.empty) else 1
        new_row = {
            "patient_id": int(next_id),
            "first_name": context["first_name"],
            "last_name": context["last_name"],
            "dob": context["dob"],
            "email": context.get("contact_email",""),
            "phone": context.get("contact_phone",""),
            "preferred_location": context.get("location",""),
            "insurance_carrier": "",
            "member_id": "",
            "group_id": ""
        }
        append_patient_row(new_row)
        context.update(new_row)
        context["new_or_returning"] = "new"
        print(f"New patient registered with id: {new_row['patient_id']}")
        return context
