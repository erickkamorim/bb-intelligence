"use client";

import { useState } from "react";
import { niceScale } from "@/lib/chart";
import { number, quarterLabel, sourceLine } from "@/lib/format";
import { C } from "@/lib/theme";
import type { SourceMeta } from "@/lib/types";

export interface Bridge {
  status: "ok" | "missing";
  period: string;
  from_period?: string;
  from_end?: string;
  start?: number;
  end?: number;
  steps?: { code: string; label: string; delta: number }[];
  residual?: number;
  closes?: boolean;
  reason?: string;
  source?: SourceMeta;
}

// Ordem da DRE gerencial (de cima para baixo), não por tamanho: é assim que o resultado se forma.
const ORDER = ["margem_financeira_bruta", "custo_credito", "receitas_servicos", "despesas_administrativas",
  "outras_receitas_despesas_op", "provisoes", "resultado_nao_operacional", "ir_csll",
  "participacoes_estatutarias", "participacoes_minoritarias"];

const bi = (v: number, sign = false) =>
  `${sign ? (v > 0 ? "+" : v < 0 ? "−" : "") : ""}R$ ${number(Math.abs(v) / 1e9, 2)} bi`;

export function BridgeChart({ data, toLabel }: { data: Bridge; toLabel: string }) {
  const [hover, setHover] = useState<number | null>(null);
  if (data.status !== "ok" || !data.steps || data.start === undefined || data.end === undefined) return null;

  const steps = [...data.steps].sort((a, b) => ORDER.indexOf(a.code) - ORDER.indexOf(b.code));
  const fromLabel = data.from_end ? quarterLabel(data.from_end) : data.from_period ?? "";
  type Row = { label: string; a: number; b: number; kind: "total" | "up" | "down"; delta?: number };
  const rows: Row[] = [{ label: `Lucro ${fromLabel}`, a: 0, b: data.start, kind: "total" }];
  let acc = data.start;
  for (const s of steps) {
    rows.push({ label: s.label, a: acc, b: acc + s.delta, kind: s.delta >= 0 ? "up" : "down", delta: s.delta });
    acc += s.delta;
  }
  rows.push({ label: `Lucro ${toLabel}`, a: 0, b: data.end, kind: "total" });

  const lo = Math.min(0, ...rows.map((r) => Math.min(r.a, r.b))) / 1e9;
  const hi = Math.max(...rows.map((r) => Math.max(r.a, r.b))) / 1e9;
  const s = niceScale(hi * 1.05, lo);
  const W = 640, LBL = 150, PADR = 92, ROW = 30, TOP = 26, H = TOP + rows.length * ROW + 24;
  const x = (v: number) => LBL + ((v / 1e9 - s.min) / (s.max - s.min)) * (W - LBL - PADR);
  const color = (k: Row["kind"], v: number) =>
    k === "total" ? (v >= 0 ? C.pos : C.neg) : k === "up" ? C.pos : C.neg;
  const h = hover !== null ? rows[hover] : null;

  return (
    <div className="chart">
      <div className="chart-canvas">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
             aria-label={`Ponte do lucro ajustado de ${fromLabel} (${bi(data.start)}) para ${toLabel} (${bi(data.end)}). ${steps.map((st) => `${st.label} ${bi(st.delta, true)}`).join("; ")}.`}>
          {s.ticks.map((t) => (
            <g key={t}>
              <line x1={x(t * 1e9)} x2={x(t * 1e9)} y1={TOP - 6} y2={H - 22} stroke={t === 0 ? C.axis : C.grid} />
              <text x={x(t * 1e9)} y={H - 6} textAnchor="middle" className="tick">{number(t, Number.isInteger(t) ? 0 : 1)}</text>
            </g>
          ))}
          <text x={LBL - 10} y={H - 6} textAnchor="end" className="tick">R$ bi</text>
          {rows.map((r, i) => {
            const y = TOP + i * ROW;
            const x0 = x(Math.min(r.a, r.b)), x1 = x(Math.max(r.a, r.b));
            const w = Math.max(x1 - x0, 2);
            const next = rows[i + 1];
            return (
              <g key={r.label}>
                <text x={LBL - 10} y={y + 15} textAnchor="end" className={r.kind === "total" ? "bridge-total" : "tick bridge-lbl"}>{r.label}</text>
                <rect x={x0} y={y + 4} width={w} height={ROW - 10} rx={3} fill={color(r.kind, r.b)}
                      stroke={i === rows.length - 1 ? C.highlight : "none"} strokeWidth={2} />
                {next && next.kind !== "total" && (
                  <line x1={x(r.b)} x2={x(r.b)} y1={y + ROW - 6} y2={y + ROW + 4} stroke={C.muted} />
                )}
                <text x={x1 + 6} y={y + 15} className={r.kind === "total" ? "value-label" : "tick bridge-val"}>
                  {r.kind === "total" ? bi(r.b) : bi(r.delta!, true)}
                </text>
                <rect x={0} y={y} width={W} height={ROW} fill="transparent" className="hit" tabIndex={0} role="button"
                      aria-label={`${r.label}: ${r.kind === "total" ? bi(r.b) : bi(r.delta!, true)}`}
                      onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
                      onFocus={() => setHover(i)} onBlur={() => setHover(null)} />
              </g>
            );
          })}
        </svg>
        {h && (
          <div className="tooltip" style={{ left: "60%" }} role="status">
            <strong>{h.label}</strong>
            <span>{h.kind === "total" ? bi(h.b) : `${bi(h.delta!, true)} no lucro vs ${fromLabel}`}</span>
            {h.kind !== "total" && <span className="tooltip-src">Acumulado: {bi(h.b)}</span>}
          </div>
        )}
      </div>
      <p className="chart-note">
        Variação de cada linha da DRE gerencial entre {fromLabel} e {toLabel}. Verde = efeito positivo no lucro, vermelho = negativo
        (o sinal está sempre no rótulo).{data.closes ? " A soma fecha com o lucro divulgado." : ` Diferença de arredondamento: ${bi(data.residual ?? 0, true)}.`}
        {data.source ? ` Fonte: ${sourceLine(data.source)}.` : ""}
      </p>
    </div>
  );
}
