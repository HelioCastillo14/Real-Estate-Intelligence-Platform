export function PendingBadge({ label = "Dato pendiente de verificación" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-border bg-muted px-2 py-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
      <span className="w-1.5 h-1.5 rounded-full border border-muted-foreground/60" />
      {label}
    </span>
  );
}
