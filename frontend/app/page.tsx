"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/Header";
import { PendingBadge } from "@/components/PendingBadge";
import { warnOnce } from "@/lib/warnings";

const suggestions = [
  "Apartamento de 3 recámaras en Punta Pacífica bajo 400k",
  "Casa familiar cerca de colegios en Clayton con jardín",
  "Estudio caminable en El Cangrejo cerca del metro",
  "Alquiler amoblado con vista al mar por menos de 3,000",
];

const TEAM = [
  { name: "Besto", role: "PM / Technical Lead", roleConfirmed: true },
  { name: "Copri", role: null, roleConfirmed: false },
  { name: "Montoya", role: null, roleConfirmed: false },
  { name: "Rives", role: null, roleConfirmed: false },
] as const;

export default function Home() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const canSubmit = query.trim().length > 3;

  const submit = () => {
    if (!canSubmit) return;
    setLoading(true);
    setTimeout(() => {
      router.push(`/resultados?q=${encodeURIComponent(query.trim())}`);
    }, 900);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      <main className="flex-1">
        {/* HERO */}
        <section className="relative overflow-hidden">
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute -top-40 -right-40 w-[600px] h-[600px] rounded-full bg-primary/10 blur-3xl" />
            <div className="absolute -bottom-32 -left-20 w-[500px] h-[500px] rounded-full bg-accent/40 blur-3xl" />
          </div>

          <div className="relative max-w-[1200px] mx-auto px-8 pt-20 pb-24">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-muted-foreground mb-8">
              <span className="w-8 h-px bg-primary" />
              Real Estate Intelligence Platform · Ciudad de Panamá
            </div>

            <h1 className="font-display text-[64px] leading-[0.98] tracking-tight text-ink font-medium max-w-4xl">
              Describe la casa que buscas.
              <br />
              <span className="italic text-primary">Nosotros interpretamos</span> el mercado.
            </h1>

            <p className="mt-6 max-w-2xl text-lg text-muted-foreground leading-relaxed">
              Busca en lenguaje natural sobre un catálogo real de propiedades en Ciudad de Panamá.
              Compatibilidad, semáforo de precio y análisis de confiabilidad — todo sin registro.
            </p>

            {/* Search */}
            <div className="mt-12 max-w-3xl">
              <div
                className={`relative bg-card border-2 rounded-2xl transition-all ${
                  query ? "border-primary shadow-editorial" : "border-border shadow-soft"
                }`}
              >
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      submit();
                    }
                  }}
                  placeholder="Ej. Apartamento de 3 recámaras con vista al mar en Punta Pacífica, bajo $420,000..."
                  rows={2}
                  disabled={loading}
                  className="w-full resize-none bg-transparent px-6 pt-5 pb-16 text-lg text-ink placeholder:text-muted-foreground/70 focus:outline-none font-display"
                />
                <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground pl-3">
                    <kbd className="px-1.5 py-0.5 rounded border border-border bg-muted text-[10px] font-mono">
                      ⏎
                    </kbd>
                    para buscar
                  </div>
                  <button
                    onClick={submit}
                    disabled={!canSubmit || loading}
                    className="inline-flex items-center gap-2 rounded-xl bg-primary text-primary-foreground px-5 py-3 text-sm font-medium transition-all hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <>
                        <span className="w-3 h-3 rounded-full border-2 border-current border-t-transparent animate-spin" />
                        Interpretando tu búsqueda...
                      </>
                    ) : (
                      <>
                        Buscar propiedades
                        <span aria-hidden>→</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              <div className="mt-6 flex flex-wrap gap-2">
                <span className="text-xs uppercase tracking-wider text-muted-foreground mr-1 self-center">
                  Prueba:
                </span>
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => setQuery(s)}
                    className="text-xs px-3 py-1.5 rounded-full bg-card border border-border text-muted-foreground hover:text-ink hover:border-primary/40 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* STATS */}
        <section id="metodologia" className="border-y border-border bg-canvas">
          <div className="max-w-[1200px] mx-auto px-8 py-16 grid grid-cols-3 gap-8">
            <Stat
              value="1,177"
              suffix="propiedades"
              label="en catálogo activo"
              pendingKey="stat-propiedades"
              pendingMessage="Contador de propiedades del Home usa la cifra operativa de CLAUDE.md (Feature 6.2.1), no un endpoint de conteo en vivo."
            />
            <Stat
              value="9"
              suffix="corregimientos"
              label="con Zone Health Index"
              pendingKey="stat-corregimientos"
              pendingMessage="Contador de corregimientos del Home no está conectado a un endpoint real — valor tomado de la tabla corregimientos documentada en CLAUDE.md."
            />
            <Stat value="M1·M2·M3" suffix="módulos" label="Matching · Valuation · NLP" />
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section id="zonas" className="max-w-[1200px] mx-auto px-8 py-24">
          <div className="grid grid-cols-12 gap-8">
            <div className="col-span-5">
              <div className="text-[11px] uppercase tracking-[0.2em] text-primary mb-6">
                Cómo funciona
              </div>
              <h2 className="font-display text-5xl leading-tight text-ink font-medium">
                Tres módulos, una misma lectura del mercado.
              </h2>
              <p className="mt-6 text-muted-foreground leading-relaxed">
                Combinamos preference matching, un motor de valuación entrenado con comparables
                reales y una capa de orquestación NLP para interpretar consultas ambiguas antes
                de mostrar resultados.
              </p>
              <Link
                href="/resultados"
                className="mt-8 inline-flex items-center gap-2 text-sm font-medium text-primary hover:gap-3 transition-all"
              >
                Ver catálogo completo <span>→</span>
              </Link>
            </div>

            <div className="col-span-7 space-y-4">
              <ModuleRow
                num="M1"
                title="Preference Matching"
                body="Cada propiedad recibe un score de compatibilidad basado en tu descripción — no en filtros rígidos."
              />
              <ModuleRow
                num="M2"
                title="Property Valuation Engine"
                body="Semáforo de precio contra comparables. Sabrás si un anuncio está bajo, en el rango, o sobre mercado."
              />
              <ModuleRow
                num="M3"
                title="NLP Orchestration Layer"
                body="Interpreta tu búsqueda y — cuando algo es ambiguo — pide precisión antes de disparar resultados."
              />
            </div>
          </div>
        </section>

        {/* TEAM */}
        <section id="equipo" className="border-t border-border bg-canvas">
          <div className="max-w-[1200px] mx-auto px-8 py-24">
            <div className="text-[11px] uppercase tracking-[0.2em] text-primary mb-6">
              El equipo
            </div>
            <h2 className="font-display text-4xl leading-tight text-ink font-medium mb-10">
              Tesis capstone, Universidad Tecnológica de Panamá
            </h2>
            <div className="grid grid-cols-4 gap-4">
              {TEAM.map((member) => (
                <div key={member.name} className="rounded-2xl border border-border bg-card p-6">
                  <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center font-display text-lg text-ink font-medium">
                    {member.name[0]}
                  </div>
                  <div className="mt-4 font-display text-lg text-ink font-medium">{member.name}</div>
                  <div className="mt-2">
                    {member.roleConfirmed ? (
                      <span className="text-sm text-muted-foreground">{member.role}</span>
                    ) : (
                      <PendingBadge label="Rol pendiente" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border bg-canvas">
        <div className="max-w-[1200px] mx-auto px-8 py-8 flex items-center justify-between text-xs text-muted-foreground">
          <div>REIP · Tesis capstone 0698 · Universidad Tecnológica de Panamá</div>
          <div className="flex items-center gap-4">
            <span>Datos: inmopanama.com</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Stat({
  value,
  suffix,
  label,
  pendingKey,
  pendingMessage,
}: {
  value: string;
  suffix: string;
  label: string;
  pendingKey?: string;
  pendingMessage?: string;
}) {
  useEffect(() => {
    if (pendingKey && pendingMessage) warnOnce(pendingKey, pendingMessage);
  }, [pendingKey, pendingMessage]);

  return (
    <div className="border-l-2 border-primary/60 pl-5">
      <div className="flex items-baseline gap-2">
        <span className="font-display text-5xl text-ink font-semibold tabular-nums leading-none">
          {value}
        </span>
        <span className="text-sm text-muted-foreground">{suffix}</span>
      </div>
      <div className="mt-3 text-sm text-ink font-medium">{label}</div>
      {pendingKey ? (
        <div className="mt-2">
          <PendingBadge />
        </div>
      ) : null}
    </div>
  );
}

function ModuleRow({ num, title, body }: { num: string; title: string; body: string }) {
  return (
    <div className="group flex gap-6 p-6 rounded-xl bg-card border border-border hover:border-primary/40 transition-colors">
      <div className="shrink-0 w-14 h-14 rounded-lg bg-primary/10 flex items-center justify-center">
        <span className="font-display text-lg text-primary font-semibold">{num}</span>
      </div>
      <div>
        <h3 className="font-display text-xl text-ink font-medium">{title}</h3>
        <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{body}</p>
      </div>
    </div>
  );
}
