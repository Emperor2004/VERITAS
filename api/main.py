"""
VERITAS FastAPI Application Server.

Provides RESTful endpoints for model auditing, real-time schema validation,
human sign-off workflows, and plain-English governance reporting.
"""
from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver

from api.routes_meta import router as meta_router
from api.routes_runs import router as runs_router, set_audit_graph
from api.settings import ALLOWED_ORIGINS, CHECKPOINT_DB_PATH, DB_PATH
from api.store import init_db
from src.agentic.graph import build_audit_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite store schema
    init_db(DB_PATH)

    # 2. Build single graph with durable SQLite checkpointer
    CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_conn = sqlite3.connect(str(CHECKPOINT_DB_PATH), check_same_thread=False)
    checkpointer = SqliteSaver(checkpoint_conn)
    graph = build_audit_graph(checkpointer)
    set_audit_graph(graph)

    yield

    # Teardown
    checkpoint_conn.close()


app = FastAPI(
    title="VERITAS AI Audit API",
    description="Verifiable Evidence & Risk Identification Toolkit for AI Systems (NIST AI RMF)",
    version="0.2.0",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS) for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta_router)
app.include_router(runs_router)
