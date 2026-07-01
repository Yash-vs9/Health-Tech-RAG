from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.logging_config import setup_logging, get_logger
from backend.routes import auth_routes, chat_routes, document_routes, message_routes

setup_logging()
logger = get_logger("backend.main")

app = FastAPI(
    title="Auth & Session Service",
    description="User authentication, chat session management, and document/message persistence for the RAG chatbot",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(document_routes.router)
app.include_router(message_routes.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth-session-service"}
