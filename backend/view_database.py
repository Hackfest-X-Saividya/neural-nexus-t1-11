"""
Quick CLI Viewer for the Neural Crime Forensic Database
Run this in terminal to display all database records:
python view_database.py
"""

import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "forensic_database.db")

def view():
    if not os.path.exists(DB_PATH):
        try:
            import database
            database.init_db()
        except Exception as e:
            print(f"Error initializing database: {e}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("\n" + "=" * 80)
    print("   NEURAL CRIME - FORENSIC SQLITE DATABASE (TABLE: cases)")
    print("=" * 80)
    cursor.execute("SELECT case_id, title, crime_type, witness_name, status, created_at FROM cases ORDER BY created_at DESC")
    rows = cursor.fetchall()
    if rows:
        for r in rows:
            print(f"[{r['status']}] {r['case_id']} | {r['title']}")
            print(f"      Type: {r['crime_type']} | Witness: {r['witness_name']} | Created: {r['created_at']}")
            print("-" * 80)
    else:
        print("No cases found in database.")

    print("\n" + "=" * 80)
    print("   SAVED 3D COMPOSITES & SKETCHES (TABLE: composites)")
    print("=" * 80)
    cursor.execute("SELECT id, case_id, model, gender, sketch_data, colored_data, created_at FROM composites ORDER BY id DESC")
    comps = cursor.fetchall()
    if comps:
        for c in comps:
            has_sketch = "YES (2D PNG)" if c['sketch_data'] else "None"
            has_color = "YES (3D Color Portrait)" if c['colored_data'] else "None"
            print(f"Composite #{c['id']} for {c['case_id']}")
            print(f"      Model: {c['model']} ({c['gender']}) | Sketch: {has_sketch} | Color Photo: {has_color} | At: {c['created_at']}")
            print("-" * 80)
    else:
        print("No composites saved yet.")

    print("\n" + "=" * 80)
    print("   DATABASE LOCATION: " + os.path.abspath(DB_PATH))
    print("=" * 80 + "\n")

if __name__ == "__main__":
    view()
