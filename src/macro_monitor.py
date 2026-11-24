"""
MX Macro Monitor - weekly pipeline.

    python src/macro_monitor.py              # fetch APIs, build everything
    python src/macro_monitor.py --offline    # rebuild from data/raw (no tokens needed)
    python src/macro_monitor.py --date 2026-11-30 --offline   # simulate a run date

Outputs (bulletins/):
    carousel_es.pdf, carousel_en.pdf   LinkedIn document posts (6 pages, 4:5, magazine design v5)
    cover_es.png, cover_en.png         cover previews
    linkedin_post.md                   post copy (ES) + first comment (EN) + checklist
    latest_es.md, latest_en.md         one-page bulletins for GitHub
    archive/YYYY-MM-DD_es.md           weekly archive
data/: raw/*.csv (API cache), latest.json (snapshot), history.csv (one row per run)

Author: Isaac Tienda
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

import agenda as agenda_mod  # noqa: E402
import analytics
import magazine
import valueadd
import narrative
from config import AUTHOR, CRITICAL, DATA_DIR, OUTPUT_DIR, REPO_URL, SERIES
from narrative import SIGNAL_LABEL, day_year, month, n, signed
from sources import fetch_all, fetch_peers

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("macro_monitor")
logging.getLogger("fontTools").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
TZ = ZoneInfo("America/Mexico_City")


# --- Markdown bulletin ---------------------------------------------------------------
def bulletin_md(s: dict, t: dict, lang: str, warnings: list) -> str:
    tl, es = t[lang], lang == "es"
    i, e, p, f, a = s["inflation"], s.get("expectations") or {}, s["policy"], s["fx"], s.get("activity")
    sig = lambda k: SIGNAL_LABEL[lang][k]  # noqa: E731
    rows = [
        ("Inflación general (% anual)" if es else "Headline inflation (% y/y)", n(i["yoy"]), f"{signed(i['delta_pp'])} pp", month(i["period"], lang), sig(i["signal"])),
        ("Inflación subyacente (% anual)" if es else "Core inflation (% y/y)", n(i.get("core")), f"{signed(i.get('core_delta_pp'))} pp", month(i["period"], lang), "—"),
        ("Expectativa de inflación 12m (mediana)" if es else "12m inflation expectation (median)", n(e.get("exp_12m")),
         f"{signed((e.get('exp_12m') or 0) - (e.get('exp_12m_prev') or 0))} pp", month(e["period"], lang) if e else "N/D", "—"),
        ("Tasa objetivo Banxico (%)" if es else "Banxico policy rate (%)", n(p["rate"]), f"{signed(p['chg_12m_bp'],0)} {'pb' if es else 'bp'} 12m", day_year(p["date"], lang), "—"),
        ("Tasa real ex ante (%)" if es else "Ex-ante real rate (%)", n(p.get("real_ex_ante")), "—", month(e["period"], lang) if e else "N/D", "—"),
        ("Diferencial Banxico–Fed (pb)" if es else "Banxico–Fed spread (bp)", n(p.get("spread_bp"), 0),
         f"{signed((p.get('spread_bp') or 0) - (p.get('spread_12m_ago_bp') or 0), 0)} 12m", day_year(p["date"], lang), "—"),
        ("Tipo de cambio FIX (MXN/USD)" if es else "USD/MXN FIX", n(f["value"], 4), f"{signed(f['chg_1w_pct'])}% {'sem.' if es else 'w/w'}", day_year(f["date"], lang), sig(f["signal"])),
    ]
    if a:
        rows.append(("IGAE a.e. (% mensual)" if es else "IGAE s.a. (% m/m)", signed(a["mom"], 1), f"{signed(a['yoy'],1)}% {'anual' if es else 'y/y'}", month(a["period"], lang), sig(a["signal"])))
    hdr = ("| Indicador | Último | Cambio | Periodo | Señal |" if es else "| Indicator | Latest | Change | Period | Signal |")
    lines = [
        f"# {'MX Macro Monitor · Semana' if es else 'MX Macro Monitor · Week'} {date.fromisoformat(s['run_date']).isocalendar()[1]}",
        f"**{'Datos al' if es else 'Data as of'}** {day_year(s['run_date'], lang)} · **{'Autor' if es else 'Author'}:** {AUTHOR} · "
        f"**{'Fuentes' if es else 'Sources'}:** Banxico (SIE), INEGI (BIE), {'Reserva Federal' if es else 'Federal Reserve'} (FRED)",
        "", f"## {tl['headline']}", "", hdr, "| :--- | ---: | ---: | :---: | :--- |",
    ]
    lines += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |" for r in rows]
    for k in tl["order"]:
        b = tl["blocks"].get(k)
        if not b:
            continue
        lines += ["", f"### {b['title']}", ""] + [f"- {x}" for x in b["bullets"]] + ["", f"> {b['why']}"]
    lines += ["", f"### {'Qué sigue' if es else 'What is next'}", ""]
    lines += [f"- **{r['day']}** {r['time']} · {r['what']} ({r['src']})" + (f" — {r['prev']}" if r["prev"] else "") for r in tl["agenda"]]
    lines += ["", "---",
              ("*Metodología: IGAE desestacionalizado (INEGI 737219). Inflación anual SP30578 y subyacente SP74662; expectativa "
               "a 12 meses SR14195 (mediana); tasa objetivo SF61745; FIX SF43718; Fed DFEDTARU. Tasa real ex ante = tasa objetivo − "
               "expectativa a 12 meses. Señal: puntaje z del último cambio frente a los 60 meses previos (FIX: 260 semanas), "
               "excluyendo el propio dato; inusual ≥ 1.5σ, atípico ≥ 2σ.*" if es else
               "*Methodology: seasonally adjusted IGAE (INEGI 737219). Annual inflation SP30578, core SP74662; 12-month expectation "
               "SR14195 (median); policy rate SF61745; FIX SF43718; Fed DFEDTARU. Ex-ante real rate = policy rate − 12-month "
               "expectation. Signal: z-score of the latest change vs. the prior 60 months (FIX: 260 weeks), excluding the latest "
               "point; unusual ≥ 1.5σ, atypical ≥ 2σ.*")]
    if warnings:
        lines += ["", ("**Avisos de datos:** " if es else "**Data notices:** ") + " ".join(warnings)]
    return "\n".join(lines) + "\n"


def post_md(s: dict, t: dict, v: dict, num: int) -> str:
    return "\n".join([
        f"# Publicación LinkedIn · semana {date.fromisoformat(s['run_date']).isocalendar()[1]} ({s['run_date']})",
        "", "## 1. Texto del post (español)", "", "```text", t["es"]["post"], "```",
        f"_{len(t['es']['post'])} caracteres (límite LinkedIn: 3,000; se muestran ~210 antes de \"…ver más\")._",
        "", "## 2. Documento a adjuntar", "",
        "`bulletins/carousel_es.pdf` → en LinkedIn: *Iniciar publicación → Agregar documento*. Título sugerido del documento:",
        "", f"> MX Macro Monitor Nº {num} · {t['es']['headline']}",
        "", "Texto alternativo (para quien usa lector de pantalla; pégalo en el primer comentario si lo necesitas):",
        "", f"> {magazine.alt_text(s, v, t, num)}",
        "", "## 3. Primer comentario (inglés)", "", "```text", t["en"]["post"], "```",
        "", "## 4. Checklist antes de publicar", "",
        ("- [ ] **Nota del autor en BORRADOR:** revísala o reescríbela en `config/nota_autor.yml` (estado: final) y vuelve a correr el flujo."
         if t["es"].get("note") and t["es"]["note"]["estado"] != "final" else
         "- [ ] **Sin nota del autor esta semana:** escríbela en `config/nota_autor.yml` con la semana ISO actual y vuelve a correr el flujo."
         if not t["es"].get("note") else "- [x] Nota del autor lista."),
        "- [ ] Revisar que el titular siga vigente (si hubo un dato relevante después de las 07:00 h, ajustar).",
        "- [ ] Abrir el PDF y confirmar que las 6 páginas se ven completas.",
        "- [ ] Publicar entre 8:00 y 9:30 h (centro de México) y pegar el comentario en inglés en los primeros minutos.",
        "- [ ] Responder comentarios durante la primera hora.",
        "",
    ])


def append_history(s: dict) -> None:
    path = DATA_DIR / "history.csv"
    i, p, f, a, e = s["inflation"], s["policy"], s["fx"], s.get("activity") or {}, s.get("expectations") or {}
    row = {
        "run_date": s["run_date"], "inflation_period": i["period"], "inflation_yoy": i["yoy"], "core_yoy": i.get("core"),
        "exp_12m": e.get("exp_12m"), "policy_rate": p["rate"], "real_ex_ante": p.get("real_ex_ante"),
        "fed_upper": p.get("fed_upper"), "spread_bp": p.get("spread_bp"), "fix": f["value"], "fix_chg_1w_pct": f["chg_1w_pct"],
        "fix_signal": f["signal"], "igae_period": a.get("period"), "igae_mom": a.get("mom"), "igae_yoy": a.get("yoy"),
        "igae_signal": a.get("signal"),
    }
    df = pd.read_csv(path) if path.exists() else pd.DataFrame()
    if len(df):
        df = df[df["run_date"] != s["run_date"]]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True).sort_values("run_date")
    df.to_csv(path, index=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use data/raw cache only")
    ap.add_argument("--date", help="override run date (YYYY-MM-DD)")
    args = ap.parse_args()

    now = datetime.now(TZ)
    run_date = date.fromisoformat(args.date) if args.date else now.date()
    run_time = "23:59" if args.date else now.strftime("%H:%M")

    data, warnings = fetch_all(offline=args.offline)
    for w in warnings:
        logger.warning(w)
    missing = [k for k in CRITICAL if k not in data]
    if missing:
        logger.error("Faltan series críticas: %s. No se publica el boletín.", ", ".join(missing))
        return 1
    for k in SERIES:
        if k in data:
            logger.info("%-14s %-9s último dato %s = %.4f", k, SERIES[k][1], data[k].index[-1].date(), data[k].iloc[-1])

    snap = analytics.build_snapshot(data, run_date)
    ag = agenda_mod.window(run_date, run_time)
    text = narrative.build(snap, ag)
    peers, pw = fetch_peers(offline=args.offline)
    warnings += pw
    for w in pw:
        logger.warning(w)
    va = valueadd.build(snap, data, peers)
    num = magazine.edition_number(run_date)
    text["es"]["post"] = magazine.post_es(snap, va, text, num)
    text["en"]["post"] = magazine.comment_en(snap, va, text, num)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "archive").mkdir(exist_ok=True)
    for lang in ("es", "en"):
        res = magazine.render(snap, va, text, lang, OUTPUT_DIR, num)
        shutil.copy(res["png_dir"] / "01.png", OUTPUT_DIR / f"cover_{lang}.png")
        md = bulletin_md(snap, text, lang, warnings)
        (OUTPUT_DIR / f"latest_{lang}.md").write_text(md, encoding="utf-8")
        if lang == "es":
            (OUTPUT_DIR / "archive" / f"{snap['run_date']}_es.md").write_text(md, encoding="utf-8")
        logger.info("Carrusel %s: %s (%d láminas)", lang.upper(), res["pdf"].name, res["n"])
    (OUTPUT_DIR / "linkedin_post.md").write_text(post_md(snap, text, va, num), encoding="utf-8")

    DATA_DIR.mkdir(exist_ok=True)
    va_out = {**va, "fx_rank": {k: x for k, x in va["fx_rank"].items() if k != "weeks"}}
    (DATA_DIR / "latest.json").write_text(json.dumps({**snap, "edition": num, "value_add": va_out}, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    append_history(snap)

    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"## {text['es']['headline']}\n\n{text['es']['post']}\n\n")
            if warnings:
                fh.write("**Avisos:** " + " ".join(warnings) + "\n")
    logger.info("Titular: %s", text["es"]["headline"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
