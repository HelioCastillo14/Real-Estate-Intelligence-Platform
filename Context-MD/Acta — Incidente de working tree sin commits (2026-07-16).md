## Hallazgo: trabajo acumulado sin commitear (2026-07-16)

**Contexto:** durante la migración de Épica 5 (frontend), al intentar recuperar dos 
componentes borrados en el working tree (MapView.tsx, Signals.tsx), se confirmó vía 
`git log` que no existía ningún commit de esos archivos en ningún punto del historial.

**Alcance real, confirmado con `git status --short` completo:** no fue un incidente 
aislado de 2 archivos. El working tree tenía sin commitear, desde el commit `8923fc9`:
- Backend completo de M1/M2/M3 (routers `search.py`, `valuation.py`, 7 services de 
  KNN/NLP — 1,409 líneas nuevas)
- 6 migraciones de schema Supabase modificadas + 1 nueva + 5 scripts de carga a 
  producción (pipeline/)
- Migración completa de frontend Lovable→Next.js 14 (rutas, componentes, lib/)
- 6 Actas de cierre en Context-MD/, CLAUDE.md, .gitignore

**Consecuencia real:** MapView.tsx y Signals.tsx (con las correcciones de tiles 
OpenFreeMap y paleta SRS-035 ya aplicadas) se perdieron de forma irrecuperable vía git 
al borrarse durante la migración — nunca tuvieron un commit. Se reconstruyeron desde el 
texto de la conversación de la sesión y quedaron documentados en 
`frontend/docs/pendiente-mapview-signals.md` (commit `bdddc13`), pero de no haber 
existido ese registro en el chat, habrían sido trabajo perdido sin posibilidad de 
recuperación.

**Corrección aplicada esta sesión:** los 4 grupos de cambios se separaron en commits 
lógicos independientes (backend, migraciones+pipeline, frontend, docs) en vez de un 
commit único, para permitir revert/bisect selectivo si algo falla:
- `f647a04` — backend M1/M2/M3
- `ffbcb0e` — migraciones + pipeline
- `bdddc13` — frontend (incluye el archivo de recuperación de MapView/Signals)
- `11194df` — docs

**Decisión de proceso, pendiente de ratificar con el equipo:** ver regla propuesta en 
CLAUDE.md, sección de disciplina de commits.