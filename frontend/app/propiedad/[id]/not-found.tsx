import Link from "next/link";

export default function PropiedadNotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="font-display text-4xl text-ink">Propiedad no encontrada</div>
        <Link href="/resultados" className="mt-4 inline-block text-primary underline">
          Volver a resultados
        </Link>
      </div>
    </div>
  );
}
