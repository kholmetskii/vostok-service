from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.router import router as warehouse_config_router

app = FastAPI(title="Vostok Service Backend")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(warehouse_config_router)

