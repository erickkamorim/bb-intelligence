import type { Metadata } from "next";
import { BarSeries } from "@/components/BarSeries";
import { DonutChart } from "@/components/DonutChart";
import { IconAlert, IconCard, IconDoc, IconPie } from "@/components/Icons";
import { KpiCard } from "@/components/KpiCard";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState, ErrorState } from "@/components/States";
import { api } from "@/lib/api";
import { brl, number, quarterLabel } from "@/lib/format";
import type { CreditSegments, IndicatorItem, PeriodItem, SeriesPoint } from "@/lib/types";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Crédito e Risco" };

const SEGS = [
  { code: "carteira_pf", label: "Pessoas Físicas" },
  { code: "carteira_pj", label: "Pessoas Jurídicas" },
  { code: "carteira_agro", label: "Agronegócio" },
  { code: "carteira_credito_ampliada", label: "Total (expandida)" },
] as const;

export default async function CreditoPage({ searchParams }: { searchParams: Promise<{ period?: string }> }) {
  const sp = await searchParams;
  const periods = await api<PeriodItem[]>("/periods");
  if (!periods.ok) {
    return (<><PageHeader title="Crédito e Risco" subtitle="" /><ErrorState message={periods.error} /></>);
  }
  const ri = await api<SeriesPoint[]>("/series/carteira_credito_ampliada");
  const riEnds = new Set(ri.ok ? ri.data.map((p) => p.period_end) : []);
  // Só oferece períodos em que há carteira publicada (crédito vem do RI)
  const opts = periods.data.filter((p) => riEnds.has(p.end));
  if (!opts.length) {
    return (<><PageHeader title="Crédito e Risco" subtitle="" />
      <EmptyState title="Sem dados de crédito" message="Nenhum release do RI com carteira foi carregado." /></>);
  }
  const period = opts.find((p) => p.code === sp.period?.toUpperCase())?.code ?? opts[0].code;
  const sel = opts.find((p) => p.code === period)!;

  const [ind, seg, inad, ...segSeries] = await Promise.all([
    api<IndicatorItem[]>(`/indicators?period=${period}`),
    api<CreditSegments>(`/credit/segments?period=${period}`),
    api<SeriesPoint[]>("/series/inad_90"),
    ...SEGS.map((s) => api<SeriesPoint[]>(`/series/${s.code}`)),
  ]);
  const by: Record<string, IndicatorItem> = ind.ok ? Object.fromEntries(ind.data.map((i) => [i.code, i])) : {};
  const maps = segSeries.map((r) => new Map((r.ok ? r.data : []).map((p) => [p.period_end, p.value])));
  const ends = Array.from(riEnds).sort().reverse();

  return (
    <>
      <PageHeader title="Crédito e Risco" subtitle="Carteira por segmento e inadimplência acima de 90 dias, conforme as definições do release do BB."
                  periods={opts} period={period} sources="RI do Banco do Brasil (Análise do Desempenho)" />

      {!ind.ok ? <ErrorState message={ind.error} /> : (
        <section className="kpis" aria-label="Indicadores de crédito">
          <KpiCard item={by.carteira_credito_ampliada} icon={<IconCard />} />
          <KpiCard item={by.inad_90} icon={<IconAlert />} higherIsBetter={false} note="Quanto menor, melhor." />
          <KpiCard item={by.carteira_agro} icon={<IconPie />} />
          <KpiCard item={by.carteira_pj} icon={<IconPie />} />
        </section>
      )}

      <section className="row-2">
        <article className="card">
          <header className="card-head"><IconPie /><div><h2>Composição da carteira</h2>
            <p className="muted">Carteira expandida · {sel.label}</p></div></header>
          {seg.ok && seg.data.status === "ok" ? <DonutChart data={seg.data} />
            : <EmptyState title="Sem dado" message={`Composição não publicada para ${sel.label}.`} />}
        </article>
        <article className="card">
          <header className="card-head"><IconAlert /><div><h2>Inadimplência acima de 90 dias</h2>
            <p className="muted">INAD+90d · carteira classificada</p></div></header>
          {inad.ok ? (
            <BarSeries points={inad.data} axisTitle="% da carteira classificada" kind="pct" digits={2}
                       csvName="inad-90" selectedEnd={sel.end} />
          ) : <ErrorState message={inad.error} />}
        </article>
      </section>

      <article className="card">
        <header className="card-head"><IconDoc /><div><h2>Evolução da carteira por segmento</h2>
          <p className="muted">Saldos em fim de trimestre · variação contra o trimestre anterior disponível</p></div></header>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th scope="col">Trimestre</th>{SEGS.map((s) => <th key={s.code} scope="col" className="num">{s.label}</th>)}</tr></thead>
            <tbody>
              {ends.map((e, idx) => (
                <tr key={e}>
                  <th scope="row">{quarterLabel(e)}</th>
                  {SEGS.map((s, i) => {
                    const v = maps[i].get(e);
                    const prevEnd = ends[idx + 1];
                    const pv = prevEnd ? maps[i].get(prevEnd) : undefined;
                    return (
                      <td key={s.code} className="num">
                        {v !== undefined ? brl(v) : "—"}
                        {v !== undefined && pv ? (
                          <span className="code">{v >= pv ? "+" : ""}{number((v / pv - 1) * 100, 1)}% vs {quarterLabel(prevEnd!)}</span>
                        ) : null}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="method">
          <h3>Ainda não coletado</h3>
          <ul>
            <li>Provisões, perda esperada e índice de cobertura — próxima rodada de curadoria do release.</li>
            <li>Os trimestres sem release carregado (4T25 e 1T26) aparecem sem dado; a variação compara com o trimestre anterior disponível.</li>
          </ul>
        </div>
      </article>
    </>
  );
}
