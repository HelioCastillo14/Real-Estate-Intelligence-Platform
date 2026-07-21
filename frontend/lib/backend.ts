/**
 * URL del backend FastAPI — server-only (usado en Route Handlers y Server
 * Components, nunca en el navegador). FastAPI no tiene CORS configurado
 * (backend/app/main.py no monta CORSMiddleware), así que ningún fetch de
 * cliente puede llamarlo directo entre orígenes distintos — de ahí el
 * proxy en app/api/*.
 *
 * BACKEND_API_URL debe apuntar a la URL de Railway en producción
 * (real-estate-intelligence-platform-production.up.railway.app, sin
 * decidir todavía si con o sin esquema/puerto — confirmar contra el
 * deploy real antes de fijarlo en Vercel). Sin configurar, cae a
 * localhost:8000 para desarrollo local con `uvicorn app.main:app`.
 */
export function getBackendUrl(): string {
  return process.env.BACKEND_API_URL ?? "http://localhost:8000";
}
