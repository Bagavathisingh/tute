import sys
from pathlib import Path

# Ensure both backend directory and repository root are on sys.path
BASE_DIR = Path(__file__).resolve().parent
PARENT_DIR = BASE_DIR.parent
for p in [str(BASE_DIR), str(PARENT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import app
    sys.modules["backend.app"] = app
    import app.core.database
    sys.modules["backend.app.core.database"] = app.core.database
except Exception:
    pass
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.core.seed import seed_initial_data
from app.routers import students, standards, timetables, auth, exams, tests

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await connect_to_mongo()
        db = get_database()
        if db is not None:
            await seed_initial_data(db)
    except Exception as e:
        print(f"[Startup Warning] Could not initialize MongoDB: {e}")
        print("Please ensure your MONGODB_URI is correctly set in backend/.env")
    
    yield
    
    await close_mongo_connection()

app = FastAPI(
    title="SchoolHub Management API (MongoDB Atlas)",
    description="Full-stack educational management API with MongoDB Atlas persistence",
    version="1.0.0",
    lifespan=lifespan
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(standards.router)
app.include_router(timetables.router)
app.include_router(exams.router)
app.include_router(tests.router)

@app.get("/")
def read_root():
    return {
        "app": "SchoolHub Management API",
        "status": "online",
        "database": "MongoDB Atlas",
        "docs": "/docs"
    }

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
