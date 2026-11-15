/** Cores dos gráficos no tema escuro (validadas para daltonismo contra a superfície #121826). */
export const C = {
  surface: "#121826",
  grid: "#263042",
  axis: "#3A465C",
  ink: "#F2F5FA",
  ink2: "#B5BFCE",
  muted: "#8B97A8",
  series: "#3F7FE0",
  highlight: "#FFDF00",
  pf: "#3F7FE0",
  pj: "#B8860B",
  agro: "#1F9E8E",
  other: "#5A6578",
  // Regra do projeto: resultado positivo = verde, negativo = vermelho (sempre com sinal no rótulo)
  pos: "#2FB67C",
  neg: "#E5484D",
  up: "#2FB67C",
  down: "#E5484D",
  total: "#8B97A8",
};

/** Cor pelo sinal do resultado. `higherIsBetter=false` inverte (ex.: inadimplência, custo). */
export function toneColor(v: number, higherIsBetter = true): string {
  if (v === 0) return C.muted;
  return (v > 0) === higherIsBetter ? C.pos : C.neg;
}
