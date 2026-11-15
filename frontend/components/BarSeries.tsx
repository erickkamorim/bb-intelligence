"use client";

import { useEffect, useRef, useState } from "react";
import { downloadCsv, niceScale, quarterEnds } from "@/lib/chart";
import { number, pct, quarterLabel, sourceLine } from "@/lib/format";
import type { SeriesPoint } from "@/lib/types";
import { IconDownload } from "./Icons";

const BAR = "#1D5BB0";
const BAR_SEL = "#002D5D";
const GRID = "#E3E7ED";

/** Barras trimestrais de uma única série, com lacunas explícitas ("s/ dado"). */
type Kind = "brl_bi" | "pct";

/** Formatação definida aqui (no cliente): funções não podem vir de componentes do servidor. */
function formatters(kind: Kind, digits: number) {
  if (kind === "brl_bi") {
    return { scale: 1e9, fmt: (v: number) => `R$ ${number(v, 2)} bi`,
             tick: (v: number) => number(v, Number.isInteger(v) ? 0 : 1) };
  }
  return { scale: 1, fmt: (v: number) => pct(v, digits), tick: (v: number) => `${number(v, Number.isInteger(v) ? 0 : 1)}%` };
}

export function BarSeries({ points, axisTitle, kind, digits = 1, csvName, selectedEnd }: {
  points: SeriesPoint[];
  axisTitle: string;
  kind: Kind;
  digits?: number;
  csvName: string;
  selectedEnd?: string;
}) {
  const { scale, fmt, tick: tickFmt } = formatters(kind, digits);
  const [hover, setHover] = useState<number | null>(null);
  const canvas = useRef<HTMLDivElement>(null);
  useEffect(() => { if (canvas.current) canvas.current.scrollLeft = canvas.current.scrollWidth; }, []);

  if (!points.length) return <p className="muted">Sem observações para esta série.</p>;
  const sorted = [...points].sort((a, b) => a.period_end.localeCompare(b.period_end));
  const pm = new Map(sorted.map((p) => [p.period_end, p]));
  const ends = quarterEnds(sorted[0].period_end, sorted[sorted.length - 1].period_end).slice(-10);
  const cols = ends.map((e) => ({ end: e, label: quarterLabel(e), p: pm.get(e), v: pm.has(e) ? pm.get(e)!.value / scale : undefined }));

  const vals = cols.map((c) => c.v).filter((v): v is number => v !== undefined);
  const s = niceScale(Math.max(...vals, 0) * 1.08, Math.min(...vals, 0));
  const W = 640, PADL = 52, PADR = 12, TOP = 24, H1 = 200, H = TOP + H1 + 30;
  const band = (W - PADL - PADR) / cols.length;
  const barW = Math.min(26, band * 0.5);
  const y = (v: number) => TOP + H1 - ((v - s.min) / (s.max - s.min)) * H1;
  const cx = (i: number) => PADL + band * i + band / 2;
  const h = hover !== null ? cols[hover] : null;

  return (
    <div className="chart">
      <div className="chart-toolbar">
        <span className="muted">{cols.length} trimestres</span>
        <button className="btn-ghost" onClick={() => downloadCsv(`bb-intelligence-${csvName}.csv`, [
          ["periodo", "valor", "fonte"],
          ...cols.map((c) => [c.label, c.p ? c.p.value : "", c.p ? sourceLine(c.p) : ""]),
        ])}><IconDownload width={16} height={16} />CSV</button>
      </div>
      <div className="chart-canvas" ref={canvas}>
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`${axisTitle}. Valores na tabela abaixo.`}>
          <text x={PADL} y={12} className="axis-title">{axisTitle}</text>
          {s.ticks.map((t) => (
            <g key={t}>
              <line x1={PADL} x2={W - PADR} y1={y(t)} y2={y(t)} stroke={t === 0 ? "#B8C0CC" : GRID} />
              <text x={PADL - 8} y={y(t) + 4} textAnchor="end" className="tick">{tickFmt(t)}</text>
            </g>
          ))}
          {cols.map((c, i) => {
            if (c.v === undefined) {
              return <text key={c.end} x={cx(i)} y={y(0) - 6} textAnchor="middle" className="tick muted-tick">s/ dado</text>;
            }
            const top = y(Math.max(c.v, 0)), bot = y(Math.min(c.v, 0)), hh = Math.max(bot - top, 1);
            const r = Math.min(4, hh / 2), x = cx(i) - barW / 2, sel = c.end === selectedEnd;
            const d = c.v >= 0
              ? `M${x},${bot} V${top + r} Q${x},${top} ${x + r},${top} H${x + barW - r} Q${x + barW},${top} ${x + barW},${top + r} V${bot} Z`
              : `M${x},${top} V${bot - r} Q${x},${bot} ${x + r},${bot} H${x + barW - r} Q${x + barW},${bot} ${x + barW},${bot - r} V${top} Z`;
            return (
              <g key={c.end}>
                <path d={d} fill={sel ? BAR_SEL : BAR} />
                {(sel || i === cols.length - 1) && (
                  <text x={cx(i)} y={(c.v >= 0 ? top : bot + 14) - 6} textAnchor="middle" className="value-label">{fmt(c.v)}</text>
                )}
              </g>
            );
          })}
          {cols.map((c, i) => (
            <text key={`x${c.end}`} x={cx(i)} y={H - 8} textAnchor="middle" className="tick">{c.label}</text>
          ))}
          {cols.map((c, i) => (
            <rect key={`h${c.end}`} x={PADL + band * i} y={TOP} width={band} height={H1} fill="transparent" className="hit"
                  tabIndex={0} role="button" aria-label={`${c.label}: ${c.v !== undefined ? fmt(c.v) : "sem dado"}`}
                  onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
                  onFocus={() => setHover(i)} onBlur={() => setHover(null)} />
          ))}
        </svg>
        {h && (
          <div className="tooltip" style={{ left: `${(cx(hover!) / W) * 100}%` }} role="status">
            <strong>{h.label}</strong>
            <span>{h.v !== undefined ? fmt(h.v) : "sem dado publicado"}</span>
            {h.p && <span className="tooltip-src">{sourceLine(h.p)}</span>}
          </div>
        )}
      </div>
      <details className="table-view">
        <summary>Ver dados em tabela</summary>
        <table>
          <thead><tr><th scope="col">Período</th><th scope="col">Valor</th></tr></thead>
          <tbody>{cols.map((c) => (
            <tr key={`t${c.end}`}><th scope="row">{c.label}</th><td>{c.v !== undefined ? fmt(c.v) : "—"}</td></tr>
          ))}</tbody>
        </table>
      </details>
    </div>
  );
}
