import { number } from "@/lib/format";
import { C, toneColor } from "@/lib/theme";

export interface PeerBank {
  cod_inst: string; name: string; is_bb: boolean;
  ativo_total: number | null; carteira_credito: number | null; carteira_yoy_pct: number | null;
  patrimonio_liquido: number | null; lucro_trimestre: number | null; lucro_derivacao: string | null;
  roe_anualizado: number | null; basileia: number | null;
  roe_hist: { period_end: string; value: number }[];
  lucro_hist: { period_end: string; value: number }[];
}

type Key = "roe_anualizado" | "lucro_trimestre" | "carteira_credito" | "carteira_yoy_pct" | "basileia" | "ativo_total";
type Kind = "pct" | "pct_signed" | "brl_bi" | "brl_tri";

const fmt = (v: number, kind: Kind) =>
  kind === "pct" ? `${number(v, 1)}%`
  : kind === "pct_signed" ? `${v > 0 ? "+" : ""}${number(v, 1)}%`
  : kind === "brl_tri" ? `R$ ${number(v / 1e12, 2)} tri`
  : `R$ ${number(v / 1e9, 2)} bi`;

/** Barras horizontais, uma por banco, ordenadas; o BB em amarelo e identificado pelo nome (não só pela cor). */
export function PeerBars({ banks, k, kind }: { banks: PeerBank[]; k: Key; kind: Kind }) {
  // Resultados (ROE, lucro, crescimento) seguem a regra verde/vermelho; saldos (ativo, carteira, capital) não.
  const signed = k === "roe_anualizado" || k === "lucro_trimestre" || k === "carteira_yoy_pct";
  const rows = banks.filter((b) => b[k] !== null).sort((a, b) => (b[k] as number) - (a[k] as number));
  if (!rows.length) return <p className="muted">Sem dado para o período.</p>;
  const vals = rows.map((r) => r[k] as number);
  const lo = Math.min(0, ...vals), hi = Math.max(0, ...vals);
  const W = 520, LBL = 128, PADR = 96, ROW = 30, H = rows.length * ROW + 6;
  const x = (v: number) => LBL + ((v - lo) / Math.max(hi - lo, 1e-9)) * (W - LBL - PADR);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
         aria-label={rows.map((r, i) => `${i + 1}º ${r.name}: ${fmt(r[k] as number, kind)}`).join("; ")}>
      {lo < 0 && <line x1={x(0)} x2={x(0)} y1={0} y2={H} stroke={C.axis} />}
      {rows.map((r, i) => {
        const v = r[k] as number, y = i * ROW + 4;
        const x0 = Math.min(x(0), x(v)), w = Math.max(Math.abs(x(v) - x(0)), 2);
        return (
          <g key={r.cod_inst}>
            <text x={LBL - 10} y={y + 15} textAnchor="end" className={r.is_bb ? "bridge-total" : "tick bridge-lbl"}>
              {i + 1}º {r.name}
            </text>
            <rect x={x0} y={y + 3} width={w} height={ROW - 12} rx={4}
                  fill={signed ? toneColor(v) : r.is_bb ? C.highlight : C.series}
                  stroke={signed && r.is_bb ? C.highlight : "none"} strokeWidth={2.5} />
            <text x={Math.max(x(v), x(0)) + 6} y={y + 15} className={r.is_bb ? "value-label" : "tick bridge-val"}>
              {fmt(v, kind)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
