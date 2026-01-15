from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 🔥 DEV-ONLY CORS: allow everything local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 👈 THIS is the key
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from assistant.router import router as assistant_router
app.include_router(assistant_router)
