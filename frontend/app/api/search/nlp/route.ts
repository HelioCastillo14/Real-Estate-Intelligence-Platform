import { NextRequest, NextResponse } from "next/server";
import { getBackendUrl } from "@/lib/backend";

/**
 * Proxy same-origin hacia POST /search/nlp — mismo motivo que /api/search/filtros/route.ts:
 * FastAPI no tiene CORS configurado, un fetch directo del navegador a Railway fallaría
 * entre orígenes distintos.
 */
export async function POST(request: NextRequest) {
  const body = await request.json();

  const res = await fetch(`${getBackendUrl()}/search/nlp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
