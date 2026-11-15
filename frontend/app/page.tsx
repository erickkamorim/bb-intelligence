import { DonutChart } from "@/components/DonutChart";
import { EvolutionChart } from "@/components/EvolutionChart";
import { IconBars, IconCalendar, IconCard, IconCoins, IconDoc, IconGauge, IconPie, IconTarget, IconTrend } from "@/components/Icons";
import { KpiCard } from "@/components/KpiCard";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState, ErrorState } from "@/components/States";
import { api } from "@/lib/api";
import { date, number, pct, value } from "@/lib/format";
import type { CreditSegments, IndicatorItem, PeriodItem, SeriesPoint } from "@/lib/types";

export const dynamic = "force-dynamic";

function highlights(by: Record<string, IndicatorItem>): string[] {
  const out: string[] = [];
  const f = (code: string, label: string) => {
    const i = by[code];
    if (i?.status !== "ok" || i.value === undefined) return;
    let s = `${label}: ${value(i.value, i.unit)}`;
    if (i.yoy) s += ` (${i.yoy.value > 0 ? "+" : ""}${number(i.yoy.value, i.yoy.unit === "%" ? 1 : 2)}${i.yoy.unit === "%" ? "%" : " p.p."} a/a)`;
    else if (i.qoq) s += ` (${i.qoq.value > 0 ? "+" : ""}${number(i.qoq.value, i.qoq.unit === "%" ? 1 : 2)}${i.qoq.unit === "%" ? "%" : " p.p."} t/t)`;
    out.push(s);
  };
  f("lucro_liquido_ajustado", "Lucro líquido ajustado");
  f("roe_ajustado", "RSPL");
  f("inad_90", "Inadimplência +90 dias");
  f("carteira_agro", "Carteira de agronegócio");
  return out;
}

export default async function Page({ searchParams }: { searchParams: Promise<{ period?: string }> }) {
  const sp = await searchParams;
  const periods = await api<PeriodItem[]>("/periods");
  if (!periods.ok) {
    return (<><PageHeader title="Visão Executiva" subtitle="Desempenho e evolução dos principais indicadores do Banco do Brasil." />
      <ErrorState message={`${periods.error} Tente recarregar em alguns segundos.`} /></>);
  }
  if (!periods.data.length) {
    return (<><PageHeader title="Visão Executiva" subtitle="" />
      <EmptyState title="Sem dados carregados" message="O ETL ainda não gravou nenhum período." /></>);
  }
  const period = periods.data.find((p) => p.code === sp.period?.toUpperCase())?.code ?? periods.data[0].code;
  const sel = periods.data.find((p) => p.code === period)!;

  const [ind, seg, profit, roe] = await Promise.all([
    api<IndicatorItem[]>(`/indicators?period=${period}`),
    api<CreditSegments>(`/credit/segments?period=${period}`),
    api<SeriesPoint[]>(`/series/lucro_liquido_ajustado?to=${sel.end}`),
    api<SeriesPoint[]>(`/series/roe_ajustado?to=${sel.end}`),
  ]);

  const by: Record<string, IndicatorItem> = ind.ok ? Object.fromEntries(ind.data.map((i) => [i.code, i])) : {};
  const lastUpdate = ind.ok
    ? ind.data.map((i) => i.retrieved_at).filter((x): x is string => !!x).sort().at(-1) : undefined;
  const ipca = by.ipca_mensal;
  const selic = by.selic_meta;

  return (
    <>
      <PageHeader title="Visão Executiva" subtitle="Desempenho e evolução dos principais indicadores do Banco do Brasil."
                  periods={periods.data} period={period} lastUpdate={lastUpdate}
                  sources="RI do Banco do Brasil · CVM · Banco Central (SGS)" />

      {!ind.ok ? <ErrorState message={ind.error} /> : (
        <section className="kpis" aria-label="Indicadores principais">
          <KpiCard item={by.lucro_liquido_ajustado} icon={<IconCoins />} />
          <KpiCard item={by.roe_ajustado} icon={<IconTarget />} />
          <KpiCard item={by.carteira_credito_ampliada} icon={<IconCard />} />
          <KpiCard item={by.indice_eficiencia} icon={<IconGauge />} higherIsBetter={false}
                   note="Quanto menor, mais eficiente." />
        </section>
      )}

      <section className="row-main">
        <article className="card">
          <header className="card-head">
            <IconBars /><div><h2>Evolução do lucro líquido ajustado e do RSPL</h2>
              <p className="muted">Resultado gerencial divulgado pelo RI · até {sel.label}</p></div>
          </header>
          {profit.ok && roe.ok
            ? <EvolutionChart profit={profit.data} roe={roe.data} selectedEnd={sel.end} />
            : <ErrorState message={(!profit.ok ? profit.error : !roe.ok ? roe.error : "")} />}
        </article>
        <article className="card">
          <header className="card-head">
            <IconPie /><div><h2>Carteira de crédito por segmento</h2>
              <p className="muted">Carteira expandida · {sel.label}</p></div>
          </header>
          {!seg.ok ? <ErrorState message={seg.error} />
            : seg.data.status !== "ok" ? <EmptyState title="Sem dado" message={`Composição da carteira não publicada para ${sel.label}.`} />
            : <DonutChart data={seg.data} />}
        </article>
      </section>

      <section className="row-bottom">
        <article className="card">
          <header className="card-head"><IconTrend /><h2>Mercado &amp; Indicadores</h2></header>
          <table className="mini-table">
            <tbody>
              <tr><th scope="row">Selic (meta)</th>
                <td>{selic?.status === "ok" && selic.value !== undefined ? pct(selic.value, 2) + " a.a." : "Sem dado"}</td>
                <td className="muted">{selic?.as_of ? `em ${date(selic.as_of)}` : ""}</td></tr>
              <tr><th scope="row">IPCA (12 meses)</th>
                <td>{ipca?.ipca_12m ? pct(ipca.ipca_12m.value, 2) : "Sem dado"}</td>
                <td className="muted">{ipca?.as_of ? `até ${date(ipca.as_of).slice(3)}` : ""}</td></tr>
              <tr><th scope="row">Dólar PTAX</th><td>Sem dado</td><td className="muted">fonte em validação</td></tr>
              <tr><th scope="row">Ibovespa</th><td>Sem dado</td><td className="muted">licença B3 pendente</td></tr>
            </tbody>
          </table>
          <p className="chart-note">Banco Central — SGS (séries 432 e 433). IPCA 12m calculado a partir da variação mensal.</p>
        </article>
        <article className="card">
          <header className="card-head"><IconDoc /><h2>Destaques do {sel.label}</h2></header>
          {highlights(by).length ? (
            <ul className="highlights">{highlights(by).map((h) => <li key={h}>{h}</li>)}</ul>
          ) : <EmptyState title="Sem destaques" message="Nenhum indicador gerencial publicado para o período." />}
          <p className="chart-note">Fatos extraídos dos indicadores carregados; sem interpretação.</p>
        </article>
        <article className="card">
          <header className="card-head"><IconCalendar /><h2>Próximos eventos</h2></header>
          <EmptyState title="Agenda ainda não integrada"
                      message="Os eventos virão do calendário oficial do RI. Nenhuma data é exibida antes disso." />
        </article>
      </section>
    </>
  );
}
