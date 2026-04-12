import aiosqlite
from app.config import DB_PATH

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(str(DB_PATH))
        _db.row_factory = aiosqlite.Row
    return _db


async def init_db():
    db = await get_db()
    await db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migrations for existing DBs
    cursor = await db.execute("PRAGMA table_info(sessions)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "is_admin" not in cols:
        await db.execute("ALTER TABLE sessions ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    if "guest_name" not in cols:
        await db.execute("ALTER TABLE sessions ADD COLUMN guest_name TEXT")
    await db.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            original_filename TEXT,
            mime_type TEXT,
            file_extension TEXT,
            file_size INTEGER,
            is_official INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    # Migrations for existing uploads table
    cursor = await db.execute("PRAGMA table_info(uploads)")
    upload_cols = {row[1] for row in await cursor.fetchall()}
    if "is_official" not in upload_cols:
        await db.execute("ALTER TABLE uploads ADD COLUMN is_official INTEGER NOT NULL DEFAULT 0")
    await db.commit()
