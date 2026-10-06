import logging
import os
from contextlib import asynccontextmanager
import pymysql
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config.settings import settings
from app.helper.storage import ensure_storage_directories
from app.model.seed_model import run_seed
from app.routes import auth, admin, teacher, student, files

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smartclassroom.main")

import asyncio
from app.helper.reminder_service import check_and_send_assignment_reminders

async def assignment_reminder_worker():
    """Background worker that periodically checks and triggers assignment reminders every 60 seconds."""
    logger.info("Assignment reminder background scheduler started.")
    while True:
        try:
            await asyncio.to_thread(check_and_send_assignment_reminders)
        except asyncio.CancelledError:
            logger.info("Assignment reminder scheduler cancelled.")
            break
        except Exception as err:
            logger.error(f"Error in assignment reminder worker: {err}")
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            break

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("Initializing SmartClassroom application...")
    ensure_storage_directories()
    is_vercel = os.getenv("VERCEL") == "1"
    if not is_vercel:
        run_seed()
        logger.info("Storage directories and initial database seeds ready.")
    else:
        logger.info("Storage directories ready; database seeding is managed outside Vercel cold starts.")
    reminder_task = None
    if not is_vercel:
        reminder_task = asyncio.create_task(assignment_reminder_worker())
    yield
    # Shutdown tasks
    logger.info("Shutting down SmartClassroom application.")
    if reminder_task:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    root_path="/api",
    title="SmartClassroom API",
    description="Backend API for SmartClassroom (University College of Jaffna) with JWT Auth, Role RBAC, Google App Password Email, and Dual File Storage.",
    version="1.0.0",
    lifespan=lifespan
)

@app.exception_handler(pymysql.MySQLError)
async def database_error_handler(request: Request, exc: pymysql.MySQLError):
    logger.error("Database request failed: %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": f"Database connection error: {exc}"
        }
    )

@app.exception_handler(RuntimeError)
async def database_configuration_error_handler(request: Request, exc: RuntimeError):
    logger.error("Database configuration failed: %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": str(exc) if "Database host" in str(exc) else "Database configuration failed. Set DB_HOST in .env."
        }
    )

# Keep local development convenient while allowing a locked-down production origin.
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()] if settings else ["*"]

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(teacher.router)
app.include_router(student.router)
app.include_router(files.router)

@app.get("/")
def root():
    return {
        "status": "online",
        "system": "SmartClassroom API v1.0",
        "institution": "University College of Jaffna",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
