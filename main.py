from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from database import engine
from routers import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:

        yield
    finally:

        await engine.dispose()

app = FastAPI(
    title="Langufy API",
    version="1.0",
    openapi_url="/api/openapi.json",
    default_response_class=JSONResponse,
    lifespan=lifespan,
    routes=[
        Mount("/static/", StaticFiles(directory="static")),
        Mount("/media/", StaticFiles(directory="media")),
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(
    api_router,
    prefix="/api"
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
