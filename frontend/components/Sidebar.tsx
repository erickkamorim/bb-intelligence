"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  IconBars, IconChevronLeft, IconClose, IconDatabase, IconGrid, IconMenu, IconShield, IconSpark,
  IconScale, IconTarget, IconTrend,
} from "./Icons";

const NAV = [
  { href: "/", label: "Visão Executiva", Icon: IconGrid },
  { href: "/resultados", label: "Resultados Financeiros", Icon: IconBars },
  { href: "/credito", label: "Crédito e Risco", Icon: IconShield },
  { href: "/mercado", label: "Mercado e Ações", Icon: IconTrend },
  { href: "/pares", label: "Comparar Bancos", Icon: IconScale },
  { href: "/previsoes", label: "Previsões", Icon: IconTarget },
  { href: "/ia", label: "IA Insights", Icon: IconSpark },
  { href: "/qualidade", label: "Qualidade dos Dados", Icon: IconDatabase },
];

/** Símbolo próprio do projeto: três barras subindo num quadrado amarelo. */
function BrandMark({ size = 38 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 42 42" aria-hidden="true" focusable="false">
      <rect width="42" height="42" rx="12" fill="#FFE14D" />
      <rect x="9" y="22" width="6" height="11" rx="2" fill="#1B2696" />
      <rect x="18" y="15" width="6" height="18" rx="2" fill="#2B3FD6" />
      <rect x="27" y="9" width="6" height="24" rx="2" fill="#1B2696" />
    </svg>
  );
}

export function Sidebar() {
  const path = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem("bbi-sidebar") === "collapsed");
    } catch { /* armazenamento indisponível */ }
  }, []);
  useEffect(() => setOpen(false), [path]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    try { localStorage.setItem("bbi-sidebar", next ? "collapsed" : "expanded"); } catch { /* ok */ }
  };

  return (
    <>
      <nav className="bottomnav" aria-label="Navegação rápida">
        {NAV.slice(0, 4).map(({ href, label, Icon }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <Link key={href} href={href} className={`bn-item${active ? " is-active" : ""}`} aria-current={active ? "page" : undefined}>
              <Icon /><span>{label.split(" ")[0]}</span>
            </Link>
          );
        })}
        <button className="bn-item" onClick={() => setOpen(true)} aria-label="Mais seções" aria-expanded={open}>
          <IconMenu /><span>Mais</span>
        </button>
      </nav>
      <div className="mobilebar">
        <button className="iconbtn" onClick={() => setOpen(true)} aria-label="Abrir menu" aria-expanded={open}
                aria-controls="sidebar">
          <IconMenu />
        </button>
        <BrandMark size={30} />
        <span className="brand-text"><strong>BB</strong> Intelligence</span>
      </div>
      {open && <div className="scrim" onClick={() => setOpen(false)} aria-hidden="true" />}
      <aside id="sidebar" className={`sidebar${collapsed ? " is-collapsed" : ""}${open ? " is-open" : ""}`}
             aria-label="Navegação principal">
        <div className="sidebar-top">
          <Link href="/" className="brand" aria-label="BB Intelligence — início">
            <span className="brand-mark" aria-hidden="true"><BrandMark /></span>
            <span className="brand-text"><strong>BB</strong> Intelligence</span>
          </Link>
          <button className="iconbtn only-mobile" onClick={() => setOpen(false)} aria-label="Fechar menu">
            <IconClose />
          </button>
        </div>
        <nav>
          <ul>
            {NAV.map(({ href, label, Icon }) => {
              const active = href === "/" ? path === "/" : path.startsWith(href);
              return (
                <li key={href}>
                  <Link href={href} className={`navlink${active ? " is-active" : ""}`}
                        aria-current={active ? "page" : undefined} title={collapsed ? label : undefined}>
                    <Icon />
                    <span className="navlabel">{label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="sidebar-foot">
          <p className="sidebar-note">Projeto independente, não oficial e não afiliado ao Banco do Brasil. Dados com atualização diária, não em tempo real.</p>
          <button className="collapse-btn" onClick={toggle} aria-pressed={collapsed}
                  aria-label={collapsed ? "Expandir menu" : "Recolher menu"}>
            <IconChevronLeft className="collapse-icon" />
            <span className="navlabel">Recolher menu</span>
          </button>
        </div>
      </aside>
    </>
  );
}
