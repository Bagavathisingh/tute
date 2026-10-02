import sys
from pathlib import Path

# Ensure both backend directory and repository root are on sys.path
BASE_DIR = Path(__file__).resolve().parent
PARENT_DIR = BASE_DIR.parent
for p in [str(BASE_DIR), str(PARENT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Alias app and backend.app so all router imports share the exact same modules
try:
    import app
    sys.modules["backend.app"] = app
    import app.core.database
    sys.modules["backend.app.core.database"] = app.core.database
except Exception:
    pass
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.core.seed import seed_initial_data
from app.routers import students, standards, timetables, auth, exams, tests


class CORSAlwaysMiddleware(BaseHTTPMiddleware):
    """Ensures CORS headers are present on EVERY response, including errors."""
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "*")

        # Handle preflight OPTIONS immediately
        if request.method == "OPTIONS":
            return JSONResponse(
                content={"detail": "OK"},
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-User-Role, X-Requested-With",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "600",
                },
            )

        try:
            response = await call_next(request)
        except Exception:
            response = JSONResponse(
                content={"detail": "Internal server error"},
                status_code=500,
            )

        # Always add CORS headers
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
        return response

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# CORSAlwaysMiddleware runs as an outer wrapper — catches errors that bypass CORSMiddleware
app.add_middleware(CORSAlwaysMiddleware)

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
