"""
Dual-backend database client for content-os.

Supports SQLite (default, zero-config) and Supabase Postgres (upgrade path).
All scripts use execute() and execute_one() — the backend is transparent.

SQLite mode:
    - Database file: <project_root>/data/content.db
    - No schema prefix (ops. is stripped from queries)
    - %s placeholders converted to ?
    - JSONB columns stored as TEXT
    - NOW() converted to datetime('now')

Supabase mode:
    - Requires SUPABASE_DB_URL in .env
    - Uses psycopg2 with RealDictCursor
    - ops schema with search_path set

Usage:
    from lib.db import execute, execute_one

    rows = execute("SELECT * FROM ops.content_items WHERE platform = %s", ("youtube",))
    row = execute_one("SELECT * FROM ops.content_items WHERE id = %s", (42,))
"""

import json
import os
import re
import sqlite3
import threading
from pathlib import Path

# Lazy imports for Postgres (may not be installed)
_psycopg2 = None
_pg_pool_mod = None

_PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent),
)


def _find_project_root() -> Path:
    """Walk up from CWD to find project root."""
    cwd = Path.cwd()
    for p in [cwd] + list(cwd.parents):
        if (p / ".claude").is_dir():
            return p
    return cwd


def _load_env():
    """Load .env from project root."""
    root = _find_project_root()
    env_path = root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

def _get_backend() -> str:
    """Determine database backend from config or environment."""
    # Check .claude/content-os.local.md config
    root = _find_project_root()
    config_path = root / ".claude" / "content-os.local.md"
    if config_path.exists():
        text = config_path.read_text()
        if "backend: supabase" in text:
            if os.environ.get("SUPABASE_DB_URL"):
                return "supabase"

    # Fallback: if SUPABASE_DB_URL is set, use it
    if os.environ.get("SUPABASE_DB_URL"):
        return "supabase"

    return "sqlite"


_backend = _get_backend()


# ---------------------------------------------------------------------------
# SQLite backend
# ---------------------------------------------------------------------------

_sqlite_lock = threading.Lock()
_sqlite_conn: sqlite3.Connection | None = None


def _get_sqlite_path() -> Path:
    """Get path to SQLite database file."""
    root = _find_project_root()
    db_dir = root / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "content.db"


def _get_sqlite_conn() -> sqlite3.Connection:
    """Get or create SQLite connection (thread-safe singleton)."""
    global _sqlite_conn
    with _sqlite_lock:
        if _sqlite_conn is None:
            db_path = _get_sqlite_path()
            _sqlite_conn = sqlite3.connect(str(db_path), check_same_thread=False)
            _sqlite_conn.row_factory = sqlite3.Row
            _sqlite_conn.execute("PRAGMA journal_mode=WAL")
            _sqlite_conn.execute("PRAGMA foreign_keys=ON")
    return _sqlite_conn


def _sqlite_adapt_query(query: str) -> str:
    """Adapt a Postgres query to SQLite.

    Converts:
    - ops.table_name → table_name (strip schema prefix)
    - %s → ? (parameter placeholders)
    - NOW() → datetime('now')
    - SERIAL PRIMARY KEY → INTEGER PRIMARY KEY AUTOINCREMENT
    - TIMESTAMPTZ → TEXT
    - JSONB → TEXT
    - INTERVAL '1 day' * %s → datetime('now', '-' || ? || ' days') — handled in specific queries
    - RETURNING * → stripped (SQLite doesn't support RETURNING in older versions)
    """
    # Strip schema prefix
    query = re.sub(r'\bops\.', '', query)

    # Parameter placeholders
    query = query.replace('%s', '?')

    # NOW() → datetime('now')
    query = re.sub(r'\bNOW\(\)', "datetime('now')", query, flags=re.IGNORECASE)

    # INTERVAL patterns
    # INTERVAL '1 day' * ? → (datetime('now', '-' || ? || ' days'))
    query = re.sub(
        r"INTERVAL\s+'1 day'\s*\*\s*\?",
        "(? || ' days')",
        query,
        flags=re.IGNORECASE,
    )
    # Fix the comparison: > NOW() - INTERVAL... → > datetime('now', '-' || ? || ' days')
    query = re.sub(
        r">\s*datetime\('now'\)\s*-\s*\(\?\s*\|\|\s*' days'\)",
        "> datetime('now', '-' || ? || ' days')",
        query,
        flags=re.IGNORECASE,
    )

    # Type conversions (for CREATE TABLE)
    query = re.sub(r'\bSERIAL\b', 'INTEGER', query, flags=re.IGNORECASE)
    query = re.sub(r'\bTIMESTAMPTZ\b', 'TEXT', query, flags=re.IGNORECASE)
    query = re.sub(r'\bJSONB\b', 'TEXT', query, flags=re.IGNORECASE)

    return query


