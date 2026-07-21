/**
 * Corrige bytes C1 (0x80-0x9F) de Windows-1252 mal decodificados a UTF-8 que
 * quedaron crudos en `propiedades.title`/`propiedades.descripcion` — 256 filas
 * afectadas, verificado contra la DB real. Solo un parche de display: la DB
 * sigue con el byte crudo. Ver Context-MD/Hallazgo_Encoding_Titulos_Scraper.md.
 */
const REEMPLAZOS_WINDOWS_1252: Record<string, string> = {
  "\x91": "'",
  "\x92": "'",
  "\x93": '"',
  "\x94": '"',
  "\x96": "–",
  "\x97": "—",
};

export function sanitizeText<T extends string | null>(texto: T): T {
  if (texto === null) return texto;
  return texto.replace(/[\x91-\x94\x96\x97]/g, (c) => REEMPLAZOS_WINDOWS_1252[c] ?? c) as T;
}
