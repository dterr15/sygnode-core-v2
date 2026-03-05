"""Startup script — creates all tables and applies PostgreSQL rules."""

import asyncio
from sqlalchemy import text
from app.database import engine, Base
from app.models import *  # noqa: F401, F403


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Apply append-only rules for timeline (G1)
        await conn.execute(text(
            "CREATE RULE IF NOT EXISTS no_update_timeline "
            "AS ON UPDATE TO case_timeline_events DO INSTEAD NOTHING;"
        ))
        await conn.execute(text(
            "CREATE RULE IF NOT EXISTS no_delete_timeline "
            "AS ON DELETE TO case_timeline_events DO INSTEAD NOTHING;"
        ))

    print("Database initialized successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())
