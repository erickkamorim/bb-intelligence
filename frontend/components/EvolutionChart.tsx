"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { number, quarterLabel, sourceLine } from "@/lib/format";
import type { SeriesPoint } from "@/lib/types";
import { IconDownload } from "./Icons";
import { C, toneColor } from "@/lib/theme";

const BAR = C.series;
const BAR_SEL = C.highlight;
const LINE = C.series;
const GRID = C.grid;
const INK2 = C.ink2;

type Mode = "q" | "y";
interface Col { key: string; label: string; profit?: number; roe?: number; complete: boolean; src?: SeriesPoint }

/** Escala com 4 intervalos "redondos": devolve [máximo, passo]. */
function niceScale(v: number): [number, number] {
  const raw = Math.max(v, 1e-9) / 4;
  const p = 10 ** Math.floor(Math.log10(raw));
  const n = raw / p;
  const step = (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p;
  return [step * Math.ceil(v / step), step];
}
const ticksOf = ([max, step]: [number, number]) =>
  Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step);

function quarterEnds(first: string, last: string): string[] {
  const out: string[] = [];
  let [y, m] = first.split("-").map(Number);
  const [ly, lm] = last.split("-").map(Number);
  while (y < ly || (y === ly && m <= lm)) {
    const end = new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10);
    out.push(end);
    m += 3;
    if (m > 12) { m -= 12; y += 1; }
  }
  return out;
}

/** "9M26", "6M26"... para acumulados do ano. */
const ytdLabel = (end: string) => `${Number(end.slice(5, 7))}M${end.slice(2, 4)}`;