def _sqlite_execute(query: str, params=None, fetch=True):
    """Execute query on SQLite backend."""
    conn = _get_sqlite_conn()
    adapted = _sqlite_adapt_query(query)

    # Handle RETURNING clause — SQLite 3.35+ supports it, but we'll handle gracefully
    has_returning = "RETURNING" in adapted.upper()

    try:
        cur = conn.cursor()
        cur.execute(adapted, params or ())

        if has_returning and fetch:
            rows = cur.fetchall()
            conn.commit()
            return [_sqlite_row_to_dict(r) for r in rows]
        elif fetch and adapted.strip().upper().startswith("SELECT"):
            rows = cur.fetchall()
            return [_sqlite_row_to_dict(r) for r in rows]
        elif fetch and has_returning:
            rows = cur.fetchall()
            conn.commit()
            return [_sqlite_row_to_dict(r) for r in rows]
        else:
            conn.commit()
            if has_returning:
                # Fallback: return last inserted row
                last_id = cur.lastrowid
                if last_id:
                    table_match = re.search(r'(?:INSERT INTO|UPDATE)\s+(\w+)', adapted, re.IGNORECASE)
                    if table_match:
                        table = table_match.group(1)
                        cur.execute(f"SELECT * FROM {table} WHERE id = ?", (last_id,))
                        row = cur.fetchone()
                        return [_sqlite_row_to_dict(row)] if row else []
            return cur.rowcount
    except Exception:
        conn.rollback()
        raise


def _sqlite_row_to_dict(row: sqlite3.Row) -> dict:
    """Convert sqlite3.Row to a regular dict, parsing JSON fields."""
    d = dict(row)
    # Parse JSON text fields that should be dicts
    for key in ("metadata",):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


# ---------------------------------------------------------------------------
# Postgres (Supabase) backend
# ---------------------------------------------------------------------------

_pg_pool = None
_pg_pool_lock = threading.Lock()


def _get_pg_pool():
    """Get or create Postgres connection pool."""
    global _pg_pool, _psycopg2, _pg_pool_mod

    with _pg_pool_lock:
        if _pg_pool is None or _pg_pool.closed:
            import psycopg2
            from psycopg2 import pool as pg_pool_mod
            from psycopg2.extras import RealDictCursor

            _psycopg2 = psycopg2
            _pg_pool_mod = pg_pool_mod

            db_url = os.environ.get("SUPABASE_DB_URL")
            if not db_url:
                raise RuntimeError("SUPABASE_DB_URL not set in .env")

            _pg_pool = pg_pool_mod.ThreadedConnectionPool(
                minconn=1,
                maxconn=5,
                dsn=db_url,
                cursor_factory=RealDictCursor,
                options="-c search_path=ops,public,extensions",
            )
    return _pg_pool


def _pg_execute(query: str, params=None, fetch=True):
    """Execute query on Postgres backend."""
    pool = _get_pg_pool()
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if fetch:
            result = cur.fetchall()
        else:
            result = cur.rowcount
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def execute(query: str, params=None, fetch=True):
    """Execute a query and return results as list of dicts.

    Works transparently on both SQLite and Postgres backends.

    For INSERT/UPDATE/DELETE without RETURNING, set fetch=False.
    For INSERT ... RETURNING, keep fetch=True.
    """
    if _backend == "supabase":
        return _pg_execute(query, params, fetch)
    else:
        return _sqlite_execute(query, params, fetch)


def execute_one(query: str, params=None):
    """Execute a query and return a single row as dict, or None."""
    rows = execute(query, params, fetch=True)
    if isinstance(rows, list) and rows:
        return rows[0]
    return None


def get_backend() -> str:
    """Return the current database backend name."""
    return _backend


def init_db():
    """Initialize database tables.

    For SQLite: creates tables directly.
    For Supabase: runs the migration SQL.
    """
    migration_path = Path(_PLUGIN_ROOT) / "migrations" / "001_content_tables.sql"
    if not migration_path.exists():
        raise FileNotFoundError(f"Migration not found: {migration_path}")

    sql = migration_path.read_text()

    if _backend == "sqlite":
        conn = _get_sqlite_conn()
        # Adapt and execute each statement
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        for stmt in statements:
            adapted = _sqlite_adapt_query(stmt)
            # Skip CREATE INDEX with WHERE (SQLite partial index syntax differs)
            # and skip CREATE SCHEMA
            if "CREATE SCHEMA" in adapted.upper():
                continue
            # Remove CHECK constraints that reference complex expressions
            try:
                conn.execute(adapted)
            except sqlite3.OperationalError as e:
                if "already exists" in str(e):
                    continue
                raise
        conn.commit()
        return {"success": True, "backend": "sqlite", "path": str(_get_sqlite_path())}
    else:
        # For Supabase, execute the raw SQL
        pool = _get_pg_pool()
        conn = pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute(sql)
            conn.commit()
            return {"success": True, "backend": "supabase"}
        except Exception:
            conn.rollback()
            raise
        finally:
            pool.putconn(conn)
