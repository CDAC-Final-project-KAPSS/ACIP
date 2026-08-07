from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:root@localhost:5432/acip_platform_db"
    CHROMA_COLLECTION: str = "acip_regulations"
    LOCAL_STORAGE_PATH: str = "./storage"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
