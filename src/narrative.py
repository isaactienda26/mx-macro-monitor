"""
Rule-based interpretation layer (ES/EN).

Every sentence is built from the Snapshot: no figure is typed by hand and no
cause is asserted that the data cannot show. Wording is institutional and
neutral (verbs describe direction; no adjectives about "good" or "bad").
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from config import AUTHOR, REPO_URL

MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MES_L = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MON_L = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
         "October", "November", "December"]
DIA = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
DAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# --- formatting ----------------------------------------------------------------
def n(x: Optional[float], d: int = 2, lang: str = "es") -> str:
    return "N/D" if x is None else f"{x:,.{d}f}"


def signed(x: Optional[float], d: int = 2, unit: str = "") -> str:
    if x is None:
        return "N/D"
    s = "+" if x > 0 else ("−" if x < 0 else "")
    return f"{s}{abs(x):.{d}f}{unit}"


def month(period: str, lang: str, long: bool = False) -> str:
    y, m = int(period[:4]), int(period[5:7])
    if lang == "es":
        return f"{MES_L[m-1]} {y}" if long else f"{MES[m-1]}-{y}"
    return f"{MON_L[m-1]} {y}" if long else f"{MON[m-1]}-{y}"


def month_only(period: str, lang: str) -> str:
    m = int(period[5:7])
    return MES_L[m - 1] if lang == "es" else MON_L[m - 1]


def day(d, lang: str, weekday: bool = True) -> str:
    if isinstance(d, str):
        d = date.fromisoformat(d)
    if lang == "es":
        base = f"{d.day}-{MES[d.month-1]}"
        return f"{DIA[d.weekday()]} {base}" if weekday else base
    base = f"{MON[d.month-1]} {d.day}"
    return f"{DAY[d.weekday()]} {base}" if weekday else base


def day_year(d, lang: str) -> str:
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return f"{d.day}-{MES[d.month-1]}-{d.year}" if lang == "es" else f"{MON[d.month-1]} {d.day}, {d.year}"


def direction(delta: Optional[float], lang: str, up: str, down: str, flat: str, tol: float = 0.05) -> str:
    if delta is None or abs(delta) < tol:
        return flat
    return up if delta > 0 else down


SIGNAL_LABEL = {
    "es": {"normal": "Dentro de lo habitual", "unusual": "Inusual", "atypical": "Atípico", "na": "Sin señal"},
    "en": {"normal": "Within normal range", "unusual": "Unusual", "atypical": "Atypical", "na": "No signal"},
}


# --- per-block readings ---------------------------------------------------------
def inflation_text(s: dict, lang: str) -> dict:
    i, e = s["inflation"], s.get("expectations") or {}
    m = month(i["period"], lang)
    lo, hi = i["band"]
    if lang == "es":
        verb = direction(i["delta_pp"], lang, "sube", "baja", "se mantiene")
        title = f"La inflación {verb} {'a' if verb != 'se mantiene' else 'en'} {n(i['yoy'])}% en {month_only(i['period'], lang)}"
        if abs(i.get("streak", 0)) >= 2 and verb != "se mantiene":
            title += f" y acumula {abs(i['streak'])} meses {'al alza' if i['streak'] > 0 else 'a la baja'}"
        inside = lo <= i["yoy"] <= hi
        band = (f"dentro del intervalo de Banxico ({n(lo,0)}%–{n(hi,0)}%), {n(abs(i['yoy']-i['target']))} pp "
                f"{'por encima' if i['yoy'] > i['target'] else 'por debajo'} de la meta de {n(i['target'],0)}%"
                if inside else
                f"fuera del intervalo de Banxico ({n(lo,0)}%–{n(hi,0)}%)")
        bullets = [f"General: {n(i['yoy'])}% anual en {m} ({signed(i['delta_pp'])} pp vs. mes previo), {band}."]
        if i.get("core") is not None:
            gap = i["core"] - i["yoy"]
            src = ("La subyacente supera a la general: la presión proviene sobre todo de componentes persistentes." if gap > 0.15 else
                   "La general supera a la subyacente: la presión proviene sobre todo de componentes volátiles (no subyacente)." if gap < -0.15
                   else "General y subyacente se ubican en niveles similares.")
            bullets.append(f"Subyacente: {n(i['core'])}% ({signed(i['core_delta_pp'])} pp). {src}")
        if e.get("exp_12m") is not None:
            bullets.append(f"Expectativa a 12 meses (mediana, encuesta Banxico de {month(e['period'], lang)}): "
                           f"{n(e['exp_12m'])}%, {direction(e['exp_12m'] - e['exp_12m_prev'], lang, 'al alza', 'a la baja', 'sin cambio')} "
                           f"frente a {n(e['exp_12m_prev'])}% del mes previo.")
        why = ("Por qué importa: la subyacente es la medida que Banxico vigila para calibrar su tasa; "
               "su distancia a la meta condiciona el espacio para recortes.")
    else:
        verb = direction(i["delta_pp"], lang, "rises", "falls", "holds")
        title = f"Inflation {verb} {'to' if verb != 'holds' else 'at'} {n(i['yoy'])}% in {month_only(i['period'], lang)}"
        if abs(i.get("streak", 0)) >= 2 and verb != "holds":
            title += f", {abs(i['streak'])} months {'up' if i['streak'] > 0 else 'down'} in a row"
        inside = lo <= i["yoy"] <= hi
        band = (f"inside Banxico's {n(lo,0)}%–{n(hi,0)}% band, {n(abs(i['yoy']-i['target']))} pp "
                f"{'above' if i['yoy'] > i['target'] else 'below'} the {n(i['target'],0)}% target"
                if inside else f"outside Banxico's {n(lo,0)}%–{n(hi,0)}% band")
        bullets = [f"Headline: {n(i['yoy'])}% YoY in {m} ({signed(i['delta_pp'])} pp m/m), {band}."]
        if i.get("core") is not None:
            gap = i["core"] - i["yoy"]
            src = ("Core runs above headline: pressure comes mainly from persistent items." if gap > 0.15 else
                   "Headline runs above core: pressure comes mainly from volatile (non-core) items." if gap < -0.15
                   else "Headline and core are running at similar levels.")
            bullets.append(f"Core: {n(i['core'])}% ({signed(i['core_delta_pp'])} pp). {src}")
        if e.get("exp_12m") is not None:
            bullets.append(f"12-month expectation (median, Banxico survey, {month(e['period'], lang)}): {n(e['exp_12m'])}%, "
                           f"vs. {n(e['exp_12m_prev'])}% the previous month.")
        why = ("Why it matters: core inflation is the gauge Banxico watches to set rates; "
               "its distance from target defines the room for further cuts.")
    return {"title": title, "bullets": bullets, "why": why}


def policy_text(s: dict, lang: str) -> dict:
    p = s["policy"]
    eff = p.get("last_change_effective")
    if lang == "es":
        title = f"Tasa de Banxico en {n(p['rate'])}%; diferencial con la Fed de {n(p.get('spread_bp'),0)} pb"
        last = (f"Último movimiento: {signed(p['last_change_bp'],0)} pb, vigente desde el {day_year(eff, lang)}; "
                f"{signed(p['chg_12m_bp'],0)} pb en 12 meses.") if eff else ""
        bullets = [last] if last else []
        if p.get("real_ex_ante") is not None:
            bullets.append(f"Tasa real ex ante: {n(p['real_ex_ante'])}% (tasa objetivo menos expectativa de inflación a 12 meses); "
                           f"ex post: {n(p['real_ex_post'])}%.")
        if p.get("fed_upper") is not None:
            bullets.append(f"Fed: rango {n(p['fed_lower'])}%–{n(p['fed_upper'])}%. Diferencial Banxico–Fed (límite superior): "
                           f"{n(p['spread_bp'],0)} pb vs. {n(p.get('spread_12m_ago_bp'),0)} pb hace un año.")
        why = ("Por qué importa: un diferencial más estrecho reduce el rendimiento relativo de los activos en pesos, "
               "uno de los soportes del tipo de cambio.")
    else:
        title = f"Banxico rate at {n(p['rate'])}%; spread over the Fed at {n(p.get('spread_bp'),0)} bp"
        last = (f"Last move: {signed(p['last_change_bp'],0)} bp, effective {day_year(eff, lang)}; "
                f"{signed(p['chg_12m_bp'],0)} bp over 12 months.") if eff else ""
        bullets = [last] if last else []
        if p.get("real_ex_ante") is not None:
            bullets.append(f"Ex-ante real rate: {n(p['real_ex_ante'])}% (policy rate minus 12-month inflation expectation); "
                           f"ex-post: {n(p['real_ex_post'])}%.")
        if p.get("fed_upper") is not None:
            bullets.append(f"Fed: {n(p['fed_lower'])}%–{n(p['fed_upper'])}% range. Banxico–Fed spread (upper bound): "
                           f"{n(p['spread_bp'],0)} bp vs. {n(p.get('spread_12m_ago_bp'),0)} bp a year ago.")
        why = ("Why it matters: a narrower spread lowers the relative yield on peso assets, "
               "one of the supports of the exchange rate.")
    return {"title": title, "bullets": bullets, "why": why}


def fx_text(s: dict, lang: str) -> dict:
    f = s["fx"]
    w = f["chg_1w_pct"]
    if lang == "es":
        verb = direction(w, lang, "se deprecia", "se aprecia", "se mantiene estable", tol=0.25)
        title = f"El peso {verb} {n(abs(w))}% en la semana" if "estable" not in verb else "El peso se mantiene estable en la semana"
        if f["signal"] in ("unusual", "atypical") and f.get("largest_since"):
            title += f", su mayor movimiento semanal desde {month(f['largest_since'][:7], lang, long=True)}"
        bullets = [f"FIX en {n(f['value'],4)} pesos por dólar ({day_year(f['date'], lang)}): {signed(w)}% semanal, "
                   f"{signed(f['chg_1m_pct'])}% mensual y {signed(f['chg_12m_pct'])}% anual. Un alza del FIX equivale a depreciación del peso."]
        if f["signal"] in ("unusual", "atypical"):
            since = (f"; es el mayor movimiento semanal en esa dirección desde la semana del {day_year(f['largest_since'], lang)}"
                     if f.get("largest_since") else f"; no tiene precedente en la muestra (desde {f['history_start'][:4]})")
            bullets.append(f"Señal estadística: {SIGNAL_LABEL[lang][f['signal']].lower()} ({signed(f['z_1w'])} desviaciones estándar "
                           f"frente a las variaciones semanales de los últimos 5 años){since}.")
        bullets.append(f"Rango de 52 semanas: {n(f['low_52w'],2)} ({day_year(f['low_52w_date'], lang)}) a "
                       f"{n(f['high_52w'],2)} ({day_year(f['high_52w_date'], lang)}); "
                       + ("el nivel actual es el máximo del periodo." if f["pos_52w"] >= 99.5 else
                          "el nivel actual es el mínimo del periodo." if f["pos_52w"] <= 0.5 else
                          f"el nivel actual se ubica al {n(f['pos_52w'],0)}% del recorrido entre mínimo y máximo."))
        why = "Por qué importa: el tipo de cambio se transmite a los precios de bienes importados y a los costos de empresas con insumos en dólares."
    else:
        verb = direction(w, lang, "weakens", "strengthens", "is stable", tol=0.25)
        title = f"The peso {verb} {n(abs(w))}% on the week" if verb != "is stable" else "The peso is stable on the week"
        if f["signal"] in ("unusual", "atypical") and f.get("largest_since"):
            title += f", its largest weekly move since {month(f['largest_since'][:7], lang, long=True)}"
        bullets = [f"FIX at {n(f['value'],4)} MXN per USD ({day_year(f['date'], lang)}): {signed(w)}% w/w, "
                   f"{signed(f['chg_1m_pct'])}% m/m, {signed(f['chg_12m_pct'])}% y/y. A higher FIX means a weaker peso."]
        if f["signal"] in ("unusual", "atypical"):
            since = (f"; the largest weekly move in that direction since the week of {day_year(f['largest_since'], lang)}"
                     if f.get("largest_since") else f"; unprecedented in the sample (since {f['history_start'][:4]})")
            bullets.append(f"Statistical signal: {SIGNAL_LABEL[lang][f['signal']].lower()} ({signed(f['z_1w'])} standard deviations "
                           f"vs. weekly moves over the past 5 years){since}.")
        bullets.append(f"52-week range: {n(f['low_52w'],2)} ({day_year(f['low_52w_date'], lang)}) to "
                       f"{n(f['high_52w'],2)} ({day_year(f['high_52w_date'], lang)}); "
                       + ("the current level is the period high." if f["pos_52w"] >= 99.5 else
                          "the current level is the period low." if f["pos_52w"] <= 0.5 else
                          f"the current level sits {n(f['pos_52w'],0)}% of the way from low to high."))
        why = "Why it matters: the exchange rate passes through to imported-goods prices and to costs of firms with dollar inputs."
    return {"title": title, "bullets": bullets, "why": why}


def activity_text(s: dict, lang: str) -> Optional[dict]:
    a = s.get("activity")
    if not a:
        return None
    m = month_only(a["period"], lang)
    if lang == "es":
        verb = direction(a["mom"], lang, "avanza", "retrocede", "se mantiene", tol=0.05)
        title = f"La actividad económica {verb} {n(abs(a['mom']),1)}% mensual en {m}"
        bullets = [f"IGAE desestacionalizado: {signed(a['mom'],1)}% mensual y {signed(a['yoy'],1)}% anual en {month(a['period'], lang)} "
                   f"(mes previo: {signed(a['mom_prev'],1)}% y {signed(a['yoy_prev'],1)}%).",
                   f"Promedio de los últimos 3 meses vs. los 3 previos: {signed(a['q3_vs_prev3'],1)}%. "
                   f"Esta medida suaviza el ruido de un solo mes."]
        if a["signal"] in ("unusual", "atypical"):
            bullets.append(f"Señal estadística: variación mensual {SIGNAL_LABEL[lang][a['signal']].lower()} "
                           f"({signed(a['z'])} desviaciones estándar vs. los 60 meses previos).")
        why = "Por qué importa: el IGAE es la aproximación mensual al PIB; anticipa la lectura trimestral."
    else:
        verb = direction(a["mom"], lang, "grows", "contracts", "is flat", tol=0.05)
        title = f"Economic activity {verb} {n(abs(a['mom']),1)}% m/m in {m}"
        bullets = [f"Seasonally adjusted IGAE: {signed(a['mom'],1)}% m/m and {signed(a['yoy'],1)}% y/y in {month(a['period'], lang)} "
                   f"(prior month: {signed(a['mom_prev'],1)}% and {signed(a['yoy_prev'],1)}%).",
                   f"Last 3 months vs. previous 3: {signed(a['q3_vs_prev3'],1)}%. This smooths single-month noise."]
        if a["signal"] in ("unusual", "atypical"):
            bullets.append(f"Statistical signal: {SIGNAL_LABEL[lang][a['signal']].lower()} monthly change "
                           f"({signed(a['z'])} standard deviations vs. the previous 60 months).")
        why = "Why it matters: IGAE is the monthly proxy for GDP and anticipates the quarterly print."
    return {"title": title, "bullets": bullets, "why": why}


# --- headline selection ----------------------------------------------------------
def pick_story(s: dict, recent_keys: List[str]) -> List[str]:
    """Order the four blocks by news value for this week."""
    run = date.fromisoformat(s["run_date"])
    score = {"inflation": 1.0, "policy": 0.5, "fx": 0.4, "activity": 0.3}
    p = s["policy"]
    if p.get("last_change_effective") and (run - date.fromisoformat(p["last_change_effective"])).days <= 8:
        score["policy"] = 10
    if "banxico" in recent_keys:
        score["policy"] = max(score["policy"], 9)
    sig = {"atypical": 8, "unusual": 4.5}
    score["fx"] += sig.get(s["fx"]["signal"], 0)
    if "inpc_m" in recent_keys:
        score["inflation"] += 6
    if "igae" in recent_keys and s.get("activity"):
        score["activity"] += 5
    if not s.get("activity"):
        score.pop("activity")
    return sorted(score, key=score.get, reverse=True)


def build(s: dict, agenda: dict) -> Dict[str, dict]:
    recent_keys = [e["key"] for e in agenda["recent"]]
    order = pick_story(s, recent_keys)
    out = {}
    for lang in ("es", "en"):
        blocks = {"inflation": inflation_text(s, lang), "policy": policy_text(s, lang),
                  "fx": fx_text(s, lang), "activity": activity_text(s, lang)}
        lead, second = blocks[order[0]], blocks[order[1]]
        out[lang] = {"order": order, "blocks": blocks, "headline": lead["title"], "subhead": second["title"],
                     "agenda": agenda_lines(s, agenda, lang),
                     "recent": agenda_lines(s, agenda, lang, "recent")}
        out[lang]["post"] = post_es(s, out[lang], agenda) if lang == "es" else comment_en(s, out[lang], agenda)
    return out


# --- agenda ------------------------------------------------------------------------
def previous_value(key: str, s: dict, lang: str) -> str:
    i, p, a, e = s["inflation"], s["policy"], s.get("activity") or {}, s.get("expectations") or {}
    prev = "previo" if lang == "es" else "prior"
    m = {
        "inpc_m": f"{prev}: {n(i['yoy'])}% ({month(i['period'], lang)})",
        "inpc_q": f"{prev} mensual: {n(i['yoy'])}%" if lang == "es" else f"last monthly: {n(i['yoy'])}%",
        "igae": f"{prev}: {signed(a.get('mom'),1)}% m/m" if a else "",
        "ioae": f"IGAE {prev}: {signed(a.get('mom'),1)}% m/m" if a else "",
        "banxico": (f"tasa actual: {n(p['rate'])}%" if lang == "es" else f"current rate: {n(p['rate'])}%"),
        "fomc": (f"rango actual: {n(p.get('fed_lower'))}%–{n(p.get('fed_upper'))}%" if lang == "es"
                 else f"current range: {n(p.get('fed_lower'))}%–{n(p.get('fed_upper'))}%"),
        "encuesta": (f"exp. 12m {prev}: {n(e.get('exp_12m'))}%" if e else ""),
    }
    return m.get(key, "")


def agenda_lines(s: dict, agenda: dict, lang: str, which: str = "upcoming") -> List[dict]:
    rows = []
    for ev in agenda[which]:
        rows.append({"day": day(ev["date"], lang), "time": ev.get("time") or "", "src": ev["src"],
                     "what": ev[lang], "prev": previous_value(ev["key"], s, lang) if which == "upcoming" else ""})
    return rows


# --- LinkedIn copy -----------------------------------------------------------------
HASHTAGS_ES = "#EconomíaMexicana #Banxico #Inflación #TipoDeCambio #Macroeconomía"
HASHTAGS_EN = "#Mexico #Economy #Banxico #Inflation #MXN"

CTA_ES = {
    "fx": "¿Cómo está afectando el tipo de cambio a los costos o ingresos de tu sector?",
    "inflation": "¿Están viendo esta presión de precios en los costos de su empresa?",
    "policy": "¿Qué movimiento esperas de Banxico en su próxima decisión?",
    "activity": "¿Su sector se mueve en línea con el IGAE o en sentido contrario?",
}


def _one_liners(s: dict, lang: str) -> Dict[str, str]:
    i, p, f, a, e = s["inflation"], s["policy"], s["fx"], s.get("activity"), s.get("expectations") or {}
    if lang == "es":
        d = {
            "fx": f"Tipo de cambio: {n(f['value'],2)} por dólar, {signed(f['chg_1w_pct'])}% en la semana y {signed(f['chg_12m_pct'])}% en 12 meses.",
            "inflation": f"Inflación: {n(i['yoy'])}% anual en {month(i['period'], lang)}; subyacente {n(i.get('core'))}%. Meta de Banxico: 3%.",
            "policy": f"Banxico: tasa en {n(p['rate'])}%; real ex ante {n(p.get('real_ex_ante'))}%; diferencial con la Fed {n(p.get('spread_bp'),0)} pb.",
        }
        if a:
            d["activity"] = f"Actividad (IGAE): {signed(a['mom'],1)}% mensual y {signed(a['yoy'],1)}% anual en {month(a['period'], lang)}."
    else:
        d = {
            "fx": f"FX: {n(f['value'],2)} MXN/USD, {signed(f['chg_1w_pct'])}% w/w, {signed(f['chg_12m_pct'])}% y/y.",
            "inflation": f"Inflation: {n(i['yoy'])}% y/y in {month(i['period'], lang)}; core {n(i.get('core'))}%. Target: 3%.",
            "policy": f"Banxico: {n(p['rate'])}% policy rate; {n(p.get('real_ex_ante'))}% ex-ante real; {n(p.get('spread_bp'),0)} bp over the Fed.",
        }
        if a:
            d["activity"] = f"Activity (IGAE): {signed(a['mom'],1)}% m/m, {signed(a['yoy'],1)}% y/y in {month(a['period'], lang)}."
    return d


def post_es(s: dict, t: dict, agenda: dict) -> str:
    lead = t["blocks"][t["order"][0]]
    lines = _one_liners(s, "es")
    ag = "\n".join(f"▪ {r['day']} · {r['what']}" for r in t["agenda"][:3])
    body = "\n".join(f"▪ {lines[k]}" for k in t["order"] if k in lines)
    return (
        f"{t['headline']}.\n\n"
        f"{lead['why'].replace('Por qué importa: ', '').capitalize()}\n\n"
        f"MX Macro Monitor · semana {date.fromisoformat(s['run_date']).isocalendar()[1]} "
        f"(datos al {day_year(s['run_date'], 'es')}):\n\n{body}\n\n"
        f"Qué sigue:\n{ag}\n\n"
        f"{CTA_ES[t['order'][0]]}\n\n"
        f"Cada lunes publico este monitor con datos oficiales de Banxico, INEGI y la Reserva Federal; "
        f"el detalle está en el carrusel.\n\n"
        f"{HASHTAGS_ES}"
    )


def comment_en(s: dict, t: dict, agenda: dict) -> str:
    lines = _one_liners(s, "en")
    body = "\n".join(f"▪ {lines[k]}" for k in t["order"] if k in lines)
    return (
        f"English version · {t['headline']}.\n\n{body}\n\n"
        f"Sources: Banxico (SIE), INEGI (BIE), Federal Reserve (FRED). Data as of {day_year(s['run_date'], 'en')}.\n"
        f"Methodology and open-source code: {REPO_URL}\n\n{HASHTAGS_EN}"
    )
