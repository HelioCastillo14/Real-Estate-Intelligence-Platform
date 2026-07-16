/**
 * Redacta PII de terceros incrustada en texto libre (`propiedades.descripcion`) — solo
 * en la capa de presentación, igual criterio que `sanitizeText()` (fix de encoding
 * Windows-1252): la columna en la DB NO se toca, sigue cruda para M2/Quality Scorer.
 *
 * Hallazgo (Feature 7.2.2, auditoría PII 2026-07-16, ver
 * Context-MD/Feature_7_2_2_Auditoria_PII_Cierre.md): 7/1,168 filas con `descripcion`
 * contienen un teléfono panameño real incrustado en el texto (formatos: "6XXX-XXXX",
 * "+507 6XXX-XXXX", "+ 507 6XXX-XXXX" con espacio tras el "+", "+5076XXXXXXX" sin
 * separadores), 1 fila con email, 2 con nombre propio de agente junto al contacto. El
 * dato ya es público en inmopanama.com, pero nuestro Detalle lo renderizaba tal cual sin
 * que nadie lo supiera — este helper cierra esa brecha sin alterar el insumo real del
 * Quality Scorer.
 *
 * Teléfono: móvil panameño real, siempre empieza en '6' y tiene 8 dígitos —
 * `(\+?\s?507[\s.-]?)?` cubre el prefijo internacional opcional, incluyendo la variante
 * con espacio entre "+" y "507" vista en 136835 ("+ 507 6205-7577"). Verificado contra
 * las 1,168 filas reales de `descripcion`: 11 coincidencias en 7 filas, cero falsos
 * positivos (no confunde `area_m2`/precio con teléfono — esas cifras no viven en el
 * texto de `descripcion` con este patrón de 8 dígitos iniciando en 6).
 */
const TELEFONO_PANAMA_RE = /(\+?\s?507[\s.-]?)?6\d{3}[\s.-]?\d{4}\b/g;
const EMAIL_RE = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;

const MARCADOR = "[contacto de terceros removido]";

export function sanitizePii<T extends string | null>(texto: T): T {
  if (texto === null) return texto;
  return texto.replace(TELEFONO_PANAMA_RE, MARCADOR).replace(EMAIL_RE, MARCADOR) as T;
}
