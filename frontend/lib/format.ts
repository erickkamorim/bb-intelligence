const nf = (min: number, max: number) =>
  new Intl.NumberFormat("pt-BR", { minimumFractionDigits: min, maximumFractionDigits: max });

export function brl(v: number): string {
  const a = Math.abs(v);
  if (a >= 1e12) return `R$ ${nf(2, 2).format(v / 1e12)} tri`;
  if (a >= 1e9) return `R$ ${nf(2, 2).format(v / 1e9)} bi`;
  if (a >= 1e6) return `R$ ${nf(1, 1).format(v / 1e6)} mi`;
  return `R$ ${nf(2, 2).format(v)}`;
}

export function pct(v: number, digits?: number): string {
  const d = digits ?? (Math.abs(v * 10 - Math.round(v * 10)) > 1e-6 ? 2 : 1);
  return `${nf(d, d).format(v)}%`;
}

export function value(v: number, unit: string): string {
  if (unit === "BRL") return brl(v);
  if (unit === "pct") return pct(v);
  if (unit === "pct_aa") return `${nf(2, 2).format(v)}% a.a.`;
  if (unit === "BRL_per_USD") return `R$ ${nf(4, 4).format(v)}`;
  return nf(0, 2).format(v);
}

export function number(v: number, digits = 1): string {
  return nf(digits, digits).format(v);
}

/** Datas "de calendário" (período, publicação): lidas em UTC para não voltar um dia no fuso de Brasília. */
export function date(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso.length === 10 ? `${iso}T12:00:00Z` : iso);
  return d.toLocaleDateString("pt-BR", { timeZone: "UTC" });
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR", {
    timeZone: "America/Sao_Paulo", day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

/** "2026-09-30" -> "3T26" */
export function quarterLabel(iso: string): string {
  const [y, m] = iso.split("-").map(Number);
  return `${Math.floor((m - 1) / 3) + 1}T${String(y).slice(2)}`;
}

type Src = { source?: string; source_code?: string; locator?: string | null; published_at?: string | null };
const SHORT: Record<string, string> = {
  ri_bb: "RI do BB", cvm_itr: "CVM (ITR)", cvm_dfp: "CVM (DFP)", bcb_sgs: "Banco Central (SGS)",
};

/** Versão completa — tooltips e CSV. */
export function sourceLine(s: Src): string {
  const parts = [s.source, s.locator, s.published_at ? `publicado em ${date(s.published_at)}` : null];
  return parts.filter(Boolean).join(" · ");
}

/** Versão curta — cartões. Ex.: "RI do BB · Tabela 1, p. 10 · 11/11/2026". */
export function sourceShort(s: Src): string {
  const loc = s.locator?.split(";")[0]
    .replace(/^An[aá]lise do Desempenho [^,]*, /, "")
    .replace(/ – [^,]*,/, ",")
    .replace(/ \(p\. \d+ do PDF\)/, "");
  const parts = [SHORT[s.source_code ?? ""] ?? s.source, loc, s.published_at ? date(s.published_at) : null];
  return parts.filter(Boolean).join(" · ");
}
