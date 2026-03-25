from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from study_app.ingestion import ingestion
from study_app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Adaptive Brain API",
    description="AI-powered study companion — input ingestion service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(ingestion.router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "adaptive-brain-api"}
