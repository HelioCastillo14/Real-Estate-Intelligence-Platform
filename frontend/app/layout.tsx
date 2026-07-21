import type { Metadata } from "next";
import { Fraunces, Inter } from "next/font/google";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
});
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "REIP · Inteligencia de mercado inmobiliario en Panamá",
  description:
    "Busca propiedades en Ciudad de Panamá con lenguaje natural. Compatibilidad, semáforo de precio y análisis del anuncio sobre un catálogo real de propiedades.",
  openGraph: {
    title: "REIP · Real Estate Intelligence Platform",
    description:
      "Plataforma de inteligencia de mercado inmobiliario para Ciudad de Panamá. Búsqueda en lenguaje natural sobre catálogo real.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className={`${fraunces.variable} ${inter.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
