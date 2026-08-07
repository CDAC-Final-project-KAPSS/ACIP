from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import cases, auth, admin

from contextlib import asynccontextmanager
from app.db.database import AsyncSessionLocal
from app.db.models.models import User, UserRole
from sqlalchemy.future import select
from app.api.v1.auth import pwd_context

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed admin user
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.email == "p4shinde2003@gmail.com")
        result = await db.execute(stmt)
        admin = result.scalar_one_or_none()
        
        if not admin:
            admin_user = User(
                email="p4shinde2003@gmail.com",
                password_hash=pwd_context.hash("Admin@100"),
                role=UserRole.admin,
                is_verified=True,
                approval_status="APPROVED"
            )
            db.add(admin_user)
            await db.commit()
            print("Admin user seeded successfully.")
    yield

app = FastAPI(
    title="ACIP API",
    description="Autonomous Customs Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router)
app.include_router(auth.router)
app.include_router(admin.router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "ACIP API is running"}
