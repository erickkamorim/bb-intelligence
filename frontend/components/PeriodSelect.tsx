"use client";

import { usePathname, useRouter } from "next/navigation";
import { useTransition } from "react";
import type { PeriodItem } from "@/lib/types";
import { IconCalendar } from "./Icons";

export function PeriodSelect({ periods, value }: { periods: PeriodItem[]; value: string }) {
  const router = useRouter();
  const path = usePathname();
  const [pending, start] = useTransition();
  return (
    <label className="period-select">
      <IconCalendar />
      <span className="period-label">Período de referência</span>
      <select value={value} aria-busy={pending}
              onChange={(e) => start(() => router.push(`${path}?period=${e.target.value}`))}>
        {periods.map((p) => <option key={p.code} value={p.code}>{p.label}</option>)}
      </select>
      {pending && <span className="spinner" role="status" aria-label="Carregando" />}
    </label>
  );
}
