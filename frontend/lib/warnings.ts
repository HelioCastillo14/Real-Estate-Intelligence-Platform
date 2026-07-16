const warned = new Set<string>();

export function warnOnce(key: string, message: string) {
  if (warned.has(key)) return;
  warned.add(key);
  console.warn(`[REIP] ${message}`);
}
