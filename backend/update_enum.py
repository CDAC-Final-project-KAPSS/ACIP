import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:root@localhost:5432/acip_platform_db"

async def migrate_enum():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TYPE userrole RENAME VALUE 'uploader' TO 'employee'"))
            print("Enum updated successfully")
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(migrate_enum())
