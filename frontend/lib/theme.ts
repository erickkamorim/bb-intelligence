/** Cores dos gráficos no tema claro (validadas para daltonismo contra a superfície #FFFFFF). */
export const C = {
  surface: "#FFFFFF",
  grid: "#E6EAF5",
  axis: "#A9B2CC",
  ink: "#10162F",
  ink2: "#4A5470",
  muted: "#5E6884",
  series: "#2B3FD6",
  highlight: "#C99A00",
  pf: "#2B3FD6",
  pj: "#B8860B",
  agro: "#1F9E8E",
  other: "#5A6578",
  // Regra do projeto: resultado positivo = verde, negativo = vermelho (sempre com sinal no rótulo)
  pos: "#0F8A4F",
  neg: "#D23B2E",
  up: "#0F8A4F",
  down: "#D23B2E",
  total: "#2B3FD6",
};

/** Cor pelo sinal do resultado. `higherIsBetter=false` inverte (ex.: inadimplência, custo). */
export function toneColor(v: number, higherIsBetter = true): string {
  if (v === 0) return C.muted;
  return (v > 0) === higherIsBetter ? C.pos : C.neg;
}
