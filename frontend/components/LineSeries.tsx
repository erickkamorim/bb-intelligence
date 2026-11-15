"use client";

import { useMemo, useState } from "react";
import { downloadCsv, niceScale } from "@/lib/chart";
import { date } from "@/lib/format";
import { IconDownload } from "./Icons";

const LINE = "#1D5BB0";
const GRID = "#E3E7ED";

export interface LinePoint { date: string; value: number }

/** Linha temporal de uma série (diária ou mensal) com cruz de leitura e filtro de janela. */
export function LineSeries({ points, axisTitle, fmt, csvName, windows = [["1a", 1], ["5a", 5], ["Tudo", 0]] }: {
  points: LinePoint[];
  axisTitle: string;
  fmt: (v: number) => string;
  csvName: string;
  windows?: [string, number][];
}) {
  const [years, setYears] = useState<number>(windows[windows.length - 1][1]);
  const [hover, setHover] = useState<number | null>(null);

  const data = useMemo(() => {
    if (!points.length || !years) return points;
    const last = new Date(points[points.length - 1].date + "T12:00:00Z");
    last.setUTCFullYear(last.getUTCFullYear() - years);
    const cut = last.toISOString().slice(0, 10);
    return points.filter((p) => p.date >= cut);
  }, [points, years]);

  if (!data.length) return <p className="muted">Sem observações para esta série.</p>;

  const W = 640, PADL = 52, PADR = 12, TOP = 24, H1 = 200, H = TOP + H1 + 30;
  const t0 = Date.parse(data[0].date), t1 = Date.parse(data[data.length - 1].date);
  const vals = data.map((d) => d.value);
  const s = niceScale(Math.max(...vals) * 1.05, Math.min(...vals, 0));
  const x = (d: string) => PADL + ((Date.parse(d) - t0) / Math.max(t1 - t0, 1)) * (W - PADL - PADR);
  const y = (v: number) => TOP + H1 - ((v - s.min) / (s.max - s.min)) * H1;
  const path = data.map((d, i) => `${i ? "L" : "M"}${x(d.date).toFixed(1)},${y(d.value).toFixed(1)}`).join("");
  const firstY = Number(data[0].date.slice(0, 4)), lastY = Number(data[data.length - 1].date.slice(0, 4));
  const stepY = Math.max(1, Math.ceil((lastY - firstY) / 6));
  const yearTicks: number[] = [];
  for (let yy = firstY + 1; yy <= lastY; yy += stepY) yearTicks.push(yy);

  const onMove = (e: React.PointerEvent<SVGRectElement>) => {
    const box = e.currentTarget.ownerSVGElement!.getBoundingClientRect();
    const px = ((e.clientX - box.left) / box.width) * W;
    let best = 0, bd = Infinity;
    data.forEach((d, i) => { const dd = Math.abs(x(d.date) - px); if (dd < bd) { bd = dd; best = i; } });
    setHover(best);
  };
  const h = hover !== null ? data[hover] : null;
  const last = data[data.length - 1];

  return (
    <div className="chart">
      <div className="chart-toolbar">
        <div className="segmented" role="group" aria-label="Janela de tempo">
          {windows.map(([label, n]) => (
            <button key={label} aria-pressed={years === n} onClick={() => setYears(n)}>{label}</button>
          ))}
        </div>
        <button className="btn-ghost" onClick={() => downloadCsv(`bb-intelligence-${csvName}.csv`,
          [["data", "valor"], ...data.map((d) => [d.date, d.value])])}>
          <IconDownload width={16} height={16} />CSV</button>
      </div>
      <div className="chart-canvas">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
             aria-label={`${axisTitle}: último valor ${fmt(last.value)} em ${date(last.date)}.`}>
          <text x={PADL} y={12} className="axis-title">{axisTitle}</text>
          {s.ticks.map((t) => (
            <g key={t}>
              <line x1={PADL} x2={W - PADR} y1={y(t)} y2={y(t)} stroke={t === 0 ? "#B8C0CC" : GRID} />
              <text x={PADL - 8} y={y(t) + 4} textAnchor="end" className="tick">{fmt(t)}</text>
            </g>
          ))}
          {yearTicks.map((yy) => {
            const xx = x(`${yy}-01-01`);
            return xx > PADL && xx < W - PADR
              ? <text key={yy} x={xx} y={H - 8} textAnchor="middle" className="tick">{yy}</text> : null;
          })}
          <path d={path} fill="none" stroke={LINE} strokeWidth={2} strokeLinejoin="round" />
          <circle cx={x(last.date)} cy={y(last.value)} r={6} fill="#fff" />
          <circle cx={x(last.date)} cy={y(last.value)} r={4} fill={LINE} />
          <text x={x(last.date) - 8} y={y(last.value) - 10} textAnchor="end" className="value-label">{fmt(last.value)}</text>
          {h && <line x1={x(h.date)} x2={x(h.date)} y1={TOP} y2={TOP + H1} stroke="#9AA3AE" />}
          {h && <circle cx={x(h.date)} cy={y(h.value)} r={4} fill={LINE} stroke="#fff" strokeWidth={2} />}
          <rect x={PADL} y={TOP} width={W - PADL - PADR} height={H1} fill="transparent"
                onPointerMove={onMove} onPointerLeave={() => setHover(null)} />
        </svg>
        {h && (
          <div className="tooltip" style={{ left: `${(x(h.date) / W) * 100}%` }} role="status">
            <strong>{date(h.date)}</strong><span>{fmt(h.value)}</span>
          </div>
        )}
      </div>
    </div>
  );
}
