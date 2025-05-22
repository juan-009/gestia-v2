from fastapi import FastAPI
from auth_service.app.shared.config.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0", # You might want to make version configurable too
    debug=settings.DEBUG
)

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
app.include_router(auth_router.router)

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}
