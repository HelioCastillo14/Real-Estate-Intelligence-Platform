import { Suspense } from "react";
import { Resultados } from "./Resultados";

export default function ResultadosPage() {
  return (
    <Suspense fallback={null}>
      <Resultados />
    </Suspense>
  );
}
