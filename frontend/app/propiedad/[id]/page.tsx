import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { buscarPropiedadPorId } from "@/lib/propiedades";
import { PropertyDetail } from "./PropertyDetail";

export async function generateMetadata({
  params,
}: {
  params: { id: string };
}): Promise<Metadata> {
  const listingId = Number(params.id);
  if (!Number.isInteger(listingId)) return { title: "Propiedad · REIP" };
  const property = await buscarPropiedadPorId(listingId);
  if (!property) return { title: "Propiedad · REIP" };
  return {
    title: `Propiedad #${property.listingId} · REIP`,
    description: `${property.corregimiento} · $${property.priceUsd.toLocaleString()} · REIP.`,
  };
}

export default async function PropiedadPage({ params }: { params: { id: string } }) {
  const listingId = Number(params.id);
  if (!Number.isInteger(listingId)) notFound();

  const property = await buscarPropiedadPorId(listingId);
  if (!property) notFound();

  return <PropertyDetail property={property} />;
}
