from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.health import router as health_router
from .routers.resume import router as resume_router
from .assessment.quiz.api import router as quiz_router
from .routers.candidate import router as candidate_router
from .routers.admin import router as admin_router
from .routers.ranking import router as ranking_router
from .routers.company import router as company_router
from .routers.job import router as job_router
from .routers.auth import router as auth_router
from .routers.notification import router as notify_router
from .routers.company_settings import router as company_settings_router
from .assessment.coding.router import router as coding_router
from .database.mongodb import check_mongo_connection, create_indexes


def create_app() -> FastAPI:
    app = FastAPI(
        title="ATS Platform",
        version="1.0.0"
    )

    # ==============================
    # STARTUP EVENTS (DB + INDEXES)
    # ==============================
    @app.on_event("startup")
    async def startup_event():
        await check_mongo_connection()
        await create_indexes()

    # ==============================
    # CORS CONFIGURATION
    # ==============================
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://10.60.42.214:8080",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ==============================
    # ROUTERS
    # ==============================
    app.include_router(health_router)
    app.include_router(resume_router)
    app.include_router(quiz_router)
    app.include_router(candidate_router)
    app.include_router(admin_router)
    app.include_router(ranking_router)
    app.include_router(company_router)
    app.include_router(job_router)
    app.include_router(auth_router)
    app.include_router(notify_router)
    app.include_router(company_settings_router)
    app.include_router(coding_router)

    return app


app = create_app()