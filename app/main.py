from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.config import get_settings
from app.database import engine, Base, get_db
from app.routers import books, auth
from app import schemas

settings = get_settings()

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A sample Bookstore REST API for demonstrating API testing patterns.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(books.router)


@app.get("/health", response_model=schemas.HealthResponse, tags=["health"])
def health_check():
    """Health check endpoint."""
    db_status = "ok"
    try:
        db = next(get_db())
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
    except OperationalError:
        db_status = "error"

    return schemas.HealthResponse(
        status="ok",
        version=settings.app_version,
        database=db_status,
    )


@app.get("/", tags=["root"])
def root():
    return {"message": f"Welcome to {settings.app_name}", "docs": "/docs"}
