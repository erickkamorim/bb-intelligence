import { date } from "@/lib/format";
import type { PeriodItem } from "@/lib/types";
import { IconClock } from "./Icons";
import { PeriodSelect } from "./PeriodSelect";

export function PageHeader({ title, subtitle, periods, period, lastUpdate, sources }: {
  title: string; subtitle: string; periods?: PeriodItem[]; period?: string; lastUpdate?: string; sources?: string;
}) {
  return (
    <header className="page-header">
      <div className="page-header-text">
        <h1>{title}</h1>
        {subtitle && <p className="subtitle">{subtitle}</p>}
        {sources && <p className="sources">Fontes: {sources}</p>}
      </div>
      <div className="page-header-meta">
        {periods && period && <PeriodSelect periods={periods} value={period} />}
        {lastUpdate && (
          <p className="last-update"><IconClock width={16} height={16} />
            <span>Base atualizada em<br /><strong>{date(lastUpdate)}</strong>
              <span className="freq">Atualização diária · não é tempo real</span></span></p>
        )}
      </div>
    </header>
  );
}
