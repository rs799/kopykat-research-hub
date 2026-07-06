from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from .config import get_settings

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"

# Columns added by migrations after 001_init.sql that need to land on tables
# that may already exist (and may already contain data). We add these via
# the SQLAlchemy inspector instead of raw "ALTER TABLE ... ADD COLUMN" in a
# .sql file so that re-running init-db is always safe, and so the same code
# works whether the underlying DB is SQLite or Postgres.
_EXTRA_COLUMNS: dict[str, dict[str, str]] = {
    "wallet_scores": {
        # Realized (resolved-market) performance - the only performance we
        # trust as evidence of skill.
        "realized_pnl": "REAL",
        "realized_roi": "REAL",
        "resolved_trade_count": "INTEGER",
        # Unrealized/open-position performance - stored for visibility only,
        # never folded into final_score.
        "unrealized_pnl": "REAL",
        "open_position_count": "INTEGER",
        # New scoring components.
        "liquidity_score": "REAL",
        "recency_score": "REAL",
        "exit_quality_score": "REAL",
        "clv_sample_size": "INTEGER",
        # Full transparent breakdown (weight/raw score/contribution/note per
        # component), stored as JSON so the dashboard can show "why" a wallet
        # got its score without re-deriving it.
        "component_json": "TEXT",
    }
}


def get_engine() -> Engine:
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url.replace("sqlite:///", "")
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(settings.database_url, future=True)


def _run_sql_file(conn, path: Path) -> None:
    """Execute every statement in a .sql file.

    Comment lines (starting with `--`) are stripped before splitting on `;`.
    Without this, a semicolon inside a comment (e.g. "do X; then Y" in an
    explanatory note) would be mistaken for a statement boundary and break
    the SQL that follows. All comments in this project's migrations are
    full-line, so line-level stripping is sufficient - this does not handle
    semicolons inside string literals or inline trailing comments.
    """
    sql = path.read_text(encoding="utf-8")
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    cleaned = "\n".join(lines)
    statements = [s.strip() for s in cleaned.split(";") if s.strip()]
    for stmt in statements:
        conn.execute(text(stmt))


def _ensure_extra_columns(engine: Engine) -> None:
    """Idempotently add columns introduced by later migrations.

    Using the inspector (rather than a raw ALTER TABLE in a .sql file) means
    running init-db repeatedly never errors with "duplicate column" and never
    requires dropping/recreating a table that might already have data.
    """
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table, columns in _EXTRA_COLUMNS.items():
            if table not in table_names:
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for col_name, col_type in columns.items():
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))


def init_db(engine: Engine | None = None) -> None:
    engine = engine or get_engine()
    sql_files = sorted(SQL_DIR.glob("*.sql"))
    with engine.begin() as conn:
        for sql_file in sql_files:
            _run_sql_file(conn, sql_file)
    _ensure_extra_columns(engine)
