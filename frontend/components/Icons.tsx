import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement>;
const base = (p: P) => ({
  width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
  strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const,
  "aria-hidden": true, focusable: false, ...p,
});

export const IconGrid = (p: P) => (<svg {...base(p)}><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>);
export const IconBars = (p: P) => (<svg {...base(p)}><path d="M5 20V11M12 20V5M19 20v-7"/></svg>);
export const IconShield = (p: P) => (<svg {...base(p)}><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/></svg>);
export const IconTrend = (p: P) => (<svg {...base(p)}><path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/></svg>);
export const IconTarget = (p: P) => (<svg {...base(p)}><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><path d="M12 2v3M22 12h-3"/></svg>);
export const IconSpark = (p: P) => (<svg {...base(p)}><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 17l.8 2 .2.2 2 .8-2 .8-.2.2-.8 2-.8-2-.2-.2-2-.8 2-.8.2-.2z"/></svg>);
export const IconDatabase = (p: P) => (<svg {...base(p)}><ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6"/><path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/></svg>);
export const IconCoins = (p: P) => (<svg {...base(p)}><ellipse cx="9" cy="7" rx="6" ry="3"/><path d="M3 7v5c0 1.7 2.7 3 6 3s6-1.3 6-3V7"/><path d="M9 15v2c0 1.7 2.7 3 6 3s6-1.3 6-3v-5c0-1.7-2.7-3-6-3"/></svg>);
export const IconCard = (p: P) => (<svg {...base(p)}><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h4"/></svg>);
export const IconGauge = (p: P) => (<svg {...base(p)}><path d="M4 18a8 8 0 1 1 16 0"/><path d="M12 18l4-6"/></svg>);
export const IconPie = (p: P) => (<svg {...base(p)}><path d="M12 3v9h9"/><path d="M20.5 15A9 9 0 1 1 9 3.5"/></svg>);
export const IconDoc = (p: P) => (<svg {...base(p)}><path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/></svg>);
export const IconCalendar = (p: P) => (<svg {...base(p)}><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>);
export const IconChevronLeft = (p: P) => (<svg {...base(p)}><path d="M15 6l-6 6 6 6"/></svg>);
export const IconMenu = (p: P) => (<svg {...base(p)}><path d="M4 7h16M4 12h16M4 17h16"/></svg>);
export const IconClose = (p: P) => (<svg {...base(p)}><path d="M6 6l12 12M18 6L6 18"/></svg>);
export const IconDownload = (p: P) => (<svg {...base(p)}><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg>);
export const IconInfo = (p: P) => (<svg {...base(p)}><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>);
export const IconAlert = (p: P) => (<svg {...base(p)}><path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17h.01"/></svg>);
export const IconCheck = (p: P) => (<svg {...base(p)}><circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/></svg>);
export const IconClock = (p: P) => (<svg {...base(p)}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>);
export const IconArrowUp = (p: P) => (<svg {...base(p)} width={14} height={14}><path d="M12 19V5M6 11l6-6 6 6"/></svg>);
export const IconArrowDown = (p: P) => (<svg {...base(p)} width={14} height={14}><path d="M12 5v14M6 13l6 6 6-6"/></svg>);
export const IconScale = (p: P) => (<svg {...base(p)}><path d="M12 4v16M5 20h14M6 8h12"/><path d="M6 8l-3 6a3 3 0 0 0 6 0zM18 8l-3 6a3 3 0 0 0 6 0z"/></svg>);
