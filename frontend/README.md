# Frontend — Real Estate Intelligence Platform

Next.js 14 (App Router) + MapLibre GL JS. Consume el backend FastAPI (`../backend`)
a través de Route Handlers en `app/api/*`, que actúan como proxy server-side — el
backend no tiene CORS configurado, así que ningún fetch de cliente puede llamarlo
directo entre orígenes distintos.

## Desarrollo local

```bash
npm install
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000). Requiere el backend corriendo
en paralelo (`uvicorn app.main:app`, ver `../backend`).

## Variables de entorno

| Variable | Uso | Default |
|---|---|---|
| `BACKEND_API_URL` | URL del backend FastAPI, usada server-side en `app/api/*` (`lib/backend.ts`) | `http://localhost:8000` |

En producción (Vercel), `BACKEND_API_URL` debe apuntar al deploy de Railway.

## Build

```bash
npm run build
```

Deploy en Vercel.
