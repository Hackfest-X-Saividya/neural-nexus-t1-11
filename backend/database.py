"""
Forensic SQLite Database Manager for Neural Crime
Built-in Python SQLite storage for cases, 3D facial parameters, witness transcripts, and rendered sketches.
"""

import sqlite3
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "forensic_database.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if not already created."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Cases Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            title TEXT DEFAULT 'Suspect Identification',
            crime_type TEXT DEFAULT 'Felony Investigation',
            investigator TEXT DEFAULT 'Detective Unit // Cyber Division',
            witness_name TEXT DEFAULT 'Witness #1',
            status TEXT DEFAULT 'ACTIVE',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Composites Table (3D Anatomical Parameters & Rendered Assets)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS composites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            model TEXT DEFAULT 'male.glb',
            gender TEXT DEFAULT 'male',
            params_json TEXT NOT NULL,
            sketch_data TEXT,
            colored_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
        );
        """)

        # 3. Witness Interview Transcript Logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS witness_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            question_index INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
        );
        """)

        # Pre-seed baseline case if table is empty
        cursor.execute("SELECT COUNT(*) FROM cases;")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
            INSERT INTO cases (case_id, title, crime_type, investigator, witness_name, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                "CASE-2026-X891",
                "Metro Bank Armed Sighting",
                "Armed Robbery / Identification",
                "Detective Unit // Cyber Division",
                "Witness Sarah M.",
                "ACTIVE",
                "Witness identified male suspect with rectangular glasses and stubble beard near 4th avenue."
            ))
        
        conn.commit()

# --- CASE OPERATIONS ---

def get_all_cases() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT c.*, 
               (SELECT COUNT(*) FROM composites WHERE case_id = c.case_id) as composite_count,
               (SELECT created_at FROM composites WHERE case_id = c.case_id ORDER BY id DESC LIMIT 1) as latest_composite_at
        FROM cases c
        ORDER BY c.created_at DESC;
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_case(case_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE case_id = ?;", (case_id,))
        row = cursor.fetchone()
        if not row:
            return None
        case_data = dict(row)
        
        # Fetch latest composite
        cursor.execute("SELECT * FROM composites WHERE case_id = ? ORDER BY id DESC LIMIT 1;", (case_id,))
        comp_row = cursor.fetchone()
        if comp_row:
            case_data["latest_composite"] = dict(comp_row)
            try:
                case_data["latest_composite"]["params"] = json.loads(comp_row["params_json"])
            except Exception:
                case_data["latest_composite"]["params"] = {}
                
        return case_data

def save_or_update_case(case_id: str, title: str = "Suspect Composite", crime_type: str = "Criminal Investigation", investigator: str = "Investigator", witness_name: str = "Witness", status: str = "ACTIVE", notes: str = "") -> Dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO cases (case_id, title, crime_type, investigator, witness_name, status, notes, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(case_id) DO UPDATE SET
            title = excluded.title,
            crime_type = excluded.crime_type,
            investigator = excluded.investigator,
            witness_name = excluded.witness_name,
            status = excluded.status,
            notes = excluded.notes,
            updated_at = CURRENT_TIMESTAMP;
        """, (case_id, title, crime_type, investigator, witness_name, status, notes))
        conn.commit()
    return get_case(case_id) or {}

def delete_case(case_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cases WHERE case_id = ?;", (case_id,))
        conn.commit()
        return cursor.rowcount > 0

# --- COMPOSITE OPERATIONS ---

def save_composite_record(case_id: str, model: str, gender: str, params: Dict[str, Any], sketch_data: Optional[str] = None, colored_data: Optional[str] = None) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        # Ensure parent case exists
        cursor.execute("SELECT 1 FROM cases WHERE case_id = ?;", (case_id,))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO cases (case_id, title, status)
            VALUES (?, 'Suspect Composite Reconstruction', 'ACTIVE');
            """, (case_id,))
        
        cursor.execute("""
        INSERT INTO composites (case_id, model, gender, params_json, sketch_data, colored_data)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (
            case_id,
            model,
            gender,
            json.dumps(params),
            sketch_data,
            colored_data
        ))
        comp_id = cursor.lastrowid
        conn.commit()
        return comp_id

def get_latest_composite(case_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM composites WHERE case_id = ? ORDER BY id DESC LIMIT 1;", (case_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        try:
            res["params"] = json.loads(res["params_json"])
        except Exception:
            res["params"] = {}
        return res

# --- WITNESS MESSAGES OPERATIONS ---

def save_message_record(case_id: str, sender: str, message: str, question_index: Optional[int] = None) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO witness_messages (case_id, sender, message, question_index)
        VALUES (?, ?, ?, ?);
        """, (case_id, sender, message, question_index))
        msg_id = cursor.lastrowid
        conn.commit()
        return msg_id

def get_messages_for_case(case_id: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM witness_messages WHERE case_id = ? ORDER BY id ASC;", (case_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