export function EvolutionChart({ profit, roe, profitYtd = [], roeYtd = [], selectedEnd }: {
  profit: SeriesPoint[]; roe: SeriesPoint[]; profitYtd?: SeriesPoint[]; roeYtd?: SeriesPoint[]; selectedEnd: string;
}) {
  const [mode, setMode] = useState<Mode>("q");
  const [hover, setHover] = useState<number | null>(null);
  const canvas = useRef<HTMLDivElement>(null);
  // No celular o gráfico rola na horizontal: começa mostrando o período mais recente.
  useEffect(() => {
    if (canvas.current) canvas.current.scrollLeft = mode === "q" ? canvas.current.scrollWidth : 0;
  }, [mode]);

  const cols: Col[] = useMemo(() => {
    const all = [...profit, ...roe].map((p) => p.period_end).sort();
    if (!all.length && mode === "q") return [];
    const pm = new Map(profit.map((p) => [p.period_end, p]));
    const rm = new Map(roe.map((p) => [p.period_end, p]));
    if (mode === "q") {
      const ends = quarterEnds(all[0], all[all.length - 1]).slice(-8);
      return ends.map((e) => ({
        key: e, label: quarterLabel(e), profit: pm.get(e)?.value, roe: rm.get(e)?.value,
        complete: pm.has(e), src: pm.get(e),
      }));
    }
    // Acumulado no ano (YTD) publicado pelo banco: compara períodos iguais (ex.: 9M25 × 9M26)
    const pm2 = new Map(profitYtd.map((p) => [p.period_end, p]));
    const rm2 = new Map(roeYtd.map((p) => [p.period_end, p]));
    const yEnds = Array.from(new Set([...pm2.keys(), ...rm2.keys()])).filter((e) => e <= selectedEnd).sort().slice(-4);
    return yEnds.map((e) => ({ key: e, label: ytdLabel(e), profit: pm2.get(e)?.value, roe: rm2.get(e)?.value,
                               complete: pm2.has(e), src: pm2.get(e) }));
  }, [profit, roe, profitYtd, roeYtd, selectedEnd, mode]);

  if (!cols.length) {
    return (
      <div className="chart">
        <div className="chart-toolbar">
          <div className="segmented" role="group" aria-label="Agregação">
            <button aria-pressed={mode === "q"} onClick={() => setMode("q")}>Trimestral</button>
            <button aria-pressed={mode === "y"} onClick={() => setMode("y")}>Acumulado</button>
          </div>
        </div>
        <p className="muted">Sem dados {mode === "q" ? "trimestrais" : "acumulados no ano"} até este período.</p>
      </div>
    );
  }
  const ytdChange = mode === "y" && cols.length >= 2 && cols.at(-1)!.profit !== undefined
    ? (() => {
        const last = cols.at(-1)!, prevYear = cols.find((c) => c.key === `${Number(last.key.slice(0, 4)) - 1}${last.key.slice(4)}`);
        return prevYear?.profit ? { label: `${prevYear.label} → ${last.label}`, pct: (last.profit! / prevYear.profit - 1) * 100 } : null;
      })()
    : null;

  const W = 640, PADL = 52, PADR = 16, H1 = 190, H2 = 120, GAP = 34, TOP = 18;
  const plotW = W - PADL - PADR;
  const band = plotW / cols.length;
  const barW = Math.min(24, band * 0.5);
  const pScale = niceScale(Math.max(...cols.map((c) => (c.profit ?? 0) / 1e9), 0.1));
  const pMax = pScale[0];
  const pTicks = ticksOf(pScale);
  const yP = (v: number) => TOP + H1 - (v / pMax) * H1;
  const showRoe = true;
  const rVals = cols.map((c) => c.roe).filter((v): v is number => v !== undefined);
  const rScale = niceScale(Math.max(...rVals, 1) * 1.15);
  const rMax = rScale[0];
  const rTicks = ticksOf(rScale).filter((_, i, a) => a.length <= 4 || i % 2 === 0 || i === a.length - 1);
  const top2 = TOP + H1 + GAP + 14;
  const yR = (v: number) => top2 + H2 - (v / rMax) * H2;
  const cx = (i: number) => PADL + band * i + band / 2;
  const H = showRoe ? top2 + H2 + 30 : TOP + H1 + 30;

  const roeSegs: string[] = [];
  let cur = "";
  cols.forEach((c, i) => {
    if (c.roe === undefined) { if (cur) roeSegs.push(cur); cur = ""; return; }
    cur += `${cur ? "L" : "M"}${cx(i)},${yR(c.roe)}`;
  });
  if (cur) roeSegs.push(cur);

  const csv = () => {
    const rows = [["periodo", "lucro_liquido_ajustado_brl", "rspl_pct", "completo", "fonte"],
      ...cols.map((c) => [c.label, c.profit ?? "", showRoe ? (c.roe ?? "") : "", c.complete ? "sim" : "nao",
                          c.src ? sourceLine(c.src) : ""])];
    const blob = new Blob(["﻿" + rows.map((r) => r.map((x) => `"${String(x).replace(/"/g, '""')}"`).join(";"))
      .join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `bb-intelligence-lucro-rspl-${mode === "q" ? "trimestral" : "acumulado"}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const h = hover !== null ? cols[hover] : null;

  return (
    <div className="chart">
      <div className="chart-toolbar">
        <div className="segmented" role="group" aria-label="Agregação">
          <button aria-pressed={mode === "q"} onClick={() => setMode("q")}>Trimestral</button>
          <button aria-pressed={mode === "y"} onClick={() => setMode("y")}>Acumulado</button>
        </div>
        <button className="btn-ghost" onClick={csv}><IconDownload width={16} height={16} />CSV</button>
      </div>

      <div className="chart-canvas" ref={canvas}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" width="100%" style={{ minWidth: cols.length > 4 ? 460 : 0 }}
             aria-label={`Lucro líquido ajustado ${mode === "q" ? "por trimestre" : "acumulado no ano"}${showRoe ? " e RSPL" : ""}. Valores na tabela abaixo.`}>
          <text x={PADL} y={10} className="axis-title">Lucro líquido ajustado (R$ bi)</text>
          {pTicks.map((t) => (
            <g key={`p${t}`}>
              <line x1={PADL} x2={W - PADR} y1={yP(t)} y2={yP(t)} stroke={GRID} />
              <text x={PADL - 8} y={yP(t) + 4} textAnchor="end" className="tick">{number(t, Number.isInteger(t) ? 0 : 1)}</text>
            </g>
          ))}
          {cols.map((c, i) => {
            const sel = c.key === selectedEnd;
            if (c.profit === undefined) {
              return <text key={c.key} x={cx(i)} y={yP(0) - 6} textAnchor="middle" className="tick muted-tick">
                s/ dado</text>;
            }
            const v = c.profit / 1e9, y = yP(Math.max(v, 0)), hgt = Math.abs(yP(v) - yP(0));
            const r = Math.min(4, hgt / 2);
            const x = cx(i) - barW / 2;
            return (
              <g key={c.key}>
                <path d={`M${x},${yP(0)} V${y + r} Q${x},${y} ${x + r},${y} H${x + barW - r} Q${x + barW},${y} ${x + barW},${y + r} V${yP(0)} Z`}
                      fill={toneColor(c.profit)} stroke={sel ? BAR_SEL : "none"} strokeWidth={2.5} />
                {(sel || i === cols.length - 1) && (
                  <text x={cx(i)} y={y - 6} textAnchor="middle" className="value-label">{number(v, 2)}</text>
                )}
              </g>
            );
          })}

          {showRoe && (
            <>
              <text x={PADL} y={top2 - 8} className="axis-title">RSPL – ROE ajustado (% a.a.)</text>
              {rTicks.map((t) => (
                <g key={`r${t}`}>
                  <line x1={PADL} x2={W - PADR} y1={yR(t)} y2={yR(t)} stroke={GRID} />
                  <text x={PADL - 8} y={yR(t) + 4} textAnchor="end" className="tick">{number(t, 0)}%</text>
                </g>
              ))}
              {roeSegs.map((d) => <path key={d} d={d} fill="none" stroke={LINE} strokeWidth={2}
                                        strokeLinejoin="round" strokeLinecap="round" />)}
              {cols.map((c, i) => c.roe === undefined ? (
                <text key={`rm${c.key}`} x={cx(i)} y={yR(0) - 6} textAnchor="middle" className="tick muted-tick">s/ dado</text>
              ) : (
                <g key={`rd${c.key}`}>
                  <circle cx={cx(i)} cy={yR(c.roe)} r={6} fill={C.surface} />
                  <circle cx={cx(i)} cy={yR(c.roe)} r={4} fill={toneColor(c.roe)} />
                  {i === cols.length - 1 && (
                    <text x={cx(i)} y={yR(c.roe) + 20} textAnchor="middle" className="value-label">{number(c.roe, 1)}%</text>
                  )}
                </g>
              ))}
            </>
          )}

          {cols.map((c, i) => (
            <text key={`x${c.key}`} x={cx(i)} y={H - 8} textAnchor="middle" className="tick" fill={INK2}>{c.label}</text>
          ))}
          {cols.map((c, i) => (
            <rect key={`hit${c.key}`} x={PADL + band * i} y={TOP} width={band} height={H - TOP - 20}
                  fill="transparent" tabIndex={0} role="button"
                  aria-label={`${c.label}: lucro ${c.profit !== undefined ? `R$ ${number(c.profit / 1e9, 2)} bi` : "sem dado"}${showRoe ? `, RSPL ${c.roe !== undefined ? `${number(c.roe, 1)}%` : "sem dado"}` : ""}`}
                  onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
                  onFocus={() => setHover(i)} onBlur={() => setHover(null)}
                  className="hit" />
          ))}
          {hover !== null && <line x1={cx(hover)} x2={cx(hover)} y1={TOP} y2={H - 22} stroke={C.muted} />}
        </svg>
        {h && (
          <div className="tooltip" style={{ left: `${(cx(hover!) / W) * 100}%` }} role="status">
            <strong>{h.label}</strong>
            <span>Lucro ajustado: {h.profit !== undefined ? `R$ ${number(h.profit / 1e9, 2)} bi`
              : "sem dado"}</span>
            {showRoe && <span>RSPL: {h.roe !== undefined ? `${number(h.roe, 1)}% a.a.` : "sem dado"}</span>}
            {h.src && <span className="tooltip-src">{sourceLine(h.src)}</span>}
          </div>
        )}
      </div>

      {ytdChange && (
        <p className="ytd-change">
          Lucro ajustado {ytdChange.label}:{" "}
          <strong className={ytdChange.pct >= 0 ? "pos" : "neg"}>{ytdChange.pct > 0 ? "+" : ""}{number(ytdChange.pct, 1)}%</strong>
        </p>
      )}
      <p className="chart-note">
        {mode === "q"
          ? "Verde = resultado positivo, vermelho = negativo; trimestre selecionado com contorno amarelo. Lucro e RSPL em gráficos separados, cada um com sua escala."
          : "Acumulado de janeiro até o trimestre, como publicado pelo banco (lucro e RSPL do período). Compara sempre períodos iguais, ex.: 9M25 × 9M26."}
      </p>
      <details className="table-view">
        <summary>Ver dados em tabela</summary>
        <table>
          <thead><tr><th scope="col">Período</th><th scope="col">Lucro ajustado</th>{showRoe && <th scope="col">RSPL</th>}</tr></thead>
          <tbody>
            {cols.map((c) => (
              <tr key={`t${c.key}`}>
                <th scope="row">{c.label}</th>
                <td>{c.profit !== undefined ? `R$ ${number(c.profit / 1e9, 2)} bi` : "—"}</td>
                {showRoe && <td>{c.roe !== undefined ? `${number(c.roe, 1)}%` : "—"}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
