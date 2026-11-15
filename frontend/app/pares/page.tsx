import type { Metadata } from "next";
import { IconBars, IconDoc, IconTrend } from "@/components/Icons";
import { PageHeader } from "@/components/PageHeader";
import { type PeerBank, PeerBars } from "@/components/PeerBars";
import { EmptyState, ErrorState } from "@/components/States";
import { api } from "@/lib/api";
import { number, quarterLabel, sourceLine } from "@/lib/format";
import type { PeriodItem, SourceMeta } from "@/lib/types";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Comparar Bancos" };

interface Peers {
  status: "ok" | "missing"; period?: string; period_end?: string; periods: string[]; reason?: string;
  banks?: PeerBank[]; bb_rank?: Record<string, { position: number | null; of: number }>;
  source?: SourceMeta; notes?: string[];
}

const LABELS: Record<string, string> = {
  roe_anualizado: "ROE", lucro_trimestre: "lucro do trimestre", carteira_credito: "carteira de crédito",
  carteira_yoy_pct: "crescimento da carteira em 12 meses", basileia: "Índice de Basileia", ativo_total: "ativo total",
};

const toItem = (code: string): PeriodItem => {
  const y = Number(code.slice(0, 4)), q = Number(code.slice(5));
  const end = new Date(Date.UTC(y, q * 3, 0)).toISOString().slice(0, 10);
  return { code, end, label: quarterLabel(end) };
};

export default async function ParesPage({ searchParams }: { searchParams: Promise<{ period?: string }> }) {
  const sp = await searchParams;
  const res = await api<Peers>(`/peers${sp.period ? `?period=${sp.period}` : ""}`);
  const header = (p?: Peers) => (
    <PageHeader title="Comparar Bancos"
                subtitle="Banco do Brasil frente a Itaú, Bradesco, Santander e Caixa, com dados regulatórios do Banco Central."
                periods={p?.periods.map(toItem)} period={p?.period}
                lastUpdate={p?.source?.retrieved_at ?? undefined}
                sources="Banco Central — IF.data (conglomerados prudenciais)" />
  );
  if (!res.ok) return (<>{header()}<ErrorState message={res.error} /></>);
  const d = res.data;
  if (d.status !== "ok" || !d.banks) {
    return (<>{header(d)}<EmptyState title="Sem dados de pares" message={d.reason ?? ""} /></>);
  }
  const lbl = quarterLabel(d.period_end!);
  const ranks = Object.entries(d.bb_rank ?? {}).filter(([, r]) => r.position);
  const bb = d.banks.find((b) => b.is_bb)!;
  const histEnds = Array.from(new Set(d.banks.flatMap((b) => b.roe_hist.map((h) => h.period_end)))).sort().slice(-6);

  return (
    <>
      {header(d)}
      <section className="headline" aria-label="Posição do BB">
        <IconTrend />
        <p>
          No {lbl}, o Banco do Brasil ficou em{" "}
          {ranks.map(([k, r], i) => (
            <span key={k}>{i > 0 ? (i === ranks.length - 1 ? " e " : ", ") : ""}{r.position}º de {r.of} em {LABELS[k]}</span>
          ))}
          {bb.roe_anualizado !== null ? `. ROE anualizado de ${number(bb.roe_anualizado, 1)}%` : ""}.
        </p>
      </section>

      <section className="row-2">
        {([
          ["ROE anualizado", "Lucro do trimestre × 4 / PL médio", "roe_anualizado", "pct"],
          ["Lucro líquido do trimestre", "Perímetro prudencial", "lucro_trimestre", "brl_bi"],
          ["Carteira de crédito", `Saldo em ${lbl}`, "carteira_credito", "brl_tri"],
          ["Crescimento da carteira", "Últimos 12 meses", "carteira_yoy_pct", "pct_signed"],
          ["Índice de Basileia", "Capital regulatório / ativos ponderados pelo risco", "basileia", "pct"],
          ["Ativo total", `Saldo em ${lbl}`, "ativo_total", "brl_tri"],
        ] as const).map(([title, sub, k, kind]) => (
          <article className="card" key={k}>
            <header className="card-head"><IconBars /><div><h2>{title}</h2><p className="muted">{sub}</p></div></header>
            <PeerBars banks={d.banks!} k={k} kind={kind} />
          </article>
        ))}
      </section>

      <article className="card">
        <header className="card-head"><IconDoc /><div><h2>ROE anualizado por trimestre</h2>
          <p className="muted">Evolução recente · cálculo da plataforma a partir do IF.data</p></div></header>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th scope="col">Banco</th>{histEnds.map((e) => <th key={e} scope="col" className="num">{quarterLabel(e)}</th>)}</tr></thead>
            <tbody>
              {d.banks.map((b) => {
                const m = new Map(b.roe_hist.map((h) => [h.period_end, h.value]));
                return (
                  <tr key={b.cod_inst} className={b.is_bb ? "row-bb" : undefined}>
                    <th scope="row">{b.name}</th>
                    {histEnds.map((e) => {
                      const v = m.get(e);
                      return <td key={e} className={`num${v !== undefined ? (v > 0 ? " pos" : v < 0 ? " neg" : "") : ""}`}>
                        {v !== undefined ? `${number(v, 1)}%` : "—"}</td>;
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="method">
          <h3>Como ler</h3>
          <ul>{(d.notes ?? []).map((n) => <li key={n}>{n}</li>)}
            <li>Cores: verde = resultado positivo, vermelho = negativo. O Banco do Brasil aparece com nome em negrito e contorno amarelo.</li></ul>
          {d.source && <p className="alert-src">Fonte: {sourceLine(d.source)}</p>}
        </div>
      </article>
    </>
  );
}
