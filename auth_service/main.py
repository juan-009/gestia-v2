from fastapi import FastAPI
from .api.endpoints import auth as auth_router
from .api.endpoints import roles as roles_router # Import roles router
from .db.database import create_db_and_tables # For dev convenience

# TODO: For production, consider using lifespan events for DB setup/teardown
# For development, we call it here to ensure tables are created.
# Be cautious with this approach in production (e.g., if you have multiple workers).
# Ensure your database is running and accessible before starting the app.
# Example: Run `python -m auth_service.db.database` once manually first.
try:
    create_db_and_tables() 
    print("Database tables checked/created (if they didn't exist).")
except Exception as e:
    print(f"Error during initial table creation: {e}")
    print("Please ensure your PostgreSQL server is running and accessible,")
    print("and that the database 'auth_db' exists with correct user/password.")
    # Depending on the severity, you might want to exit or re-raise
    # For now, we'll let the app try to start, but it will likely fail on DB operations.

app = FastAPI(title="Auth Core Service")

app.include_router(auth_router.router)
app.include_router(roles_router.router) # Register roles router

@app.get("/")
async def root():
    return {"message": "Welcome to Auth Core Service"}
