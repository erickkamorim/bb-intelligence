import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/States";

const SECTIONS: Record<string, { title: string; subtitle: string; plan: string }> = {
  resultados: {
    title: "Resultados Financeiros",
    subtitle: "Lucro contábil e ajustado, receitas, despesas, patrimônio, ROE e eficiência.",
    plan: "Próxima entrega: comparação t/t e a/a com detalhamento metodológico, separando lucro contábil (CVM) e ajustado (RI).",
  },
  credito: {
    title: "Crédito e Risco",
    subtitle: "Carteira por segmento, inadimplência +90 dias, provisões e cobertura.",
    plan: "Próxima entrega: séries de INAD+90d e cobertura por segmento, conforme definições do release.",
  },
  mercado: {
    title: "Mercado e Ações",
    subtitle: "BBAS3, retornos, proventos e volatilidade.",
    plan: "Bloqueado até confirmar uma fonte de preços com licença de redistribuição compatível.",
  },
  previsoes: {
    title: "Previsões",
    subtitle: "Cenários com validação temporal, intervalos e limitações.",
    plan: "Fase 2: só depois de histórico suficiente e backtesting sem vazamento de dados.",
  },
  ia: {
    title: "IA Insights",
    subtitle: "Perguntas em linguagem natural com citação de fonte e período.",
    plan: "Fase 2: respostas sempre baseadas em consulta aos dados e documentos, distinguindo fato de interpretação.",
  },
};

export function generateStaticParams() {
  return Object.keys(SECTIONS).map((slug) => ({ slug }));
}
export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  return { title: SECTIONS[slug]?.title ?? "Página" };
}

export default async function SectionPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const s = SECTIONS[slug];
  if (!s) notFound();
  return (
    <>
      <PageHeader title={s.title} subtitle={s.subtitle} />
      <EmptyState title="Em desenvolvimento" message={s.plan} />
    </>
  );
}
