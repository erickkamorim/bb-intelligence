"""CLI do ETL.  Uso: python -m etl.cli <comando> --help

Comandos:
  seed                         cadastra fontes e dicionário de indicadores
  cvm inspect --doc ITR --year 2026 [--statement DRE]
                               baixa o ZIP e lista as contas do BB (confirmação manual de códigos)
  cvm load --doc ITR --year 2026 [--allow-unconfirmed]
  sgs load --indicator selic_meta --start 2016-01-01 [--end 2026-11-14]
  ri load --file ../data/manual/ri_bb.csv
  quality                      cobertura por indicador e últimas execuções
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone

from app.core.config import settings

from . import cvm, ri_manual, sgs, storage, validation
from .periods import PeriodType, period_code
from .registry import INDICATORS


def _session():
    from app.db.session import SessionLocal
    return SessionLocal()


def _requests_session():
    import requests
    s = requests.Session()
    s.headers["User-Agent"] = settings.user_agent
    return s


def cmd_seed(_args) -> int:
    from .load import seed
    with _session() as s:
        seed(s)
        s.commit()
    print(f"OK: {len(INDICATORS)} indicadores sincronizados")
    return 0


def _download_cvm(doc: str, year: int) -> storage.RawFile:
    url = cvm.zip_url(doc, year)
    raw = storage.download(url, settings.raw_dir, f"cvm_{doc.lower()}", _requests_session(), settings.http_timeout)
    print(f"{'reaproveitado' if raw.reused else 'baixado'}: {raw.path} sha256={raw.sha256[:12]}…")
    return raw


def cmd_cvm_inspect(args) -> int:
    raw = _download_cvm(args.doc, args.year)
    df = cvm.normalize(cvm.read_statement(raw.path, args.statement))
    if df.empty:
        print("Nenhuma linha do BB encontrada — conferir CNPJ e ano.")
        return 1
    with __import__("pandas").option_context("display.max_rows", 500, "display.width", 200):
        print(cvm.list_accounts(df, args.level).to_string(index=False))
    return 0


def cmd_cvm_load(args) -> int:
    from .load import ObsIn, etl_run, get_or_create_document, upsert_observations

    raw = _download_cvm(args.doc, args.year)
    targets = [i for i in INDICATORS.values() if i.cvm is not None
               and (i.cvm.confirmed or args.allow_unconfirmed) and i.cvm.cd_conta]
    skipped = [i.code for i in INDICATORS.values() if i.cvm is not None and i not in targets]
    if skipped:
        print(f"AVISO: mapeamentos não confirmados ignorados: {skipped}")

    by_stmt: dict[str, list] = {}
    for ind in targets:
        by_stmt.setdefault(ind.cvm.statement, []).append(ind)

    rows: list[ObsIn] = []
    issues: list[validation.Issue] = []
    for stmt, inds in by_stmt.items():
        df = cvm.normalize(cvm.read_statement(raw.path, stmt))
        for ind in inds:
            obs = cvm.extract(df, ind, allow_unconfirmed=args.allow_unconfirmed)
            issues += validation.check_finite([o.value for o in obs], ind.code)
            issues += validation.check_no_duplicates(
                [(o.period_start, o.period_end, o.period_type) for o in obs], ind.code)
            q = {o.period_end: o.value for o in obs if o.period_type == PeriodType.QUARTER.value}
            ytd = {o.period_end: o.value for o in obs if o.period_type == PeriodType.YTD.value}
            issues += validation.check_quarter_sum(q, ytd, ind.code)
            rows += [ObsIn(ind.code, o.period_start, o.period_end, o.period_type, o.value,
                           extra={"cd_conta": o.cd_conta, "ds_conta": o.ds_conta, "versao": o.version,
                                  "arquivo": o.member}) for o in obs]
    for i in issues:
        print(f"[{i.severity}] {i.rule}: {i.message}")
    if validation.has_errors(issues):
        print("Carga abortada por erros de validação.")
        return 2

    with _session() as s, etl_run(s, f"cvm_{args.doc.lower()}_{args.year}") as run:
        doc = get_or_create_document(s, f"cvm_{args.doc.lower()}", args.doc.upper(), raw.url, raw.sha256,
                                     raw.retrieved_at, period=str(args.year))
        ins, rev = upsert_observations(s, doc, rows)
        run.rows_inserted, run.rows_updated = ins, rev
        run.details = {"warnings": [i.message for i in issues], "skipped": skipped}
        s.commit()
    print(f"OK: {ins} inseridas, {rev} revisadas")
    return 0


def cmd_sgs_load(args) -> int:
    import hashlib
    import json

    from .load import ObsIn, etl_run, get_or_create_document, upsert_observations

    ind = INDICATORS[args.indicator]
    if ind.sgs_code is None:
        print(f"{ind.code} não é série SGS")
        return 1
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end) if args.end else date.today()
    pts = sgs.fetch(ind.sgs_code, start, end, _requests_session())
    if not pts:
        print("Nenhum dado retornado na janela.")
        return 1
    issues = validation.check_finite([p.value for p in pts], ind.code)
    if validation.has_errors(issues):
        print(issues)
        return 2
    payload = json.dumps([[p.date.isoformat(), p.value] for p in pts]).encode()
    digest = hashlib.sha256(payload).hexdigest()
    url = f"{sgs.BASE.format(code=ind.sgs_code)}?formato=json"  # janelas exatas ficam em `period`
    now = datetime.now(timezone.utc)
    with _session() as s, etl_run(s, f"sgs_{ind.code}") as run:
        doc = get_or_create_document(s, "bcb_sgs", "SGS", url, digest, now, period=f"{start}..{end}")
        rows = [ObsIn(ind.code, None, p.date, ind.sgs_period_type or "daily", p.value) for p in pts]
        ins, rev = upsert_observations(s, doc, rows)
        run.rows_inserted, run.rows_updated = ins, rev
        s.commit()
    print(f"OK {ind.code}: {len(pts)} pontos ({pts[0].date} a {pts[-1].date}); {ins} inseridos, {rev} revisados")
    return 0


def cmd_ri_load(args) -> int:
    import hashlib

    from .load import ObsIn, etl_run, get_or_create_document, upsert_observations

    obs = ri_manual.load_csv(args.file)
    now = datetime.now(timezone.utc)
    with _session() as s, etl_run(s, "ri_manual") as run:
        total_i = total_r = 0
        for o in obs:
            key = f"{o.source_url}#{o.source_locator}"
            doc = get_or_create_document(
                s, "ri_bb", "RI_RELEASE", o.source_url, hashlib.sha256(key.encode()).hexdigest(), now,
                period=period_code(o.period_end),
                published_at=datetime.combine(o.published_at, datetime.min.time(), timezone.utc),
                locator=o.source_locator)
            i, r = upsert_observations(s, doc, [ObsIn(o.indicator_code, o.period_start, o.period_end, "quarter",
                                                      o.value, extra={"collected_by": o.collected_by})])
            total_i, total_r = total_i + i, total_r + r
        run.rows_inserted, run.rows_updated = total_i, total_r
        s.commit()
    print(f"OK: {total_i} inseridas, {total_r} revisadas")
    return 0


def cmd_quality(_args) -> int:
    from sqlalchemy import select

    from app.db.models import EtlRun
    from .load import coverage
    with _session() as s:
        print("Cobertura por indicador:")
        for c in coverage(s):
            status = "SEM DADOS" if c["n"] == 0 else f"{c['n']:>5} obs  {c['first']} → {c['last']}"
            print(f"  {c['indicator']:<30} {status}")
        print("\nÚltimas execuções:")
        for r in s.scalars(select(EtlRun).order_by(EtlRun.id.desc()).limit(10)):
            print(f"  #{r.id} {r.job_name:<22} {r.status:<8} +{r.rows_inserted} ~{r.rows_updated} "
                  f"{r.error_message or ''}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="etl", description="ETL BB Intelligence — Etapa 1")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed").set_defaults(func=cmd_seed)

    c = sub.add_parser("cvm").add_subparsers(dest="sub", required=True)
    ci = c.add_parser("inspect")
    ci.add_argument("--doc", choices=["ITR", "DFP"], default="ITR")
    ci.add_argument("--year", type=int, required=True)
    ci.add_argument("--statement", choices=["DRE", "BPA", "BPP", "DFC_MI", "DMPL", "DVA"], default="DRE")
    ci.add_argument("--level", type=int, default=2)
    ci.set_defaults(func=cmd_cvm_inspect)
    cl = c.add_parser("load")
    cl.add_argument("--doc", choices=["ITR", "DFP"], default="ITR")
    cl.add_argument("--year", type=int, required=True)
    cl.add_argument("--allow-unconfirmed", action="store_true",
                    help="somente para desenvolvimento: carrega mapeamentos ainda não confirmados")
    cl.set_defaults(func=cmd_cvm_load)

    g = sub.add_parser("sgs").add_subparsers(dest="sub", required=True)
    gl = g.add_parser("load")
    gl.add_argument("--indicator", choices=[k for k, v in INDICATORS.items() if v.sgs_code], required=True)
    gl.add_argument("--start", required=True)
    gl.add_argument("--end")
    gl.set_defaults(func=cmd_sgs_load)

    r = sub.add_parser("ri").add_subparsers(dest="sub", required=True)
    rl = r.add_parser("load")
    rl.add_argument("--file", required=True)
    rl.set_defaults(func=cmd_ri_load)

    sub.add_parser("quality").set_defaults(func=cmd_quality)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
