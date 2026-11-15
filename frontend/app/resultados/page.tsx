import type { Metadata } from "next";
import { BarSeries } from "@/components/BarSeries";
import { IconBars, IconCoins, IconDoc, IconPie } from "@/components/Icons";
import { KpiCard } from "@/components/KpiCard";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState } from "@/components/States";
import { api } from "@/lib/api";
import { brl, pct, periodCode, quarterLabel } from "@/lib/format";
import type { IndicatorItem, SeriesPoint } from "@/lib/types";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Resultados Financeiros" };

const COLS = [
  { code: "lucro_liquido_ajustado", label: "Lucro ajustado", src: "RI", fmt: (v: number) => brl(v) },
  { code: "lucro_liquido_contabil_ri", label: "Lucro contábil", src: "RI", fmt: (v: number) => brl(v) },
  { code: "lucro_liquido_contabil", label: "Lucro consolidado", src: "CVM", fmt: (v: number) => brl(v) },
  { code: "lucro_liquido_controladores", label: "Atribuído aos controladores", src: "CVM", fmt: (v: number) => brl(v) },
  { code: "roe_ajustado", label: "RSPL", src: "RI", fmt: (v: number) => pct(v) },
  { code: "indice_eficiencia", label: "Eficiência", src: "RI", fmt: (v: number) => pct(v) },
] as const;

export default async function ResultadosPage() {
  const series = await Promise.all(COLS.map((c) => api<SeriesPoint[]>(`/series/${c.code}`)));
  const failed = series.find((s) => !s.ok);
  if (failed && !failed.ok) {
    return (<><PageHeader title="Resultados Financeiros" subtitle="" /><ErrorState message={failed.error} /></>);
  }
  const data = series.map((s) => (s.ok ? s.data : []));
  const byCode = Object.fromEntries(COLS.map((c, i) => [c.code, new Map(data[i].map((p) => [p.period_end, p]))]));
  const ends = Array.from(new Set(data.flat().map((p) => p.period_end))).sort().reverse();

  // KPIs contábeis: último trimestre com balanço publicado na CVM
  const lastCvm = data[2].map((p) => p.period_end).sort().at(-1);
  const snap = lastCvm ? await api<IndicatorItem[]>(`/indicators?period=${periodCode(lastCvm)}`) : null;
  const by: Record<string, IndicatorItem> = snap && snap.ok ? Object.fromEntries(snap.data.map((i) => [i.code, i])) : {};

  return (
    <>
      <PageHeader title="Resultados Financeiros"
                  subtitle="Lucro contábil e ajustado, rentabilidade, eficiência e balanço. Gerencial (RI) e contábil (CVM) nunca são misturados."
                  sources="CVM (ITR/DFP, demonstrações consolidadas) · RI do Banco do Brasil" />

      {lastCvm && (
        <>
          <h2 className="section-title">Balanço e resultado contábil — CVM · {quarterLabel(lastCvm)}</h2>
          <section className="kpis" aria-label="Indicadores contábeis">
            <KpiCard item={by.lucro_liquido_contabil} icon={<IconCoins />} />
            <KpiCard item={by.lucro_liquido_controladores} icon={<IconCoins />} />
            <KpiCard item={by.patrimonio_liquido} icon={<IconPie />} />
            <KpiCard item={by.ativo_total} icon={<IconBars />} />
          </section>
        </>
      )}

      <section className="row-2">
        <article className="card">
          <header className="card-head"><IconBars /><div><h2>Lucro líquido consolidado (CVM)</h2>
            <p className="muted">Trimestre isolado · DRE consolidada, conta 3.11</p></div></header>
          <BarSeries points={data[2]} axisTitle="R$ bilhões" kind="brl_bi" csvName="lucro-consolidado-cvm" tone="sign" />
          <p className="chart-note">O 4T25 é derivado: exercício da DFP 2025 menos o acumulado de 9 meses do ITR.</p>
        </article>
        <article className="card">
          <header className="card-head"><IconBars /><div><h2>Índice de eficiência (RI)</h2>
            <p className="muted">Trimestral · quanto menor, mais eficiente</p></div></header>
          <BarSeries points={data[5]} axisTitle="% (despesas administrativas / receitas)" kind="pct" csvName="indice-eficiencia" tone="up_bad" />
        </article>
      </section>

      <article className="card">
        <header className="card-head"><IconDoc /><div><h2>Comparativo trimestral</h2>
          <p className="muted">Cada coluna mantém sua fonte. &quot;—&quot; = não publicado ou ainda não coletado.</p></div></header>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Trimestre</th>
                {COLS.map((c) => <th key={c.code} scope="col" className="num">{c.label}<span className="code">{c.src}</span></th>)}
              </tr>
            </thead>
            <tbody>
              {ends.map((e) => (
                <tr key={e}>
                  <th scope="row">{quarterLabel(e)}</th>
                  {COLS.map((c) => {
                    const p = byCode[c.code].get(e);
                    return (
                      <td key={c.code} className={`num${p && c.code !== "indice_eficiencia" ? (p.value > 0 ? " pos" : p.value < 0 ? " neg" : "") : ""}`}
                          title={p ? `${p.source ?? ""} ${p.locator ?? ""}`.trim() : undefined}>
                        {p ? c.fmt(p.value) : "—"}{p?.derivation ? "*" : ""}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="method">
          <h3>Notas metodológicas</h3>
          <ul>
            <li><strong>Lucro ajustado (RI)</strong> é gerencial: exclui itens que o banco classifica como extraordinários. Não é auditado como a DRE.</li>
            <li><strong>Lucro contábil (RI)</strong> é o número contábil apresentado no release; difere da DRE enviada à CVM por critério de apresentação.</li>
            <li><strong>Lucro consolidado (CVM)</strong> inclui a parcela de acionistas não controladores; <strong>atribuído aos controladores</strong> é a parte dos acionistas do BB.</li>
            <li><strong>RSPL</strong> é anualizado e calculado pelo banco sobre o lucro ajustado.</li>
            <li>* Valor derivado (ex.: 4º trimestre = exercício − 9 meses).</li>
          </ul>
        </div>
      </article>
    </>
  );
}
