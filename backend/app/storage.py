from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # Local SQLite development does not require psycopg.
    psycopg = None
    dict_row = None

DB_PATH = Path(__file__).resolve().parent.parent / "platform.db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)

RELATION_LABELS = {
    "labor": "标准劳动关系",
    "ambiguous": "新业态模糊混合用工关系",
    "service": "劳务依附型合作关系",
    "business": "纯平等民事商务合作关系",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _clean_relation_label(result: dict) -> str:
    label = str(result.get("relationLabel") or "")
    relation_type = str(result.get("relationType") or "")
    if not label or any(marker in label for marker in ("æ", "ç", "å", "ã", "忙", "莽", "氓", "茫")):
        return RELATION_LABELS.get(relation_type, "未分类")
    return label


@contextmanager
def _connect() -> Iterator[Any]:
    if USE_POSTGRES:
        if psycopg is None:
            raise RuntimeError("DATABASE_URL is set, but psycopg is not installed.")
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            yield conn
    else:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn


def _param(sqlite_sql: str, postgres_sql: str | None = None) -> str:
    if USE_POSTGRES:
        return postgres_sql or sqlite_sql.replace("?", "%s")
    return sqlite_sql


def _row_value(row: Any, key: str) -> Any:
    return row[key]


def _ensure_column(conn: Any, table: str, column: str, definition: str) -> None:
    if USE_POSTGRES:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
        return
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db(initial_cases: list[dict] | None = None, initial_knowledge: list[dict] | None = None) -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluations (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                relation TEXT NOT NULL,
                year INTEGER NOT NULL,
                focus_json TEXT NOT NULL,
                summary TEXT NOT NULL,
                similarity INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                points_json TEXT NOT NULL,
                basis_json TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS matters (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, party_role TEXT NOT NULL,
                mcn_name TEXT NOT NULL, dispute_types_json TEXT NOT NULL,
                status TEXT NOT NULL, current_step INTEGER NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence_items (
                id TEXT PRIMARY KEY, matter_id TEXT NOT NULL, category TEXT NOT NULL,
                name TEXT NOT NULL, status TEXT NOT NULL, note TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY, user_id TEXT NOT NULL, action TEXT NOT NULL,
                entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
                detail TEXT NOT NULL, created_at TEXT NOT NULL
            )
        """)
        _ensure_column(conn, "evaluations", "user_id", "TEXT NOT NULL DEFAULT 'legacy'")
        _ensure_column(conn, "matters", "user_id", "TEXT NOT NULL DEFAULT 'legacy'")
        _ensure_column(conn, "matters", "evaluation_id", "TEXT")
        _ensure_column(conn, "evidence_items", "stored_name", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "evidence_items", "mime_type", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "evidence_items", "size_bytes", "INTEGER NOT NULL DEFAULT 0")
        if initial_cases:
            count = _row_value(conn.execute("SELECT COUNT(*) AS total FROM cases").fetchone(), "total")
            if count == 0:
                conn.executemany(
                    _param(
                        """
                        INSERT INTO cases
                        (id, title, relation, year, focus_json, summary, similarity, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """
                    ),
                    [
                        (
                            item["id"],
                            item["title"],
                            item["relation"],
                            item["year"],
                            json.dumps(item["focus"], ensure_ascii=False),
                            item["summary"],
                            item["similarity"],
                            _now(),
                        )
                        for item in initial_cases
                    ],
                )
        if initial_knowledge:
            conn.executemany(
                _param(
                    """
                    INSERT OR IGNORE INTO knowledge
                    (id, category, title, summary, points_json, basis_json, tags_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    """
                    INSERT INTO knowledge
                    (id, category, title, summary, points_json, basis_json, tags_json, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                ),
                [
                    (
                        item["id"],
                        item["category"],
                        item["title"],
                        item["summary"],
                        json.dumps(_json_list(item.get("points")), ensure_ascii=False),
                        json.dumps(_json_list(item.get("basis")), ensure_ascii=False),
                        json.dumps(_json_list(item.get("tags")), ensure_ascii=False),
                        _now(),
                    )
                    for item in initial_knowledge
                ],
            )
        conn.commit()


def save_evaluation(answers: dict, result: dict, user_id: str) -> str:
    evaluation_id = str(uuid4())
    with _connect() as conn:
        conn.execute(
            _param("INSERT INTO evaluations (id, created_at, answers_json, result_json, user_id) VALUES (?, ?, ?, ?, ?)"),
            (
                evaluation_id,
                _now(),
                json.dumps(answers, ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
                user_id,
            ),
        )
        conn.commit()
    return evaluation_id


def list_evaluations(user_id: str, limit: int = 20, is_admin: bool = False) -> list[dict]:
    with _connect() as conn:
        if is_admin:
            rows = conn.execute(_param("SELECT id, created_at, result_json FROM evaluations ORDER BY created_at DESC LIMIT ?"), (limit,)).fetchall()
        else:
            rows = conn.execute(_param("SELECT id, created_at, result_json FROM evaluations WHERE user_id=? ORDER BY created_at DESC LIMIT ?"), (user_id, limit)).fetchall()
    return [
        {"id": row["id"], "createdAt": row["created_at"], "result": json.loads(row["result_json"])}
        for row in rows
    ]


def evaluation_owned(evaluation_id: str, user_id: str, is_admin: bool = False) -> bool:
    with _connect() as conn:
        if is_admin:
            row = conn.execute(_param("SELECT id FROM evaluations WHERE id=?"), (evaluation_id,)).fetchone()
        else:
            row = conn.execute(_param("SELECT id FROM evaluations WHERE id=? AND user_id=?"), (evaluation_id, user_id)).fetchone()
    return bool(row)


def save_case(payload: dict) -> dict:
    focus = _json_list(payload.get("focus")) or ["未分类"]
    item = {
        "id": str(uuid4()),
        "title": payload["title"].strip(),
        "relation": payload["relation"].strip(),
        "year": int(payload.get("year") or datetime.utcnow().year),
        "focus": focus,
        "summary": payload["summary"].strip(),
        "similarity": int(payload.get("similarity") or 78),
    }
    with _connect() as conn:
        conn.execute(
            _param(
                """
                INSERT INTO cases
                (id, title, relation, year, focus_json, summary, similarity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
            ),
            (
                item["id"],
                item["title"],
                item["relation"],
                item["year"],
                json.dumps(item["focus"], ensure_ascii=False),
                item["summary"],
                item["similarity"],
                _now(),
            ),
        )
        conn.commit()
    return item


def delete_case(case_id: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute(_param("DELETE FROM cases WHERE id = ?"), (case_id,))
        conn.commit()
    return cursor.rowcount > 0


def _case_match_score(item: dict, keyword: str) -> int:
    normalized = keyword.strip().lower()
    if not normalized:
        return int(item.get("similarity") or 60)
    terms = [term for term in normalized.replace("，", " ").replace("、", " ").replace(",", " ").split() if term]
    if not terms:
        terms = [normalized]
    haystacks = {
        "title": str(item["title"]).lower(),
        "relation": str(item["relation"]).lower(),
        "summary": str(item["summary"]).lower(),
        "focus": " ".join(str(tag).lower() for tag in item["focus"]),
    }
    score = 35
    for term in terms:
        if term in haystacks["title"]:
            score += 24
        if term in haystacks["focus"]:
            score += 22
        if term in haystacks["relation"]:
            score += 18
        if term in haystacks["summary"]:
            score += 12
    return max(35, min(98, score))


def list_cases(keyword: str = "") -> list[dict]:
    normalized = keyword.strip()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, title, relation, year, focus_json, summary, similarity
            FROM cases
            ORDER BY created_at DESC, year DESC
            """
        ).fetchall()

    items = [
        {
            "id": row["id"],
            "title": row["title"],
            "relation": row["relation"],
            "year": row["year"],
            "focus": json.loads(row["focus_json"]),
            "summary": row["summary"],
            "similarity": row["similarity"],
        }
        for row in rows
    ]
    for item in items:
        item["similarity"] = _case_match_score(item, normalized)
    if not normalized:
        return items
    return [
        item
        for item in items
        if normalized in item["title"]
        or normalized in item["summary"]
        or normalized in item["relation"]
        or any(normalized in tag for tag in item["focus"])
    ]


def save_knowledge(payload: dict) -> dict:
    points = _json_list(payload.get("points")) or ["待补充要点"]
    basis = _json_list(payload.get("basis")) or ["待补充依据"]
    tags = _json_list(payload.get("tags")) or [payload["category"].strip()]

    item = {
        "id": str(uuid4()),
        "category": payload["category"].strip(),
        "title": payload["title"].strip(),
        "summary": payload["summary"].strip(),
        "points": points,
        "basis": basis,
        "tags": tags,
    }
    with _connect() as conn:
        conn.execute(
            _param(
                """
                INSERT INTO knowledge
                (id, category, title, summary, points_json, basis_json, tags_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
            ),
            (
                item["id"],
                item["category"],
                item["title"],
                item["summary"],
                json.dumps(item["points"], ensure_ascii=False),
                json.dumps(item["basis"], ensure_ascii=False),
                json.dumps(item["tags"], ensure_ascii=False),
                _now(),
            ),
        )
        conn.commit()
    return item


def list_knowledge(keyword: str = "") -> list[dict]:
    normalized = keyword.strip()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, category, title, summary, points_json, basis_json, tags_json
            FROM knowledge
            ORDER BY created_at DESC
            """
        ).fetchall()

    items = [
        {
            "id": row["id"],
            "category": row["category"],
            "title": row["title"],
            "summary": row["summary"],
            "points": json.loads(row["points_json"]),
            "basis": json.loads(row["basis_json"]),
            "tags": json.loads(row["tags_json"]),
        }
        for row in rows
    ]
    if not normalized:
        return items
    return [
        item
        for item in items
        if normalized in item["title"]
        or normalized in item["summary"]
        or normalized in item["category"]
        or any(normalized in point for point in item["points"])
        or any(normalized in basis for basis in item["basis"])
        or any(normalized in tag for tag in item["tags"])
    ]


def platform_stats(user_id: str, is_admin: bool = False) -> dict:
    with _connect() as conn:
        if is_admin:
            rows = conn.execute("SELECT id, created_at, result_json FROM evaluations ORDER BY created_at DESC").fetchall()
            matter_count = _row_value(conn.execute("SELECT COUNT(*) AS total FROM matters").fetchone(), "total")
        else:
            rows = conn.execute(_param("SELECT id, created_at, result_json FROM evaluations WHERE user_id=? ORDER BY created_at DESC"), (user_id,)).fetchall()
            matter_count = _row_value(conn.execute(_param("SELECT COUNT(*) AS total FROM matters WHERE user_id=?"), (user_id,)).fetchone(), "total")
        case_count = _row_value(conn.execute("SELECT COUNT(*) AS total FROM cases").fetchone(), "total")

    evaluations = [
        {"id": row["id"], "createdAt": row["created_at"], "result": json.loads(row["result_json"])}
        for row in rows
    ]
    relation_counts: dict[str, int] = {}
    high_risk = 0
    for item in evaluations:
        result = item["result"]
        label = _clean_relation_label(result)
        result["relationLabel"] = label
        relation_counts[label] = relation_counts.get(label, 0) + 1
        if len(result.get("gaps", [])) >= 2:
            high_risk += 1

    return {
        "totalEvaluations": len(evaluations),
        "highRiskReports": high_risk,
        "relationDistribution": [
            {"name": name, "value": value} for name, value in relation_counts.items()
        ],
        "caseCount": case_count,
        "matterCount": matter_count,
        "latest": evaluations[:6],
    }


def save_matter(payload: dict, user_id: str) -> dict:
    now = _now()
    item = {
        "id": str(uuid4()), "title": payload["title"].strip(),
        "partyRole": payload.get("party_role", "主播"), "mcnName": payload.get("mcn_name", "").strip(),
        "disputeTypes": _json_list(payload.get("dispute_types")), "status": "处理中",
        "currentStep": 1, "evaluationId": payload.get("evaluation_id"), "createdAt": now, "updatedAt": now,
    }
    with _connect() as conn:
        conn.execute(_param("INSERT INTO matters (id,title,party_role,mcn_name,dispute_types_json,status,current_step,created_at,updated_at,user_id,evaluation_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)"),
            (item["id"], item["title"], item["partyRole"], item["mcnName"], json.dumps(item["disputeTypes"], ensure_ascii=False), item["status"], 1, now, now, user_id, item["evaluationId"]))
        conn.commit()
    item["evidence"] = []
    return item


def list_matters(user_id: str, is_admin: bool = False) -> list[dict]:
    with _connect() as conn:
        if is_admin:
            matters = conn.execute("SELECT * FROM matters ORDER BY updated_at DESC").fetchall()
        else:
            matters = conn.execute(_param("SELECT * FROM matters WHERE user_id=? ORDER BY updated_at DESC"), (user_id,)).fetchall()
        ids = [row["id"] for row in matters]
        evidence = conn.execute("SELECT * FROM evidence_items ORDER BY created_at DESC").fetchall() if ids else []
    by_matter: dict[str, list] = {}
    for row in evidence:
        if row["matter_id"] in ids:
            by_matter.setdefault(row["matter_id"], []).append({"id": row["id"], "category": row["category"], "name": row["name"], "status": row["status"], "note": row["note"], "storedName": row["stored_name"], "mimeType": row["mime_type"], "sizeBytes": row["size_bytes"]})
    return [{"id": row["id"], "title": row["title"], "partyRole": row["party_role"], "mcnName": row["mcn_name"], "disputeTypes": json.loads(row["dispute_types_json"]), "status": row["status"], "currentStep": row["current_step"], "evaluationId": row["evaluation_id"], "createdAt": row["created_at"], "updatedAt": row["updated_at"], "evidence": by_matter.get(row["id"], [])} for row in matters]


def update_matter(matter_id: str, payload: dict, user_id: str, is_admin: bool = False) -> bool:
    with _connect() as conn:
        if is_admin:
            cursor = conn.execute(_param("UPDATE matters SET status=?, current_step=?, updated_at=? WHERE id=?"), (payload.get("status", "处理中"), int(payload.get("current_step", 1)), _now(), matter_id))
        else:
            cursor = conn.execute(_param("UPDATE matters SET status=?, current_step=?, updated_at=? WHERE id=? AND user_id=?"), (payload.get("status", "处理中"), int(payload.get("current_step", 1)), _now(), matter_id, user_id))
        conn.commit()
    return cursor.rowcount > 0


def matter_owned(matter_id: str, user_id: str, is_admin: bool = False) -> bool:
    with _connect() as conn:
        if is_admin:
            row = conn.execute(_param("SELECT id FROM matters WHERE id=?"), (matter_id,)).fetchone()
        else:
            row = conn.execute(_param("SELECT id FROM matters WHERE id=? AND user_id=?"), (matter_id, user_id)).fetchone()
    return bool(row)


def delete_matter(matter_id: str, user_id: str, is_admin: bool = False) -> list[str] | None:
    if not matter_owned(matter_id, user_id, is_admin):
        return None
    with _connect() as conn:
        rows = conn.execute(_param("SELECT stored_name FROM evidence_items WHERE matter_id=?"), (matter_id,)).fetchall()
        conn.execute(_param("DELETE FROM evidence_items WHERE matter_id=?"), (matter_id,))
        conn.execute(_param("DELETE FROM matters WHERE id=?"), (matter_id,))
        conn.commit()
    return [row["stored_name"] for row in rows if row["stored_name"]]


def save_evidence(matter_id: str, payload: dict) -> dict:
    now = _now()
    item = {"id": str(uuid4()), "category": payload.get("category", "其他材料"), "name": payload["name"].strip(), "status": payload.get("status", "待核验"), "note": payload.get("note", "").strip(), "storedName": payload.get("stored_name", ""), "mimeType": payload.get("mime_type", ""), "sizeBytes": int(payload.get("size_bytes", 0))}
    with _connect() as conn:
        conn.execute(_param("INSERT INTO evidence_items (id,matter_id,category,name,status,note,created_at,updated_at,stored_name,mime_type,size_bytes) VALUES (?,?,?,?,?,?,?,?,?,?,?)"), (item["id"], matter_id, item["category"], item["name"], item["status"], item["note"], now, now, item["storedName"], item["mimeType"], item["sizeBytes"]))
        conn.commit()
    return item


def get_evidence(evidence_id: str, user_id: str, is_admin: bool = False) -> dict | None:
    with _connect() as conn:
        sql = """SELECT e.*, m.user_id FROM evidence_items e JOIN matters m ON m.id=e.matter_id WHERE e.id=?"""
        row = conn.execute(_param(sql), (evidence_id,)).fetchone()
    if not row or (not is_admin and row["user_id"] != user_id):
        return None
    return {"id": row["id"], "matterId": row["matter_id"], "name": row["name"], "storedName": row["stored_name"], "mimeType": row["mime_type"], "sizeBytes": row["size_bytes"]}


def delete_evidence(evidence_id: str, user_id: str, is_admin: bool = False) -> dict | None:
    item = get_evidence(evidence_id, user_id, is_admin)
    if not item:
        return None
    with _connect() as conn:
        conn.execute(_param("DELETE FROM evidence_items WHERE id=?"), (evidence_id,))
        conn.commit()
    return item


def log_action(user_id: str, action: str, entity_type: str, entity_id: str, detail: str = "") -> None:
    with _connect() as conn:
        conn.execute(_param("INSERT INTO audit_logs (id,user_id,action,entity_type,entity_id,detail,created_at) VALUES (?,?,?,?,?,?,?)"), (str(uuid4()), user_id, action, entity_type, entity_id, detail[:1000], _now()))
        conn.commit()


def list_audit_logs(limit: int = 100) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(_param("""SELECT a.*, COALESCE(u.name,'历史用户') AS user_name, COALESCE(u.email,'') AS user_email FROM audit_logs a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.created_at DESC LIMIT ?"""), (min(max(limit, 1), 500),)).fetchall()
    return [{"id": row["id"], "userName": row["user_name"], "userEmail": row["user_email"], "action": row["action"], "entityType": row["entity_type"], "entityId": row["entity_id"], "detail": row["detail"], "createdAt": row["created_at"]} for row in rows]


def delete_knowledge(knowledge_id: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute(_param("DELETE FROM knowledge WHERE id=?"), (knowledge_id,))
        conn.commit()
    return cursor.rowcount > 0
