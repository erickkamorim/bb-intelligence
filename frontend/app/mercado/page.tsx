import type { Metadata } from "next";
import { IconAlert, IconTrend } from "@/components/Icons";
import { type LinePoint, LineSeries } from "@/components/LineSeries";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState, ErrorState } from "@/components/States";
import { api } from "@/lib/api";
import { date, number, pct } from "@/lib/format";
import type { SeriesPoint } from "@/lib/types";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Mercado e Ações" };

/** A meta Selic só muda nas reuniões do Copom: guarda os degraus (ponto anterior + novo valor). */
function selicSteps(points: SeriesPoint[], today: string): LinePoint[] {
  const past = points.filter((p) => p.period_end <= today);
  const out: LinePoint[] = [];
  past.forEach((p, i) => {
    const prev = past[i - 1];
    if (!prev || prev.value !== p.value) {
      if (prev) out.push({ date: p.period_end, value: prev.value });
      out.push({ date: p.period_end, value: p.value });
    }
  });
  const last = past.at(-1);
  if (last && out.at(-1)?.date !== last.period_end) out.push({ date: last.period_end, value: last.value });
  return out;
}

/** IPCA acumulado em 12 meses a partir da variação mensal (cálculo próprio, marcado como derivado). */
function ipca12m(points: SeriesPoint[]): LinePoint[] {
  const s = [...points].sort((a, b) => a.period_end.localeCompare(b.period_end));
  const out: LinePoint[] = [];
  for (let i = 11; i < s.length; i++) {
    const win = s.slice(i - 11, i + 1);
    const [y0, m0] = win[0].period_end.split("-").map(Number);
    const [y1, m1] = win[11].period_end.split("-").map(Number);
    if ((y1 - y0) * 12 + (m1 - m0) !== 11) continue; // janela com mês faltando
    const acc = win.reduce((a, p) => a * (1 + p.value / 100), 1);
    out.push({ date: win[11].period_end, value: (acc - 1) * 100 });
  }
  return out;
}

export default async function MercadoPage() {
  const today = new Date().toISOString().slice(0, 10);
  const [selic, ipca] = await Promise.all([
    api<SeriesPoint[]>("/series/selic_meta?compact=true&from=2016-01-01"),
    api<SeriesPoint[]>("/series/ipca_mensal?compact=true"),
  ]);
  const sel = selic.ok ? selicSteps(selic.data, today) : [];
  const ip = ipca.ok ? ipca12m(ipca.data) : [];
  const lastSelic = sel.at(-1);
  const lastIpca = ip.at(-1);
  const real = lastSelic && lastIpca ? ((1 + lastSelic.value / 100) / (1 + lastIpca.value / 100) - 1) * 100 : null;

  return (
    <>
      <PageHeader title="Mercado e Ações" subtitle="Contexto macroeconômico do Banco Central. Dados de BBAS3 só entram com fonte licenciada."
                  sources="Banco Central — SGS (séries 432 e 433)" />

      <section className="kpis kpis-3" aria-label="Indicadores de mercado">
        <article className="card kpi">
          <h2 className="kpi-title">Meta Selic</h2>
          <p className="kpi-value">{lastSelic ? `${number(lastSelic.value, 2)}%` : "Sem dado"}</p>
          <p className="kpi-source">{lastSelic ? `ao ano · vigente em ${date(lastSelic.date)} · BCB/SGS 432` : ""}</p>
        </article>
        <article className="card kpi">
          <h2 className="kpi-title">IPCA acumulado 12 meses</h2>
          <p className="kpi-value">{lastIpca ? pct(lastIpca.value, 2) : "Sem dado"}</p>
          <p className="kpi-source">{lastIpca ? `até ${date(lastIpca.date).slice(3)} · calculado da série mensal BCB/SGS 433` : ""}</p>
        </article>
        <article className="card kpi">
          <h2 className="kpi-title">Juro real ex-post</h2>
          <p className="kpi-value">{real !== null ? pct(real, 2) : "Sem dado"}</p>
          <p className="kpi-source">Cálculo próprio: (1 + Selic) / (1 + IPCA 12m) − 1. Indicativo, não oficial.</p>
        </article>
      </section>

      <section className="row-2">
        <article className="card">
          <header className="card-head"><IconTrend /><div><h2>Meta Selic</h2>
            <p className="muted">% ao ano · definida pelo Copom</p></div></header>
          {selic.ok ? <LineSeries points={sel} axisTitle="% a.a." csvName="selic-meta" digits={2} />
            : <ErrorState message={selic.error} />}
        </article>
        <article className="card">
          <header className="card-head"><IconTrend /><div><h2>IPCA acumulado em 12 meses</h2>
            <p className="muted">% · calculado a partir da variação mensal</p></div></header>
          {ipca.ok ? <LineSeries points={ip} axisTitle="%" csvName="ipca-12m" digits={1} />
            : <ErrorState message={ipca.error} />}
        </article>
      </section>

      <section className="row-2">
        <article className="card">
          <header className="card-head"><IconAlert /><h2>BBAS3 — cotação, retorno e proventos</h2></header>
          <EmptyState title="Fonte ainda não licenciada"
                      message="Preços e proventos da B3 têm regras de redistribuição. A seção só será ativada com uma fonte cujo uso público esteja confirmado." />
        </article>
        <article className="card">
          <header className="card-head"><IconAlert /><h2>Dólar PTAX</h2></header>
          <EmptyState title="Série em validação"
                      message="O código da série no SGS ainda não foi confirmado nos metadados oficiais do Banco Central." />
        </article>
      </section>
    </>
  );
}
