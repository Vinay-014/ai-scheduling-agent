# utils/excel_utils.py

from pathlib import Path
import pandas as pd
from .db_utils import load_appointments_df

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
REPORTS_DIR = DATA / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

def export_admin_report():
    """
    Export all appointments into an Excel report for admin review.
    File will be saved under data/reports/admin_report.xlsx
    Returns the path to the report file.
    """
    df = load_appointments_df()
    if df.empty:
        print("No appointments to export.")
        return None

    out_path = REPORTS_DIR / "admin_report.xlsx"
    df.to_excel(out_path, index=False)
    print(f"Admin report exported to {out_path}")
    return out_path
