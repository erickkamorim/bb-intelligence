import type { ReactNode } from "react";
import type { Delta, IndicatorItem } from "@/lib/types";
import { number, sourceLine, sourceShort, value } from "@/lib/format";
import { IconArrowDown, IconArrowUp } from "./Icons";

function DeltaChip({ d, label, higherIsBetter = true }: { d: Delta; label: string; higherIsBetter?: boolean }) {
  const up = d.value > 0;
  const flat = Math.abs(d.value) < 0.005;
  const good = flat ? null : up === higherIsBetter;
  const sign = d.value > 0 ? "+" : "";
  const txt = d.unit === "%" ? `${sign}${number(d.value, 1)}%` : `${sign}${number(d.value, 2)} p.p.`;
  return (
    <span className={`delta ${good === null ? "delta-flat" : good ? "delta-good" : "delta-bad"}`}
          aria-label={`${label}: ${txt}`}>
      {!flat && (up ? <IconArrowUp /> : <IconArrowDown />)}
      {txt} <span className="delta-label">{label}</span>
    </span>
  );
}

export function KpiCard({ item, icon, higherIsBetter = true, note }: {
  item: IndicatorItem | undefined; icon: ReactNode; higherIsBetter?: boolean; note?: string;
}) {
  if (!item) return null;
  const ok = item.status === "ok" && item.value !== undefined;
  return (
    <article className="card kpi" aria-labelledby={`kpi-${item.code}`}>
      <header className="kpi-head">
        <span className="kpi-icon">{icon}</span>
        <h2 id={`kpi-${item.code}`} className="kpi-title">{item.name}</h2>
      </header>
      {ok ? (
        <>
          <p className="kpi-value">{value(item.value!, item.unit)}</p>
          <div className="kpi-deltas">
            {item.yoy && <DeltaChip d={item.yoy} label="a/a" higherIsBetter={higherIsBetter} />}
            {item.qoq && <DeltaChip d={item.qoq} label="t/t" higherIsBetter={higherIsBetter} />}
          </div>
          <p className="kpi-source" title={`${sourceLine(item)}\n\n${item.definition}`}>Fonte: {sourceShort(item)}</p>
          {note && <p className="kpi-note">{note}</p>}
        </>
      ) : (
        <>
          <p className="kpi-value kpi-missing">Sem dado</p>
          <p className="kpi-source">Nenhuma observação publicada para {item.period}.</p>
        </>
      )}
    </article>
  );
}
