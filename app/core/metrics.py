from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.core.utils import now_iso


def init_metrics_db(db_path: Path) -> None:
    """Ensure the metrics database and schema exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conv_id TEXT,
                prompt_index INTEGER,
                success INTEGER,
                ttft_ms REAL,
                total_ms REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_requests_created_at ON requests(created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_requests_conv_id ON requests(conv_id)"
        )
        conn.commit()


def record_request(
    db_path: Path,
    *,
    conv_id: str | None,
    prompt_index: int,
    success: bool,
    total_ms: float | None,
    created_at: str | None = None,
) -> None:
    init_metrics_db(db_path)
    timestamp = created_at or now_iso()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO requests (conv_id, prompt_index, success, ttft_ms, total_ms, created_at)
            VALUES (?, ?, ?, NULL, ?, ?)
            """,
            (conv_id, prompt_index, int(success), total_ms, timestamp),
        )
        conn.commit()


def fetch_summary(db_path: Path) -> dict[str, Any]:
    init_metrics_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(success), 0), AVG(total_ms) FROM requests"
        ).fetchone()
    total, successes, avg_total = row
    success_rate = (successes / total) if total else 0.0
    return {
        "total_requests": int(total),
        "successes": int(successes),
        "success_rate": success_rate,
        "avg_total_ms": float(avg_total) if avg_total is not None else None,
    }


def fetch_request_timeseries(
    db_path: Path, bucket: str = "%Y-%m-%dT%H:00:00"
) -> list[dict[str, Any]]:
    """Return counts and success counts aggregated per time bucket."""
    init_metrics_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT strftime(
                       ?,
                       datetime(
                           replace(replace(created_at, 'T', ' '), 'Z', '')
                       )
                   ) AS bucket,
                   COUNT(*) AS total,
                   COALESCE(SUM(success), 0) AS success
            FROM requests
            GROUP BY bucket
            ORDER BY bucket ASC
            """,
            (bucket,),
        ).fetchall()
    return [
        {"bucket": bucket_value, "total": total, "success": success}
        for bucket_value, total, success in rows
    ]


def fetch_latency_timeseries(
    db_path: Path, bucket: str = "%Y-%m-%dT%H:00:00"
) -> list[dict[str, Any]]:
    """Return average total latency per time bucket."""
    init_metrics_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT strftime(
                       ?,
                       datetime(
                           replace(replace(created_at, 'T', ' '), 'Z', '')
                       )
                   ) AS bucket,
                   AVG(total_ms) AS avg_total
            FROM requests
            WHERE total_ms IS NOT NULL
            GROUP BY bucket
            ORDER BY bucket ASC
            """,
            (bucket,),
        ).fetchall()
    return [
        {"bucket": bucket_value, "avg_total_ms": avg_total}
        for bucket_value, avg_total in rows
    ]


def fetch_prompts_to_success(
    db_path: Path,
) -> tuple[list[dict[str, Any]], float | None]:
    """Return per-conversation prompts required before the first successful answer."""
    init_metrics_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT conv_id, prompt_index, created_at
            FROM requests
            WHERE success = 1
              AND id IN (
                SELECT MIN(id) FROM requests WHERE success = 1 GROUP BY conv_id
              )
            ORDER BY created_at ASC
            """
        ).fetchall()
    data = [
        {"conv_id": conv_id, "prompt_index": prompt_index, "created_at": created_at}
        for conv_id, prompt_index, created_at in rows
    ]
    avg_prompts = (
        sum(item["prompt_index"] for item in data) / len(data) if data else None
    )
    return data, avg_prompts
