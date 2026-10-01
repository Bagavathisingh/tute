import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from dotenv import load_dotenv
from fastapi import HTTPException
import certifi

load_dotenv()

# Accept both MONGODB_URI (standard Atlas naming) and MONGO_URI
MONGODB_URI = (
    os.getenv("MONGODB_URI") 
    or os.getenv("MONGO_URI") 
    or "mongodb://localhost:27017"
)
DATABASE_NAME = os.getenv("DATABASE_NAME", "schoolhub_db")

class MongoDBManager:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

db_manager = MongoDBManager()

def create_mongo_client(uri: str, allow_invalid: bool = False) -> AsyncIOMotorClient:
    kwargs = {"serverSelectionTimeoutMS": 10000}
    is_tls = "mongodb+srv://" in uri or "ssl=true" in uri.lower() or "tls=true" in uri.lower()
    if is_tls:
        if allow_invalid:
            kwargs["tlsAllowInvalidCertificates"] = True
        else:
            kwargs["tlsCAFile"] = certifi.where()
    return AsyncIOMotorClient(uri, **kwargs)

async def connect_to_mongo():
    """Establish connection to MongoDB Atlas / Local MongoDB."""
    try:
        allow_invalid = os.getenv("MONGODB_TLS_ALLOW_INVALID", "false").lower() in ("true", "1", "yes")
        db_manager.client = create_mongo_client(MONGODB_URI, allow_invalid=allow_invalid)
        db_manager.db = db_manager.client[DATABASE_NAME]

        # Verify connection by pinging
        try:
            await db_manager.client.admin.command('ping')
            masked_uri = MONGODB_URI.split("@")[-1] if "@" in MONGODB_URI else MONGODB_URI
            print(f"[MongoDB Atlas] Successfully connected and pinged database: '{DATABASE_NAME}' via {masked_uri}")
        except Exception as ping_err:
            err_str = str(ping_err)
            if "SSL" in err_str or "TLS" in err_str:
                print(f"[MongoDB Atlas] Standard TLS handshake encountered: {err_str}")
                print("[MongoDB Atlas] Retrying with TLS fallback (tlsAllowInvalidCertificates=True)...")
                db_manager.client = create_mongo_client(MONGODB_URI, allow_invalid=True)
                db_manager.db = db_manager.client[DATABASE_NAME]
                await db_manager.client.admin.command('ping')
                print(f"[MongoDB Atlas] Fallback TLS connection successful!")
            else:
                raise ping_err
    except Exception as e:
        print(f"[MongoDB Atlas] Startup ping warning: {e}")
        # Ensure client and db objects exist so requests can connect once network access is active
        if db_manager.db is None:
            allow_invalid = True
            db_manager.client = create_mongo_client(MONGODB_URI, allow_invalid=allow_invalid)
            db_manager.db = db_manager.client[DATABASE_NAME]

async def close_mongo_connection():
    """Close MongoDB connection gracefully."""
    if db_manager.client:
        db_manager.client.close()
        print("[MongoDB Atlas] Connection closed.")

def get_database() -> AsyncIOMotorDatabase:
    """Dependency injector for routes."""
    # 1. Check if aliased module has the initialized db
    if db_manager.db is None:
        for mod_name in ["backend.app.core.database", "app.core.database"]:
            if mod_name in sys.modules:
                mod = sys.modules[mod_name]
                if getattr(mod, "db_manager", None) and mod.db_manager.db is not None:
                    db_manager.client = mod.db_manager.client
                    db_manager.db = mod.db_manager.db
                    return db_manager.db

    # 2. If client exists but db is None, assign db
    if db_manager.db is None and db_manager.client is not None:
        db_manager.db = db_manager.client[DATABASE_NAME]

    # 3. If client itself is None, initialize on-demand
    if db_manager.db is None:
        try:
            allow_invalid = os.getenv("MONGODB_TLS_ALLOW_INVALID", "true").lower() in ("true", "1", "yes")
            db_manager.client = create_mongo_client(MONGODB_URI, allow_invalid=allow_invalid)
            db_manager.db = db_manager.client[DATABASE_NAME]
        except Exception:
            pass

    if db_manager.db is None:
        raise HTTPException(
            status_code=503,
            detail="Database connection is currently unavailable. Please verify MONGODB_URI."
        )
    return db_manager.db

# Keep sys.modules in sync so imports from app.core.database and backend.app.core.database share the exact same object
if "backend.app.core.database" not in sys.modules and "app.core.database" in sys.modules:
    sys.modules["backend.app.core.database"] = sys.modules["app.core.database"]
elif "app.core.database" not in sys.modules and "backend.app.core.database" in sys.modules:
    sys.modules["app.core.database"] = sys.modules["backend.app.core.database"]
