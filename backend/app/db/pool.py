"""Pool de conexiones a Supabase (Feature 2.2.5).

Resuelve el hallazgo dejado pendiente en Feature 2.2.1: `buscar_propiedades_ann()` abría una
conexión nueva (`psycopg2.connect`) en cada llamada, ~1s de overhead de TLS/auth contra el
Supabase remoto (`us-east-1`) por request — medido en 2.1.4/2.2.1. `psycopg2.pool.SimpleConnectionPool`
(no `asyncpg`): el resto del backend (`embeddings.py`, `busqueda_ann.py`, todos los scripts de
`pipeline/scripts/`) ya usa `psycopg2` de forma síncrona — introducir `asyncpg` aquí exigiría
mezclar dos drivers Postgres distintos en el mismo backend sin ninguna necesidad real (FastAPI
sync endpoints ya corren en threadpool, no bloquean el event loop de forma problemática a este
volumen). `SimpleConnectionPool` (no `ThreadedConnectionPool`): FastAPI en modo sync ejecuta
cada request en un hilo del threadpool de Starlette, que ya se encarga de la concurrencia — no
se necesita el locking adicional de `ThreadedConnectionPool` para este caso de uso.

El pool se inicializa UNA VEZ en el `lifespan` de `main.py` (startup), no por request — ver
`inicializar_pool()`/`cerrar_pool()`. Un router pide una conexión con `pool.getconn()` y la
devuelve con `pool.putconn(conn)` (nunca `conn.close()` directo, eso la sacaría del pool).
"""

import os

from psycopg2 import pool as psycopg2_pool

_pool: psycopg2_pool.SimpleConnectionPool | None = None


def inicializar_pool(minconn: int = 1, maxconn: int = 10) -> psycopg2_pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2_pool.SimpleConnectionPool(minconn, maxconn, dsn=os.environ["DATABASE_URL"])
    return _pool


def obtener_pool() -> psycopg2_pool.SimpleConnectionPool:
    if _pool is None:
        raise RuntimeError(
            "Pool de conexiones no inicializado — falta correr inicializar_pool() en el "
            "lifespan de la app antes de atender requests."
        )
    return _pool


def cerrar_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
