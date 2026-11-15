import { brl, number, sourceLine, sourceShort } from "@/lib/format";
import type { CreditSegments } from "@/lib/types";
import { C } from "@/lib/theme";

// Paleta categórica validada (CVD e normal) para 3 séries; "Outros" é neutro.
const COLORS: Record<string, string> = { carteira_pf: C.pf, carteira_pj: C.pj, carteira_agro: C.agro, outros: C.other };

export function DonutChart({ data }: { data: CreditSegments }) {
  const segs = (data.segments ?? []).filter((s) => s.status === "ok" && s.value !== undefined);
  const total = data.total ?? 0;
  const R = 70, r = 46, C = 90;
  let angle = -Math.PI / 2;
  const gap = 0.02; // folga entre fatias (separação pela cor de fundo)

  const arcs = segs.map((s) => {
    const frac = s.value! / total;
    const a0 = angle + gap / 2, a1 = angle + frac * 2 * Math.PI - gap / 2;
    angle += frac * 2 * Math.PI;
    const large = a1 - a0 > Math.PI ? 1 : 0;
    const p = (rad: number, a: number) => `${C + rad * Math.cos(a)},${C + rad * Math.sin(a)}`;
    const d = `M${p(R, a0)} A${R},${R} 0 ${large} 1 ${p(R, a1)} L${p(r, a1)} A${r},${r} 0 ${large} 0 ${p(r, a0)} Z`;
    return { s, d };
  });

  return (
    <div className="donut">
      <svg viewBox="0 0 180 180" width="180" height="180" role="img"
           aria-label={`Carteira de crédito expandida: ${segs.map((s) => `${s.label} ${number(s.share_pct ?? 0, 1)}%`).join(", ")}`}>
        {arcs.map(({ s, d }) => (
          <path key={s.code} d={d} fill={COLORS[s.code] ?? C.other}>
            <title>{`${s.label}: ${brl(s.value!)} (${number(s.share_pct ?? 0, 1)}%)`}</title>
          </path>
        ))}
        <text x={C} y={C - 2} textAnchor="middle" className="donut-total">{brl(total)}</text>
        <text x={C} y={C + 16} textAnchor="middle" className="donut-unit">expandida</text>
      </svg>
      <ul className="legend">
        {segs.map((s) => (
          <li key={s.code}>
            <span className="swatch" style={{ background: COLORS[s.code] ?? C.other }} aria-hidden="true" />
            <span className="legend-label">{s.label}{s.derivation ? "*" : ""}</span>
            <span className="legend-value">{number(s.share_pct ?? 0, 1)}%</span>
            <span className="legend-sub">{brl(s.value!)}</span>
          </li>
        ))}
      </ul>
      {data.total_source && (
        <p className="chart-note">
          <span title={sourceLine(data.total_source)}>Fonte: {sourceShort(data.total_source)}</span>. *Outros = carteira expandida menos PF, PJ e Agro (inclui carteira externa).
        </p>
      )}
    </div>
  );
}
