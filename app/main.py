"""
OJ System - Main Application Entry Point
"""
import os
import sys
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.routers import auth, users, problems, submissions, logs, admin
from app.repositories.manager import init_data


SESSION_SECRET = os.environ.get("SESSION_SECRET", "oj-dev-secret-key-change-in-production")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize data on startup."""
    init_data()
    yield


app = FastAPI(
    title="OJ System",
    description="Online Judge System built with FastAPI",
    version="1.0.0",
    lifespan=lifespan,
)

# Global exception handlers: convert to unified response format
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": str(exc.detail),
            "data": None,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "validation error", "data": None},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "internal server error", "data": None},
    )

# Session middleware for cookie-based auth
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(problems.router, prefix="/api")
app.include_router(submissions.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "OJ System API is running"}
