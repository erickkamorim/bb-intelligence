import { IconAlert, IconClock, IconInfo } from "./Icons";

export function ErrorState({ title = "Não foi possível carregar", message }: { title?: string; message: string }) {
  return (
    <div className="state state-error" role="alert">
      <IconAlert />
      <div><strong>{title}</strong><p>{message}</p></div>
    </div>
  );
}

export function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="state state-empty">
      <IconInfo />
      <div><strong>{title}</strong><p>{message}</p></div>
    </div>
  );
}

/** Rótulo de status sempre com ícone + texto (nunca só cor). */
export function StatusBadge({ status }: { status: "ok" | "missing" | "stale" }) {
  const map = {
    ok: { label: "Atualizado", cls: "badge-ok", Icon: IconInfo },
    stale: { label: "Desatualizado", cls: "badge-warn", Icon: IconClock },
    missing: { label: "Indisponível", cls: "badge-missing", Icon: IconAlert },
  } as const;
  const { label, cls, Icon } = map[status];
  return <span className={`badge ${cls}`}><Icon width={14} height={14} />{label}</span>;
}
