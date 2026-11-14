"""Regras de validação aplicadas antes de gravar qualquer observação."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from math import isfinite

from .periods import quarter_of


@dataclass
class Issue:
    severity: str  # error | warning
    rule: str
    message: str


def check_finite(values: list[float], label: str) -> list[Issue]:
    bad = [v for v in values if v is None or not isfinite(v)]
    return [Issue("error", "finite", f"{label}: {len(bad)} valores não numéricos")] if bad else []


def check_no_duplicates(keys: list[tuple], label: str) -> list[Issue]:
    seen, dups = set(), set()
    for k in keys:
        (dups if k in seen else seen).add(k)
    return [Issue("error", "duplicates", f"{label}: chaves duplicadas {sorted(dups)[:5]}")] if dups else []


def check_quarter_sum(quarters: dict[date, float], ytd: dict[date, float], label: str,
                      rel_tol: float = 0.005) -> list[Issue]:
    """Soma dos trimestres isolados do ano deve bater com o acumulado (YTD) do ITR."""
    issues: list[Issue] = []
    by_year: dict[int, dict[int, float]] = defaultdict(dict)
    for end, v in quarters.items():
        by_year[end.year][quarter_of(end)] = v
    for end, ytd_v in ytd.items():
        q = quarter_of(end)
        qs = by_year[end.year]
        if all(i in qs for i in range(1, q + 1)):
            total = sum(qs[i] for i in range(1, q + 1))
            if abs(total - ytd_v) > rel_tol * max(abs(ytd_v), 1.0):
                issues.append(Issue("error", "quarter_sum",
                                    f"{label} {end}: soma trimestres {total:,.0f} ≠ YTD {ytd_v:,.0f}"))
        else:
            issues.append(Issue("warning", "quarter_sum",
                                f"{label} {end}: trimestres incompletos, soma não verificada"))
    return issues


def check_gaps(period_ends: list[date], label: str) -> list[Issue]:
    """Aponta trimestres faltantes numa série trimestral."""
    if len(period_ends) < 2:
        return []
    idx = sorted({d.year * 4 + quarter_of(d) - 1 for d in period_ends})
    missing = [i for i in range(idx[0], idx[-1] + 1) if i not in set(idx)]
    return [Issue("warning", "gaps", f"{label}: faltam {[f'{i // 4}Q{i % 4 + 1}' for i in missing]}")] if missing else []


def has_errors(issues: list[Issue]) -> bool:
    return any(i.severity == "error" for i in issues)
