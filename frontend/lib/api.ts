import type { Envelope } from "./types";

const BASE = (process.env.BB_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export type ApiResult<T> =
  | { ok: true; data: T; meta: Envelope<T>["meta"] }
  | { ok: false; error: string; status?: number };

/** Busca na API. Nunca lança: a página decide como mostrar o erro. */
export async function api<T>(path: string): Promise<ApiResult<T>> {
  try {
    const res = await fetch(`${BASE}/api/v1${path}`, {
      next: { revalidate: 300 },
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(45_000), // a API gratuita pode estar "acordando"
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) {
      const msg = body?.error?.message ?? `Erro ${res.status} ao consultar a API`;
      return { ok: false, error: msg, status: res.status };
    }
    return { ok: true, data: body.data as T, meta: body.meta };
  } catch (e) {
    const reason = e instanceof Error && e.name === "TimeoutError" ? "tempo esgotado" : "sem conexão";
    return { ok: false, error: `Não foi possível falar com a API (${reason}).` };
  }
}
