import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app import WEB_HOST, WEB_PORT
from app.api import routers


app = FastAPI(
    title="9oormthon Keyboard Backend",
    description="API Server",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routers.router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(
        "app.__main__:app",
        host=WEB_HOST,
        port=WEB_PORT,
        reload=True,
        workers=4
    )