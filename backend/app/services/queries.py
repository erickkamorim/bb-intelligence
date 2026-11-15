"""Consultas da API. Regras:
- Sempre a última revisão de cada observação.
- Nenhum valor é inventado: ausência vira status "missing", nunca zero.
- Valores calculados aqui (variações, IPCA 12m, "outros") vêm marcados como derivados.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Document, EtlRun, IndicatorModel, Observation, Source
from etl.periods import parse_period_code, period_code, quarter_end, quarter_of
from etl.registry import INDICATORS

# Atraso máximo aceitável antes de um indicador ser marcado como desatualizado
STALE_AFTER_DAYS = {"quarterly": 150, "monthly": 60, "daily": 7}


@dataclass
class Obs:
    indicator: IndicatorModel
    obs: Observation
    document: Document
    source: Source


def _latest_revisions(rows: list[tuple[Observation, Document, Source]]) -> list[tuple[Observation, Document, Source]]:
    best: dict[tuple, tuple[Observation, Document, Source]] = {}
    for o, d, s in rows:
        key = (o.period_start, o.period_end, o.period_type, o.entity_scope)
        if key not in best or o.revision > best[key][0].revision:
            best[key] = (o, d, s)
    return sorted(best.values(), key=lambda t: (t[0].period_end, t[0].period_type))


def indicator_by_code(db: Session, code: str) -> IndicatorModel | None:
    return db.scalar(select(IndicatorModel).where(IndicatorModel.code == code))


def observations(db: Session, ind: IndicatorModel, period_type: str | None = None,
                 start: date | None = None, end: date | None = None) -> list[tuple[Observation, Document, Source]]:
    q = (select(Observation, Document, Source)
         .join(Document, Observation.source_document_id == Document.id)
         .join(Source, Document.source_id == Source.id)
         .where(Observation.indicator_id == ind.id))
    if period_type:
        q = q.where(Observation.period_type == period_type)
    if start:
        q = q.where(Observation.period_end >= start)
    if end:
        q = q.where(Observation.period_end <= end)
    return _latest_revisions(list(db.execute(q).all()))


def source_meta(o: Observation, d: Document, s: Source) -> dict:
    return {
        "source": s.name,
        "source_code": s.code,
        "url": d.url,
        "locator": d.locator,
        "document_type": d.document_type,
        "published_at": (o.published_at or d.published_at),
        "retrieved_at": o.retrieved_at,
        "revision": o.revision,
        "derivation": o.derivation,
    }


def available_periods(db: Session) -> list[dict]:
    q = select(Observation.period_end).where(Observation.period_type.in_(["quarter", "instant"])).distinct()
    ends = sorted({e for (e,) in db.execute(q) if e == quarter_end(e.year, quarter_of(e))}, reverse=True)
    return [{"code": period_code(e), "end": e, "label": f"{quarter_of(e)}T{str(e.year)[2:]}"} for e in ends]


def _shift_quarters(end: date, n: int) -> date:
    idx = end.year * 4 + quarter_of(end) - 1 - n
    return quarter_end(idx // 4, idx % 4 + 1)


def _value_at(rows, end: date, period_type: str):
    for o, d, s in rows:
        if o.period_end == end and o.period_type == period_type:
            return o, d, s
    return None


def _delta(cur: float, prev: float | None, unit: str) -> dict | None:
    if prev is None:
        return None
    if unit.startswith("pct"):
        return {"value": round(cur - prev, 4), "unit": "p.p."}
    if prev == 0:
        return None
    return {"value": round((cur / prev - 1) * 100, 4), "unit": "%"}


def indicator_snapshot(db: Session, period: str) -> list[dict]:
    """Valor de cada indicador no período, com variação t/t e a/a."""
    _, end = parse_period_code(period)
    out = []
    for code, meta in INDICATORS.items():
        ind = indicator_by_code(db, code)
        item = {"code": code, "name": meta.name, "unit": meta.unit, "scope": meta.scope,
                "frequency": meta.frequency, "definition": meta.definition, "period": period}
        if ind is None:
            out.append({**item, "status": "missing"})
            continue
        if meta.frequency == "quarterly":
            ptype = "instant" if (meta.cvm and meta.cvm.statement in {"BPA", "BPP"}) else "quarter"
            rows = observations(db, ind, period_type=ptype)
            hit = _value_at(rows, end, ptype)
            if hit is None:
                out.append({**item, "status": "missing"})
                continue
            o, d, s = hit
            cur = float(o.value)
            prev_q = _value_at(rows, _shift_quarters(end, 1), ptype)
            prev_y = _value_at(rows, _shift_quarters(end, 4), ptype)
            out.append({**item, "status": "ok", "value": cur, "as_of": o.period_end,
                        "qoq": _delta(cur, float(prev_q[0].value) if prev_q else None, meta.unit),
                        "yoy": _delta(cur, float(prev_y[0].value) if prev_y else None, meta.unit),
                        **source_meta(o, d, s)})
        else:
            out.append({**item, **macro_at(db, ind, code, end)})
    return out


def macro_at(db: Session, ind: IndicatorModel, code: str, end: date) -> dict:
    """Último valor disponível até o fim do período (e nunca depois de hoje)."""
    cutoff = min(end, date.today())
    rows = observations(db, ind, end=cutoff, start=cutoff - timedelta(days=400))
    if not rows:
        return {"status": "missing"}
    o, d, s = rows[-1]
    res = {"status": "ok", "value": float(o.value), "as_of": o.period_end, **source_meta(o, d, s)}
    if code == "ipca_mensal":
        last12 = [r for r in rows if r[0].period_end > _month_back(o.period_end, 12)]
        if len(last12) == 12:
            acc = 1.0
            for r in last12:
                acc *= 1 + float(r[0].value) / 100
            res["ipca_12m"] = {"value": round((acc - 1) * 100, 4), "unit": "pct",
                               "derivation": "derived:product_of_12_monthly"}
    return res


def _month_back(d: date, n: int) -> date:
    m = d.year * 12 + d.month - 1 - n
    return date(m // 12, m % 12 + 1, 1)


def credit_segments(db: Session, period: str) -> dict:
    _, end = parse_period_code(period)
    segs = {"carteira_pf": "Pessoas Físicas", "carteira_pj": "Pessoas Jurídicas", "carteira_agro": "Agronegócio"}
    total_ind = indicator_by_code(db, "carteira_credito_ampliada")
    total_hit = _value_at(observations(db, total_ind, "quarter"), end, "quarter") if total_ind else None
    if total_hit is None:
        return {"status": "missing", "period": period}
    total = float(total_hit[0].value)
    items, summed = [], 0.0
    for code, label in segs.items():
        ind = indicator_by_code(db, code)
        hit = _value_at(observations(db, ind, "quarter"), end, "quarter") if ind else None
        if hit is None:
            items.append({"code": code, "label": label, "status": "missing"})
            continue
        v = float(hit[0].value)
        summed += v
        items.append({"code": code, "label": label, "status": "ok", "value": v,
                      "share_pct": round(v / total * 100, 2), **source_meta(*hit)})
    if all(i["status"] == "ok" for i in items):
        rest = total - summed
        items.append({"code": "outros", "label": "Outros (exterior)", "status": "ok", "value": rest,
                      "share_pct": round(rest / total * 100, 2),
                      "derivation": "derived:total_minus_segments"})
    return {"status": "ok", "period": period, "unit": "BRL", "total": total,
            "total_source": source_meta(*total_hit), "segments": items}


def data_quality(db: Session) -> dict:
    today = date.today()
    inds = []
    for code, meta in INDICATORS.items():
        ind = indicator_by_code(db, code)
        row = None
        if ind is not None:
            row = db.execute(select(func.count(Observation.id), func.min(Observation.period_end),
                                    func.max(Observation.period_end), func.max(Observation.retrieved_at))
                             .where(Observation.indicator_id == ind.id,
                                    Observation.period_end <= today)).one()
        n, first, last, retrieved = row if row else (0, None, None, None)
        if not n:
            status = "missing"
        elif (today - last).days > STALE_AFTER_DAYS.get(meta.frequency, 150):
            status = "stale"
        else:
            status = "ok"
        inds.append({"code": code, "name": meta.name, "source": meta.source, "frequency": meta.frequency,
                     "observations": n, "first_period": first, "last_period": last,
                     "last_retrieved_at": retrieved, "status": status})
    runs = db.scalars(select(EtlRun).order_by(EtlRun.id.desc()).limit(20)).all()
    return {
        "indicators": inds,
        "summary": {s: sum(1 for i in inds if i["status"] == s) for s in ("ok", "stale", "missing")},
        "runs": [{"id": r.id, "job": r.job_name, "status": r.status, "started_at": r.started_at,
                  "ended_at": r.ended_at, "rows_inserted": r.rows_inserted, "rows_updated": r.rows_updated,
                  "error": r.error_message} for r in runs],
        "checked_at": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------- ponte do lucro
BRIDGE = [
    ("margem_financeira_bruta", "Margem financeira"),
    ("custo_credito", "Custo do crédito"),
    ("receitas_servicos", "Serviços"),
    ("despesas_administrativas", "Despesas adm."),
    ("outras_receitas_despesas_op", "Outras operacionais"),
    ("provisoes", "Provisões"),
    ("resultado_nao_operacional", "Não operacional"),
    ("ir_csll", "IR/CSLL"),
    ("participacoes_estatutarias", "Part. estatutárias"),
    ("participacoes_minoritarias", "Minoritários"),
]


def _quarter_values(db: Session, code: str) -> dict[date, tuple]:
    ind = indicator_by_code(db, code)
    if ind is None:
        return {}
    return {o.period_end: (float(o.value), o, d, s) for o, d, s in observations(db, ind, period_type="quarter")}


def profit_bridge(db: Session, period: str) -> dict:
    """Do lucro ajustado do trimestre comparável anterior ao atual, linha a linha da DRE gerencial."""
    _, end = parse_period_code(period)
    profit = _quarter_values(db, "lucro_liquido_ajustado")
    comps = {c: _quarter_values(db, c) for c, _ in BRIDGE}
    complete = sorted(e for e in profit if all(e in comps[c] for c, _ in BRIDGE))
    if end not in complete:
        return {"status": "missing", "period": period,
                "reason": "Componentes da DRE gerencial não carregados para este trimestre."}
    prevs = [e for e in complete if e < end]
    if not prevs:
        return {"status": "missing", "period": period, "reason": "Sem trimestre anterior comparável."}
    prev = prevs[-1]
    steps = [{"code": c, "label": lbl, "delta": comps[c][end][0] - comps[c][prev][0]} for c, lbl in BRIDGE]
    start_v, end_v = profit[prev][0], profit[end][0]
    residual = end_v - start_v - sum(st["delta"] for st in steps)
    _, o, d, s = profit[end]
    return {"status": "ok", "period": period, "from_period": period_code(prev), "from_end": prev,
            "start": start_v, "end": end_v, "steps": sorted(steps, key=lambda st: st["delta"]),
            "residual": residual, "unit": "BRL", "closes": abs(residual) <= 5e6, "source": source_meta(o, d, s)}


# ---------------------------------------------------------------- alertas
# polaridade: True = subir é bom; False = subir é ruim. Linhas de custo (negativas) comparam o tamanho.
POLARITY = {
    "lucro_liquido_ajustado": True, "roe_ajustado": True, "indice_eficiencia": False, "inad_90": False,
    "cobertura_90": True, "carteira_credito_ampliada": True, "carteira_pf": True, "carteira_pj": True,
    "carteira_agro": True, "margem_financeira_bruta": True, "receitas_servicos": True,
    "custo_credito": False, "despesas_administrativas": False, "lucro_liquido_contabil": True,
}
COST = {"custo_credito", "despesas_administrativas"}
THRESH_PCT = 8.0   # variação relativa mínima para valores em R$
THRESH_PP = 0.3    # variação mínima em p.p. para taxas


def alerts(db: Session, period: str) -> list[dict]:
    _, end = parse_period_code(period)
    prev_q, prev_y = _shift_quarters(end, 1), _shift_quarters(end, 4)
    out = []
    for code, up_good in POLARITY.items():
        vals = _quarter_values(db, code)
        if end not in vals:
            continue
        meta = INDICATORS[code]
        cur, o, d, s = vals[end]
        hist = [abs(v) if code in COST else v for e, (v, *_rest) in vals.items() if e <= end]
        cur_cmp = abs(cur) if code in COST else cur
        for ref, label in ((prev_q, "t/t"), (prev_y, "a/a")):
            if ref not in vals:
                continue
            base = vals[ref][0]
            if meta.unit.startswith("pct"):
                delta, unit, big = cur - base, "p.p.", abs(cur - base) >= THRESH_PP
            else:
                a, b = (abs(cur), abs(base)) if code in COST else (cur, base)
                if b == 0:
                    continue
                delta, unit = (a / b - 1) * 100, "%"
                big = abs(delta) >= THRESH_PCT
            if not big:
                continue
            rising = delta > 0
            good = rising == up_good
            extreme = None
            if len(hist) >= 3:
                noun = "maior custo" if code in COST else "maior valor"
                if cur_cmp == max(hist):
                    extreme = f"{noun} da série carregada"
                elif cur_cmp == min(hist):
                    extreme = ("menor custo" if code in COST else "menor valor") + " da série carregada"
            out.append({"code": code, "name": meta.name, "unit": meta.unit, "value": cur, "compare": label,
                        "compare_period": period_code(ref), "delta": round(delta, 2), "delta_unit": unit,
                        "direction": "up" if rising else "down", "tone": "positive" if good else "negative",
                        "extreme": extreme, **source_meta(o, d, s)})
            break  # um alerta por indicador: t/t tem prioridade
    order = {"negative": 0, "positive": 1}
    return sorted(out, key=lambda a: (order[a["tone"]], -abs(a["delta"]) if a["delta_unit"] == "%" else -abs(a["delta"]) * 20))


# ---------------------------------------------------------------- notas do release
def release_notes(period: str) -> list[dict]:
    import csv
    from pathlib import Path

    # Fica dentro do backend: o Render publica só a pasta backend/
    path = Path(__file__).resolve().parents[1] / "data" / "ri_notes.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r["period"].upper() == period.upper()]
