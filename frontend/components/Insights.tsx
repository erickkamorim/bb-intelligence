import { number, pct, quarterLabel, sourceShort, value } from "@/lib/format";
import type { SourceMeta } from "@/lib/types";
import type { Bridge } from "./BridgeChart";
import { IconAlert, IconArrowDown, IconArrowUp, IconCheck } from "./Icons";

export interface AlertItem extends SourceMeta {
  code: string; name: string; unit: string; value: number; compare: "t/t" | "a/a"; compare_period: string;
  delta: number; delta_unit: "%" | "p.p."; direction: "up" | "down"; tone: "positive" | "negative"; extreme: string | null;
}
export interface NoteItem { period: string; topic: string; text: string; source_locator: string }

const bi = (v: number) => `R$ ${number(Math.abs(v) / 1e9, 2)} bi`;

const PHRASE: Record<string, string> = {
  margem_financeira_bruta: "a margem financeira", custo_credito: "o custo do crédito", receitas_servicos: "as receitas de serviços",
  despesas_administrativas: "as despesas administrativas", outras_receitas_despesas_op: "outras receitas e despesas operacionais",
  provisoes: "as provisões", resultado_nao_operacional: "o resultado não operacional", ir_csll: "o IR/CSLL",
  participacoes_estatutarias: "as participações estatutárias", participacoes_minoritarias: "a parcela dos minoritários",
};
const phrase = (st: { code: string; label: string }) => PHRASE[st.code] ?? st.label;

export type Seg = { text: string; tone?: "pos" | "neg" };

/** Frase-resumo montada só com números carregados (sem adjetivos, sem previsão). Números positivos em verde, negativos em vermelho. */
export function headline(lucro: { value?: number; qoq?: { value: number } | null } | undefined, bridge: Bridge | null,
                         label: string): Seg[] | null {
  if (lucro?.value === undefined) return null;
  const segs: Seg[] = [{ text: `No ${label}, o lucro líquido ajustado foi de ` },
    { text: bi(lucro.value), tone: lucro.value >= 0 ? "pos" : "neg" }];
  if (lucro.qoq) {
    segs.push({ text: " (" }, { text: `${lucro.qoq.value > 0 ? "+" : ""}${number(lucro.qoq.value, 1)}%`,
      tone: lucro.qoq.value >= 0 ? "pos" : "neg" }, { text: " no trimestre)" });
  }
  if (bridge?.status === "ok" && bridge.steps?.length) {
    const neg = [...bridge.steps].sort((a, b) => a.delta - b.delta)[0];
    const pos = [...bridge.steps].sort((a, b) => b.delta - a.delta)[0];
    if (neg.delta < 0) segs.push({ text: `. O que mais pesou: ${phrase(neg)} (` }, { text: `−${bi(neg.delta)}`, tone: "neg" }, { text: ")" });
    if (pos.delta > 0) segs.push({ text: `; o que mais ajudou: ${phrase(pos)} (` }, { text: `+${bi(pos.delta)}`, tone: "pos" }, { text: ")" });
  }
  segs.push({ text: "." });
  return segs;
}

export function AlertsPanel({ items }: { items: AlertItem[] }) {
  if (!items.length) {
    return <p className="muted">Nenhuma variação acima dos limites no trimestre.</p>;
  }
  return (
    <ul className="alerts">
      {items.slice(0, 6).map((a) => {
        const d = a.delta_unit === "%" ? `${a.delta > 0 ? "+" : ""}${number(a.delta, 1)}%` : `${a.delta > 0 ? "+" : ""}${number(a.delta, 2)} p.p.`;
        return (
          <li key={a.code} className={`alert alert-${a.tone}`}>
            <span className="alert-icon" aria-hidden="true">{a.tone === "negative" ? <IconAlert width={18} height={18} /> : <IconCheck width={18} height={18} />}</span>
            <div>
              <p className="alert-title">
                {a.name} <span className="alert-delta">{a.direction === "up" ? <IconArrowUp /> : <IconArrowDown />}{d} {a.compare}</span>
              </p>
              <p className="alert-sub">
                {a.unit.startsWith("pct") ? pct(a.value) : value(Math.abs(a.value), a.unit)} no trimestre
                {` · vs ${quarterLabel(periodEnd(a.compare_period))}`}
                {a.extreme ? ` · ${a.extreme}` : ""}
                <span className="sr-only">{a.tone === "negative" ? " (sinal de atenção)" : " (sinal positivo)"}</span>
              </p>
              <p className="alert-src">Fonte: {sourceShort(a)}</p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function periodEnd(code: string): string {
  const y = Number(code.slice(0, 4)), q = Number(code.slice(5));
  const m = q * 3;
  return new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10);
}

export function NotesPanel({ items }: { items: NoteItem[] }) {
  if (!items.length) return <p className="muted">Sem notas do release carregadas para este trimestre.</p>;
  return (
    <ul className="notes">
      {items.map((n) => (
        <li key={n.topic}>
          <p>{n.text}</p>
          <p className="alert-src">{n.source_locator}</p>
        </li>
      ))}
    </ul>
  );
}
