-- Feature Épica 5 (geom sintético de propiedades) — agrega el flag que distingue un
-- punto generado dentro del polígono real de la propiedad (corregimiento oficial) de
-- uno generado dentro del polígono del corregimiento padre (zona no oficial heredada:
-- El Cangrejo, Marbella, Obarrio → Bella Vista). Sin esta columna, el frontend no puede
-- diferenciar ambos casos y mostraría una precisión de ubicación que no existe.
--
-- default false: todas las filas ya existentes (1,177) no tienen geom todavía (ver
-- CLAUDE.md, "Estado del pipeline de datos") — el default es una convención segura para
-- cuando se pueble geom fila por fila en cargar_geom_sintetico_propiedades.py, no una
-- afirmación de que esas filas ya tienen ubicación exacta.

alter table propiedades
    add column ubicacion_aproximada boolean not null default false;

comment on column propiedades.ubicacion_aproximada is
    'true cuando el punto de geom se generó dentro del polígono del corregimiento padre '
    '(herencia visual), no del polígono real de la propiedad — ver Épica 5, resolución '
    'de zonas no oficiales sin geometría propia.';
