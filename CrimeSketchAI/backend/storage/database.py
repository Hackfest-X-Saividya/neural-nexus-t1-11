"""
SQLite Storage for CrimeSketchAI Refinement Requests.

Logs all incoming refinement requests, whether accepted or rejected,
with full UTC audit timestamps, parsed features, proposed deltas, and error details.
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            # Default to local backend database
            self.db_path = str(Path(__file__).resolve().parent.parent.parent / "refinements.db")
        else:
            self.db_path = str(db_path)
            
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS refinement_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_utc TEXT NOT NULL,
                    request_text TEXT NOT NULL,
                    case_id TEXT,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,          -- 'SUCCESS', 'REJECTED', 'VALIDATION_ERROR'
                    parsed_feature TEXT,
                    target_identifier TEXT,
                    current_value REAL,
                    proposed_delta REAL,
                    proposed_value REAL,
                    error_message TEXT,
                    details_json TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applied_refinements (
                    preview_log_id INTEGER PRIMARY KEY,
                    applied_at_utc TEXT NOT NULL,
                    case_id TEXT,
                    character_name TEXT NOT NULL,
                    status TEXT NOT NULL,          -- 'IN_PROGRESS', 'APPLIED', 'FAILED'
                    apply_log_id INTEGER,
                    error_message TEXT,
                    FOREIGN KEY (preview_log_id) REFERENCES refinement_logs (id)
                )
            """)
            conn.commit()

    def log_request(
        self,
        request_text: str,
        mode: str,
        status: str,
        case_id: Optional[str] = None,
        parsed_feature: Optional[str] = None,
        target_identifier: Optional[str] = None,
        current_value: Optional[float] = None,
        proposed_delta: Optional[float] = None,
        proposed_value: Optional[float] = None,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> int:
        timestamp_utc = datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details) if details else None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO refinement_logs (
                    timestamp_utc,
                    request_text,
                    case_id,
                    mode,
                    status,
                    parsed_feature,
                    target_identifier,
                    current_value,
                    proposed_delta,
                    proposed_value,
                    error_message,
                    details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp_utc,
                request_text,
                case_id,
                mode,
                status,
                parsed_feature,
                target_identifier,
                current_value,
                proposed_delta,
                proposed_value,
                error_message,
                details_json
            ))
            conn.commit()
            return cursor.lastrowid

    def get_logs(self, limit: int = 50, case_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if case_id:
                cursor.execute("""
                    SELECT * FROM refinement_logs 
                    WHERE case_id = ? 
                    ORDER BY id DESC LIMIT ?
                """, (case_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM refinement_logs 
                    ORDER BY id DESC LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_log_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single log record by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM refinement_logs WHERE id = ?", (log_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def claim_preview_for_apply(
        self,
        preview_log_id: int,
        case_id: Optional[str],
        character_name: str
    ) -> bool:
        """
        Atomically claims preview_log_id to prevent duplicate or concurrent applications.
        Returns True if claimed, False if already claimed or applied (replay protection).
        """
        timestamp_utc = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO applied_refinements (
                        preview_log_id, applied_at_utc, case_id, character_name, status
                    ) VALUES (?, ?, ?, ?, 'IN_PROGRESS')
                """, (preview_log_id, timestamp_utc, case_id, character_name))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def complete_preview_apply(
        self,
        preview_log_id: int,
        status: str,
        apply_log_id: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Updates the status and apply_log_id for an applied preview."""
        timestamp_utc = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE applied_refinements
                SET status = ?, apply_log_id = ?, error_message = ?, applied_at_utc = ?
                WHERE preview_log_id = ?
            """, (status, apply_log_id, error_message, timestamp_utc, preview_log_id))
            conn.commit()

    def get_applied_record(self, preview_log_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves the applied_refinements record for a preview_log_id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applied_refinements WHERE preview_log_id = ?", (preview_log_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

