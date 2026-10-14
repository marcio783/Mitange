import os
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import init_db
from .errors import AppError
from .routers import clientes, dashboard, equipamentos, ordens, pecas


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="TechFix Pro API", version="1.0.0", lifespan=lifespan)

origins = os.environ.get("TECHFIX_CORS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor. Tente novamente mais tarde."},
    )


@app.exception_handler(sqlite3.IntegrityError)
async def integrity_handler(_: Request, exc: sqlite3.IntegrityError):
    return JSONResponse(
        status_code=409,
        content={"detail": "Operação não permitida: o registro está em uso por outros dados."},
    )


for r in (clientes.router, equipamentos.router, pecas.router, ordens.router, dashboard.router):
    app.include_router(r)


@app.get("/api/health", tags=["Infra"])
async def health():
    return {"status": "ok"}
