/** Escala com ~4 intervalos "redondos". Aceita mínimo negativo. */
export function niceScale(maxV: number, minV = 0): { min: number; max: number; ticks: number[] } {
  const lo = Math.min(minV, 0);
  const span = Math.max(maxV - lo, 1e-9);
  const raw = span / 4;
  const p = 10 ** Math.floor(Math.log10(raw));
  const n = raw / p;
  const step = (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p;
  const min = step * Math.floor(lo / step);
  const max = step * Math.ceil(maxV / step);
  const ticks: number[] = [];
  for (let t = min; t <= max + step / 2; t += step) ticks.push(Math.round(t * 1e9) / 1e9);
  return { min, max, ticks };
}

/** Lista contínua de fins de trimestre entre duas datas (inclusive). */
export function quarterEnds(first: string, last: string): string[] {
  const out: string[] = [];
  let [y, m] = first.split("-").map(Number);
  m = Math.ceil(m / 3) * 3;
  const [ly, lm] = last.split("-").map(Number);
  while (y < ly || (y === ly && m <= lm)) {
    out.push(new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10));
    m += 3;
    if (m > 12) { m -= 12; y += 1; }
  }
  return out;
}

export function downloadCsv(filename: string, rows: (string | number)[][]) {
  const body = rows.map((r) => r.map((x) => `"${String(x).replace(/"/g, '""')}"`).join(";")).join("\n");
  const blob = new Blob(["﻿" + body], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
