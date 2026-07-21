import { NextRequest, NextResponse } from "next/server";
import { getBackendUrl } from "@/lib/backend";

/**
 * Proxy same-origin hacia POST /search/filtros del backend real. Necesario
 * porque FastAPI no tiene CORS configurado — un fetch directo del navegador
 * a Railway fallaría entre orígenes distintos. El navegador solo habla con
 * este Route Handler (mismo origen que el resto del frontend); este handler
 * corre en el servidor de Next.js y reenvía la petición sin restricción de
 * CORS (server-to-server).
 */
export async function POST(request: NextRequest) {
  const body = await request.json();

  const res = await fetch(`${getBackendUrl()}/search/filtros`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
