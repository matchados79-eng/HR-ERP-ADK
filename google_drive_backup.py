import os
import json
import zipfile
import io
from datetime import datetime
import database as db

BASE_DIR = os.path.dirname(__file__)

def generate_full_backup_archive() -> str:
    """
    Creates a full backup archive containing:
    1. Complete database JSON dump (all tables)
    2. Document & photo upload files
    Returns absolute file path to the generated backup zip archive.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"saudi_hr_backup_{timestamp}.zip"
    backup_dir = os.path.join(BASE_DIR, "uploads", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    zip_path = os.path.join(backup_dir, backup_filename)
    
    # 1. Export Database Tables to JSON
    db_dump = {
        "export_date": datetime.now().isoformat(),
        "departments": db.query_all("SELECT * FROM departments"),
        "employees": db.query_all("SELECT * FROM employees"),
        "documents": db.query_all("SELECT * FROM documents"),
        "leaves": db.query_all("SELECT * FROM leaves"),
        "payroll_runs": db.query_all("SELECT * FROM payroll_runs"),
        "payroll_details": db.query_all("SELECT * FROM payroll_details"),
        "settings": db.query_all("SELECT * FROM settings"),
        "users": db.query_all("SELECT * FROM users") if db.query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='users'") else []
    }
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add database dump JSON
        zf.writestr("database_dump.json", json.dumps(db_dump, indent=2, ensure_ascii=False))
        
        # Add SQLite db binary if present
        if os.path.exists(db.DB_WORKSPACE_PATH):
            zf.write(db.DB_WORKSPACE_PATH, arcname="saudi_hr.db")
            
        # Add uploaded photos and documents
        uploads_dir = os.path.join(BASE_DIR, "uploads")
        if os.path.exists(uploads_dir):
            for root, dirs, files in os.walk(uploads_dir):
                if "backups" in root:
                    continue # Skip backup folder itself
                for file in files:
                    full_file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_file_path, BASE_DIR)
                    zf.write(full_file_path, arcname=rel_path)
                    
    return zip_path
