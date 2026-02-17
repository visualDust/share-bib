import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from api.auth import router as auth_router
from api.collections import router as collections_router
from api.papers import router as papers_router
from api.import_tasks import router as import_router
from api.users import router as users_router
from api.admin import router as admin_router
from api.system import router as system_router

app = FastAPI(title="Paper Collector", version="0.1.0")

frontend_port = os.environ.get("FRONTEND_PORT", "11551")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{frontend_port}",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(collections_router)
app.include_router(papers_router)
app.include_router(import_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(system_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/stats")
def global_stats():
    from database import SessionLocal
    from models import Collection, Paper

    db = SessionLocal()
    try:
        return {
            "collections": db.query(Collection).count(),
            "papers": db.query(Paper).count(),
        }
    finally:
        db.close()
