import asyncio
from app.db.database import Base, engine
from app.db.models.models import *

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created successfully.")

if __name__ == "__main__":
    asyncio.run(init())
