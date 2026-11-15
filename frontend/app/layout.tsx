import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { Sidebar } from "@/components/Sidebar";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap", variable: "--font-inter" });

export const metadata: Metadata = {
  title: { default: "BB Intelligence", template: "%s · BB Intelligence" },
  description: "Plataforma independente de inteligência financeira sobre o Banco do Brasil, com fontes públicas auditáveis.",
};
export const viewport: Viewport = { themeColor: "#061B3A" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={inter.variable}>
      <body>
        <a href="#conteudo" className="skip-link">Pular para o conteúdo</a>
        <div className="shell">
          <Sidebar />
          <main id="conteudo" className="main" tabIndex={-1}>
            {children}
            <footer className="disclaimer" role="note">
              Projeto independente, não oficial e não afiliado ao Banco do Brasil. Informações para fins
              analíticos, não recomendação de investimento. Os dados são atualizados periodicamente (dias úteis),
              não em tempo real: cada número mostra a fonte e a data de publicação.
            </footer>
          </main>
        </div>
      </body>
    </html>
  );
}
