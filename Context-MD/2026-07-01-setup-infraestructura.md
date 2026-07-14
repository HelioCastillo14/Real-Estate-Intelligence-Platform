# Decision Log — Setup de Infraestructura REIP
**Fecha:** 2026-07-01 | **Feature WBS:** 1.1 — Setup de entorno | **Estado: Completo (1.1.1 a 1.1.6, 12 SP)**
 
---
 
## Resumen de la sesión
 
Se completó el Feature 1.1 completo del WBS. Incluyó recreación del proyecto Supabase original (bloqueado por desconocimiento de la herramienta, no por error técnico), setup de FastAPI, Next.js + MapLibre, deploy en Railway y Vercel, y gestión de secrets.
 
---
 
## 1.1.1 — Supabase: PostGIS + pgvector
 
**Decisión:** se descartó el proyecto Supabase anterior (tier NANO, bloqueado) y se creó uno nuevo desde cero.
 
**Configuración del proyecto nuevo:**
- Tier: NANO (gratuito) — **pendiente de validar si soporta el volumen de 1.5.6 (PostGIS+pgvector combinado a full catálogo)**. Revisar al llegar a esa tarea.
- Región: Americas.
- "Automatically expose new tables": **desactivado** — decisión deliberada para no exponer `conjunto_referencia_m1` ni tablas de staging vía Data API por accidente.
- "Enable automatic RLS": desactivado — el backend usa service role key, no hay acceso directo del frontend a Supabase.
**Extensiones verificadas:**
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
```
- PostGIS: **3.3** (USE_GEOS=1 USE_PROJ=1 USE_STATS=1)
- pgvector: **0.8.0**
**Verificación desde local:** confirmada vía `psql` desde terminal Mac (no solo SQL Editor web), cumpliendo la condición de done tal como está escrita en el WBS.
 
**Incidente de conexión (documentado para no repetir):**
- La password original generada por Supabase contenía caracteres especiales (`@`, `$`, `&`) que rompían tanto la URL de conexión como el shell (zsh interpretaba `@` como separador falso).
- **Resolución:** se reseteó la password a una sin caracteres especiales vía Project Settings → Database → Reset database password. Recomendación para el equipo: al generar password de Supabase, evitar caracteres que requieran URL-encoding si se va a usar `psql` directo desde terminal.
**Herramienta usada para conectar:** `psql` (PostgreSQL 18.4 cliente, servidor 17.6), instalado vía Homebrew (`brew install libpq && brew link --force libpq`).
 
---
 
## 1.1.2 — Repo GitHub
 
Ya existía previo a esta sesión (`HelioCastillo14/Real-Estate-Intelligence-Platform`, ramas `main`/`dev`/`feature/*`). Sin cambios adicionales en esta sesión más allá de los commits normales de las tareas siguientes.
 
---
 
## 1.1.3 — FastAPI + estructura de carpetas
 
**Estructura implementada:**
```
backend/
├── app/
│   ├── __init__.py       (vacío)
│   ├── main.py           (endpoint /health)
│   ├── models/
│   ├── routers/
│   └── services/
├── requirements.txt
└── .env                  (no versionado)
```
 
**Incidente documentado:** en el primer intento, el contenido de `main.py` se pegó por error dentro de `app/__init__.py` (archivo equivocado). Corregido vaciando `__init__.py` y creando `main.py` con el contenido correcto vía heredoc.
 
**Verificación:** `GET /health` → `{"status":"ok"}`, confirmado con `curl` local. Condición de done cumplida.
 
---
 
## 1.1.4 — Next.js 14 + MapLibre GL JS
 
**Setup:**
- `create-next-app@14` con TypeScript, ESLint, Tailwind CSS, App Router, sin `src/` directory, sin alias de import custom.
- `maplibre-gl` v5.24.0 instalado vía npm.
- Página raíz (`app/page.tsx`) renderiza mapa centrado en Ciudad de Panamá (`[-79.5199, 8.9824]`, zoom 12), usando tiles gratuitos de OpenFreeMap (`https://tiles.openfreemap.org/styles/liberty`).
**Incidente menor:** TypeScript no reconocía el import de `maplibre-gl/dist/maplibre-gl.css` como módulo válido. Resuelto creando `app/css.d.ts` con `declare module "*.css";`.
 
**Verificación:** mapa renderiza correctamente; los "errores" visibles en consola del navegador eran atribuibles a extensiones del navegador (Trancy, NoteBoolLM) y a un warning cosmético interno de MapLibre — ninguno bloqueante ni atribuible al código propio. Condición de done cumplida.
 
---
 
## 1.1.5 — Deploy: Railway (backend) + Vercel (frontend)
 
### Railway (backend)
 
**Configuración final:**
- Root Directory: `backend`
- Start Command (manual, porque Railpack no detectó automáticamente el entrypoint en `app/main.py`):
  ```
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- Branch: `dev`
- Dominio público generado (puerto 8080): `real-estate-intelligence-platform-production.up.railway.app`
**Incidente documentado:** el primer intento de deploy falló porque Railway (Railpack) no pudo autodetectar un start command al no encontrar `main.py`/`app.py` en la raíz de `backend/` (está en `backend/app/main.py`). Se resolvió especificando el Start Command manualmente en Settings.
 
**Verificación:** `curl .../health` → `{"status":"ok"}` desde producción. Confirmado.
 
### Vercel (frontend)
 
**Configuración final:**
- Root Directory: `frontend`
- Framework: Next.js (autodetectado tras configurar el Root Directory)
- Deploy confirmado desde rama `dev` (Source: dev, commit visible en el deployment).
**Incidente documentado:** el primer y segundo intento de deploy fallaron con "No Next.js version detected" porque el campo "Root Directory" mostraba `frontend` como placeholder (texto gris), no como valor guardado. Se resolvió reingresando el valor en Settings → General → Root Directory y confirmando el guardado explícito con el botón "Save".
 
**Pendiente (no bloqueante):** la "Production Branch" de Vercel sigue configurada en `main`, no en `dev`. El deployment de prueba se hizo correctamente desde `dev` vía push directo, pero la URL de producción "oficial" (sin el sufijo `-git-dev-...`) seguirá apuntando a `main` hasta que se cambie explícitamente en Settings → Git → Production Branch. **Acción recomendada para la próxima sesión:** decidir si formalizar `dev` como production branch en Vercel, o mantener `main` como production y usar la URL de preview de `dev` para trabajo diario.
 
**Verificación:** logs de deploy muestran `GET 200` en la ruta raíz. Confirmado visualmente que el mapa renderiza en la URL de preview de `dev`.
 
---
 
## 1.1.6 — Gestión de secrets
 
**Estado:** completado parcialmente — estructura y documentación completas; **GEMINI_API_KEY pendiente de generar** (no bloqueante para esta fase, sí bloqueante antes de llegar a Épica 3/4 — Quality Scorer y NLP Orchestration).
 
**Variables documentadas y configuradas:**
 
| Variable | Local (`backend/.env`) | Railway (producción) |
|---|---|---|
| `SUPABASE_URL` | ✅ | ✅ |
| `SUPABASE_KEY` | ✅ (secret key, no anon/publishable) | ✅ |
| `DATABASE_URL` | ✅ (connection string modo Session) | ✅ |
| `GEMINI_API_KEY` | ⏳ vacío | ⏳ vacío |
 
**Nota sobre Supabase API keys:** Supabase migró de la nomenclatura `anon`/`service_role` a `publishable`/`secret`. Se usó la **secret key** (`sb_secret_...`) en el backend — equivalente funcional de `service_role`. La `publishable key` (`sb_publishable_...`) queda pendiente de uso si el frontend llega a hablar directo con Supabase (no es el caso actual — todo pasa por FastAPI).
 
**Verificación:** `.env` confirmado como no trackeado por Git (`git status` limpio tras crear el archivo). Variables documentadas en `README.md`. 4 variables visibles en Railway → Variables (más 8 agregadas automáticamente por Railway mismo).
 
**Acción pendiente para próxima sesión:** generar `GEMINI_API_KEY` en Google AI Studio y agregarla a `backend/.env` + Railway antes de comenzar cualquier tarea de Épica 2 (embeddings) o Épica 3/4 (Quality Scorer, NLP).
 
---
 
## Resumen de Feature 1.1 — Setup de entorno
 
| ID | Tarea | Estado |
|---|---|---|
| 1.1.1 | Supabase + PostGIS + pgvector | ✅ Completado |
| 1.1.2 | Repo GitHub | ✅ Completado (previo) |
| 1.1.3 | FastAPI + estructura de carpetas | ✅ Completado |
| 1.1.4 | Next.js 14 + MapLibre GL JS | ✅ Completado |
| 1.1.5 | Railway + Vercel deploy | ✅ Completado |
| 1.1.6 | Gestión de secrets | ⚠️ Completado excepto Gemini API Key |
 
**Total: 12 SP cerrados de 12 SP del Feature 1.1** (con una deuda menor pendiente: Gemini API Key).
 
---
 
## Aprendizajes de la sesión (para no repetir)
 
1. **Passwords con caracteres especiales rompen conexiones psql/URL** — generar sin `@`, `$`, `&` si se va a usar terminal directo, o URL-encodearlos correctamente desde el inicio.
2. **Los campos de configuración con placeholder gris ≠ valor guardado** — confirmar visualmente que el texto quedó en color sólido antes de asumir que se guardó (pasó en Root Directory de Vercel, dos veces).
3. **Railway/Vercel no siempre autodetectan monorepos** — si el repo tiene `backend/` y `frontend/` como hermanos, el Root Directory debe configurarse explícitamente en ambos servicios antes del primer deploy exitoso.
4. **Verificar en qué rama/carpeta está el terminal antes de correr comandos** — varios pasos se enredaron por confundir `pipeline/` con `backend/`, o `dev` con `main`, en el prompt.
5. **"Bloqueado" en el WBS debe indicar causa, no solo estado** — el bloqueo de 1.1.1 no era técnico, era desconocimiento de la herramienta. Distinguir esto en el decision log ahorra tiempo de diagnóstico en la siguiente sesión.
---
 
## Próxima sesión — orden sugerido
 
1. Generar `GEMINI_API_KEY` (Google AI Studio) — 2 minutos, cierra a Épica 3/4.
2. Decidir Production Branch de Vercel (`dev` vs `main`) — 1 decisión de equipo, no técnica.
3. Retomar Feature 1.2 — Pipeline de scraping: verificar slugs de los 3-4 corregimientos faltantes (Pedregal, El Cangrejo, Marbella, Costa del Este) según `context_log_scraping.md`.