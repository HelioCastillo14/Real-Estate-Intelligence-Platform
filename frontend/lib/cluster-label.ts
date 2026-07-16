import { warnOnce } from "./warnings";

/**
 * Mapeo cluster_id -> etiqueta legible. Fuente de verdad:
 * Context-MD/Feature_3_2_4_Etiquetado_Clusters_KMeans_Acta_Excepcion.md §3.
 * valuacion_segmento_kmeans.cluster_id solo guarda el entero — el texto no vive en DB.
 */
const CLUSTER_LABELS: Record<0 | 1, string> = {
  0: "Compacto / económico",
  1: "Grande / premium",
};

export function resolveClusterLabel(clusterId: number | null): string {
  if (clusterId === null) {
    return "Sin segmentación disponible";
  }
  if (clusterId !== 0 && clusterId !== 1) {
    warnOnce(
      "cluster-label-unexpected",
      `resolveClusterLabel recibió cluster_id=${clusterId}, fuera del mapeo conocido (0/1). Revisar si el KMeans fue recalibrado con otro k.`,
    );
    return `Segmento desconocido (cluster_id=${clusterId})`;
  }
  return CLUSTER_LABELS[clusterId];
}
