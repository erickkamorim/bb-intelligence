"""API BB Intelligence.  Rodar: uvicorn app.main:app --reload  (na pasta backend)"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.routes import API_VERSION, router

app = FastAPI(title="BB Intelligence API", version=API_VERSION,
              description="Dados públicos sobre o Banco do Brasil com fonte, período e unidade. "
                          "Projeto independente, não oficial.")

origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=["*"])


@app.exception_handler(StarletteHTTPException)
async def http_error(_req: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(RequestValidationError)
async def validation_error(_req: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "invalid_request",
                                                            "message": "Parâmetros inválidos",
                                                            "details": [{"loc": list(e.get("loc", [])), "msg": e.get("msg")}
                                                                        for e in exc.errors()]}})


app.include_router(router)
