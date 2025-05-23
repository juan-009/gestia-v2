from fastapi import FastAPI
from auth_service.app.shared.config.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0", # You might want to make version configurable too
    debug=settings.DEBUG
)

# Lifespan events for Redis
from auth_service.app.infraestructura.cache.redis_client import get_redis_pool, close_redis_pool

@app.on_event("startup")
async def startup_event():
    try:
        await get_redis_pool() # Establishes and pings Redis
        print("Redis pool initialized successfully via startup event.")
    except ConnectionError as e:
        # Handle Redis connection error on startup, e.g., log and exit or run without cache
        print(f"CRITICAL: Could not connect to Redis during startup: {e}")
        # Depending on policy, you might want to sys.exit(1) if Redis is essential
        # For now, we'll print an error and the app will continue to run,
        # but caching features will likely fail or be disabled.
        # The get_redis_pool itself raises ConnectionError if ping fails.

@app.on_event("shutdown")
async def shutdown_event():
    await close_redis_pool()
    print("Redis pool closed via shutdown event.")

# Import middlewares
from auth_service.app.interfaces.api.middlewares.error_handler import global_exception_handler_middleware
from auth_service.app.interfaces.api.middlewares.auth import JWTAuthMiddleware
# from fastapi.middleware.cors import CORSMiddleware # Example, if needed

# Add Error Handler Middleware using the old style (app.middleware("http"))
# This will be one of the outermost layers, catching errors from subsequent middlewares and routes.
app.middleware("http")(global_exception_handler_middleware)

# Add JWT Auth Middleware (runs after error handler in terms of wrapping response, before in terms of processing request)
app.add_middleware(JWTAuthMiddleware)

# Example CORS (if needed, configure origins appropriately)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"], # Or specific origins: e.g., ["http://localhost:3000"]
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Import and include routers
from auth_service.app.interfaces.api.v1.routers import auth as auth_router
from auth_service.app.interfaces.api.v1.routers import permissions as permissions_router
from auth_service.app.interfaces.api.v1.routers import roles as roles_router
from auth_service.app.interfaces.api.v1.routers import usuarios as usuarios_router # New

app.include_router(auth_router.router)
app.include_router(permissions_router.router)
app.include_router(roles_router.router)
app.include_router(usuarios_router.router) # New

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}
