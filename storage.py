import datetime

import aiosqlite

import config

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS channels (
    channel_id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL,
    title TEXT,
    auto_enabled INTEGER DEFAULT 0,
    interval_hours REAL DEFAULT 3,
    last_run_at TEXT,
    active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER,
    timestamp TEXT,
    scraped INTEGER,
    working INTEGER,
    failed INTEGER
);
CREATE TABLE IF NOT EXISTS proxies (
    channel_id INTEGER,
    proxy TEXT,
    protocol TEXT,
    country TEXT,
    latency REAL,
    checked_at TEXT,
    PRIMARY KEY (channel_id, proxy)
);
"""


async def init_db() -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.executescript(_INIT_SQL)
        await db.commit()


async def count_channels_by_owner(owner_id: int) -> int:
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM channels WHERE owner_id = ? AND active = 1", (owner_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def register_channel(channel_id: int, owner_id: int, title: str) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "INSERT INTO channels (channel_id, owner_id, title, auto_enabled, interval_hours, active) "
            "VALUES (?, ?, ?, 0, ?, 1) "
            "ON CONFLICT(channel_id) DO UPDATE SET owner_id = excluded.owner_id, title = excluded.title, active = 1",
            (channel_id, owner_id, title, config.AUTO_INTERVAL_HOURS),
        )
        await db.commit()


async def deactivate_channel(channel_id: int) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE channels SET active = 0, auto_enabled = 0 WHERE channel_id = ?", (channel_id,))
        await db.commit()


async def remove_channel(channel_id: int, owner_id: int) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("DELETE FROM channels WHERE channel_id = ? AND owner_id = ?", (channel_id, owner_id))
        await db.execute("DELETE FROM proxies WHERE channel_id = ?", (channel_id,))
        await db.commit()


async def get_channels_by_owner(owner_id: int) -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            "SELECT channel_id, title, auto_enabled, interval_hours FROM channels "
            "WHERE owner_id = ? AND active = 1 ORDER BY title",
            (owner_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [
                {"channel_id": r[0], "title": r[1], "auto_enabled": bool(r[2]), "interval_hours": r[3]}
                for r in rows
            ]


async def get_channel(channel_id: int) -> dict | None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            "SELECT channel_id, owner_id, title, auto_enabled, interval_hours, last_run_at "
            "FROM channels WHERE channel_id = ? AND active = 1",
            (channel_id,),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return {
                "channel_id": row[0],
                "owner_id": row[1],
                "title": row[2],
                "auto_enabled": bool(row[3]),
                "interval_hours": row[4],
                "last_run_at": row[5],
            }


async def set_channel_auto(channel_id: int, enabled: bool) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE channels SET auto_enabled = ? WHERE channel_id = ?", (1 if enabled else 0, channel_id))
        await db.commit()


async def set_channel_interval(channel_id: int, hours: float) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE channels SET interval_hours = ? WHERE channel_id = ?", (hours, channel_id))
        await db.commit()


async def get_due_channels() -> list[int]:
    now = datetime.datetime.utcnow()
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            "SELECT channel_id, interval_hours, last_run_at FROM channels WHERE active = 1 AND auto_enabled = 1"
        ) as cur:
            rows = await cur.fetchall()

    due = []
    for channel_id, interval_hours, last_run_at in rows:
        if not last_run_at:
            due.append(channel_id)
            continue
        last_run = datetime.datetime.strptime(last_run_at, "%Y-%m-%d %H:%M:%S")
        if (now - last_run).total_seconds() >= interval_hours * 3600:
            due.append(channel_id)
    return due


async def save_run_result(channel_id: int, scraped: int, working: list[dict]) -> None:
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "INSERT INTO stats (channel_id, timestamp, scraped, working, failed) VALUES (?, ?, ?, ?, ?)",
            (channel_id, now, scraped, len(working), max(scraped - len(working), 0)),
        )
        await db.execute("DELETE FROM proxies WHERE channel_id = ?", (channel_id,))
        if working:
            await db.executemany(
                "INSERT INTO proxies (channel_id, proxy, protocol, country, latency, checked_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [(channel_id, p["proxy"], p["protocol"], p["country"], p["latency"], now) for p in working],
            )
        await db.execute("UPDATE channels SET last_run_at = ? WHERE channel_id = ?", (now, channel_id))
        await db.commit()


async def get_last_stats(channel_id: int) -> dict | None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            "SELECT timestamp, scraped, working, failed FROM stats WHERE channel_id = ? ORDER BY id DESC LIMIT 1",
            (channel_id,),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return {"timestamp": row[0], "scraped": row[1], "working": row[2], "failed": row[3]}


async def get_working_proxies(channel_id: int) -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute(
            "SELECT proxy, protocol, country, latency FROM proxies WHERE channel_id = ? ORDER BY latency ASC",
            (channel_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [
                {"proxy": r[0], "protocol": r[1], "country": r[2], "latency": r[3]}
                for r in rows
            ]
