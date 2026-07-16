import { NextRequest, NextResponse } from "next/server";
import { getBackendUrl } from "@/lib/backend";

/**
 * Proxy same-origin hacia GET /zone-health/{corregimiento} — mismo motivo que el resto
 * de /api/*: FastAPI no tiene CORS configurado. `corregimiento` llega ya URL-encoded
 * desde el cliente (nombres con espacio: "El Cangrejo", "Costa del Este") — se reenvía
 * tal cual, sin decodificar/re-codificar, para no introducir un mismatch de encoding.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { corregimiento: string } },
) {
  const res = await fetch(`${getBackendUrl()}/zone-health/${params.corregimiento}`, {
    cache: "no-store",
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
