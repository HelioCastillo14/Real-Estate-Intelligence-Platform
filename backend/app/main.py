from contextlib import asynccontextmanager

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI

load_dotenv(find_dotenv())

from app.db.pool import cerrar_pool, inicializar_pool
from app.routers import match, search, valuation


@asynccontextmanager
async def lifespan(app: FastAPI):
    inicializar_pool()
    yield
    cerrar_pool()


app = FastAPI(lifespan=lifespan)
app.include_router(match.router)
app.include_router(valuation.router)
app.include_router(search.router)

@app.get("/health")
def health():
    return {"status": "ok"}
