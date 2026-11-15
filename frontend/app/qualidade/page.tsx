import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState, StatusBadge } from "@/components/States";
import { api } from "@/lib/api";
import { date, dateTime } from "@/lib/format";
import type { DataQuality } from "@/lib/types";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Qualidade dos Dados" };

const SOURCE_NAME: Record<string, string> = {
  cvm_itr: "CVM — ITR", cvm_dfp: "CVM — DFP", bcb_sgs: "Banco Central — SGS", ri_bb: "RI do BB (curadoria)",
};
const FREQ: Record<string, string> = { quarterly: "Trimestral", monthly: "Mensal", daily: "Diária" };

export default async function QualidadePage() {
  const res = await api<DataQuality>("/data-quality");
  return (
    <>
      <PageHeader title="Qualidade dos Dados"
                  subtitle="Cobertura, atraso e execuções do pipeline. Indisponível, desatualizado e erro de coleta são estados diferentes."
                  lastUpdate={res.ok ? res.data.checked_at : undefined} />
      {!res.ok ? <ErrorState message={res.error} /> : (
        <>
          <section className="kpis kpis-3" aria-label="Resumo">
            <article className="card kpi"><h2 className="kpi-title">Atualizados</h2><p className="kpi-value">{res.data.summary.ok}</p></article>
            <article className="card kpi"><h2 className="kpi-title">Desatualizados</h2><p className="kpi-value">{res.data.summary.stale}</p></article>
            <article className="card kpi"><h2 className="kpi-title">Indisponíveis</h2><p className="kpi-value">{res.data.summary.missing}</p></article>
          </section>
          <article className="card">
            <header className="card-head"><h2>Cobertura por indicador</h2></header>
            <div className="table-wrap">
              <table className="data-table">
                <thead><tr>
                  <th scope="col">Indicador</th><th scope="col">Fonte</th><th scope="col">Frequência</th>
                  <th scope="col">Obs.</th><th scope="col">Primeiro</th><th scope="col">Último</th>
                  <th scope="col">Coletado em</th><th scope="col">Status</th>
                </tr></thead>
                <tbody>
                  {res.data.indicators.map((i) => (
                    <tr key={i.code}>
                      <th scope="row">{i.name}<span className="code">{i.code}</span></th>
                      <td>{SOURCE_NAME[i.source] ?? i.source}</td>
                      <td>{FREQ[i.frequency] ?? i.frequency}</td>
                      <td className="num">{i.observations.toLocaleString("pt-BR")}</td>
                      <td>{date(i.first_period)}</td>
                      <td>{date(i.last_period)}</td>
                      <td>{dateTime(i.last_retrieved_at)}</td>
                      <td><StatusBadge status={i.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>
          <article className="card">
            <header className="card-head"><h2>Últimas execuções do ETL</h2></header>
            <div className="table-wrap">
              <table className="data-table">
                <thead><tr>
                  <th scope="col">#</th><th scope="col">Rotina</th><th scope="col">Início</th>
                  <th scope="col">Status</th><th scope="col">Inseridas</th><th scope="col">Revisadas</th><th scope="col">Erro</th>
                </tr></thead>
                <tbody>
                  {res.data.runs.map((r) => (
                    <tr key={r.id}>
                      <td className="num">{r.id}</td><td><code>{r.job}</code></td><td>{dateTime(r.started_at)}</td>
                      <td><span className={`badge ${r.status === "success" ? "badge-ok" : r.status === "failed" ? "badge-missing" : "badge-warn"}`}>
                        {r.status === "success" ? "Sucesso" : r.status === "failed" ? "Falhou" : "Em execução"}</span></td>
                      <td className="num">{r.rows_inserted.toLocaleString("pt-BR")}</td>
                      <td className="num">{r.rows_updated.toLocaleString("pt-BR")}</td>
                      <td className="err">{r.error ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>
        </>
      )}
    </>
  );
}
