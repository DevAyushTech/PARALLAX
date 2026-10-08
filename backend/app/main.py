from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .agents import AgentOutputError
from .api import router
from .config import get_settings
from .db import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        init_db()
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Database initialization failed. Check PARALLAX_DATABASE_URL and ensure "
            "the database directory exists and is writable. Do not delete existing data."
        ) from exc
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(router)


@app.exception_handler(AgentOutputError)
async def invalid_agent_output(_: Request, __: AgentOutputError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "detail": "Specialist output could not be validated. The previous decision "
            "is unchanged. Check the evidence/provider output before retrying analysis."
        },
    )
