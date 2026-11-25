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
        out[lang]["cards"] = cards(s, lang)
        out[lang]["post"] = (post_v3_es(s, order, out[lang]["cards"], out[lang]["agenda"]) if lang == "es"
                             else comment_v3_en(s, order, out[lang]["cards"]))
        out[lang]["ed"] = editorial(s, lang)
        note = load_author_note(s["run_date"])
        out[lang]["note"] = ({"text": note[lang] or note["es"], "estado": note["estado"], "cita": note.get(f"cita_{lang}")} if note and (note.get(lang) or lang == "es")
                             else None)
        out[lang]["post"] = (post_v4_es(s, order, out[lang]["ed"], out[lang]["agenda"], note) if lang == "es"
                             else comment_v4_en(s, order, out[lang]["ed"], note))
        out[lang]["headline"] = out[lang]["ed"][order[0]]["head"]
        out[lang]["subhead"] = out[lang]["ed"][order[1]]["head"]
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
        "encuesta": ((f"expectativa 12m previa: {n(e.get('exp_12m_mean') or e.get('exp_12m'))}% (media)" if lang == "es"
                      else f"prior 12m expectation: {n(e.get('exp_12m_mean') or e.get('exp_12m'))}% (mean)") if e else ""),
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


# =====================================================================================
# v3 "cards": compact copy for the 5-slide carousel (≤ ~35 words per slide)
# =====================================================================================
REFERENCES = {
    "banxico_neutral": {
        "short": "Banxico (2024), Recuadro 7",
        "full": "Banco de México (2024). Actualización de la estimación de la tasa neutral en México. "
                "Informe Trimestral abril–junio 2024, Recuadro 7.",
    },
    "capistran": {
        "short": "Capistrán, Ibarra y Ramos-Francia (2012)",
        "full": "Capistrán, C., Ibarra, R. y Ramos-Francia, M. (2012). El traspaso de movimientos del tipo de cambio "
                "a los precios: un análisis para la economía mexicana. El Trimestre Económico, 79(316), 813–838.",
    },
    "angeles": {
        "short": "Ángeles, Cortés y Sámano (2019)",
        "full": "Ángeles, D., Cortés, J. F. y Sámano, D. (2019). Evolution and Characteristics of the Exchange Rate "
                "Pass-Through to Prices in Mexico. Banco de México, Working Paper 2019-10.",
    },
    "fama": {
        "short": "Fama (1984)",
        "full": "Fama, E. F. (1984). Forward and spot exchange rates. Journal of Monetary Economics, 14(3), 319–338.",
    },
    "heath": {
        "short": "Heath (2012)",
        "full": "Heath, J. (2012). Lo que indican los indicadores: cómo utilizar la información estadística para "
                "entender la realidad económica de México. INEGI.",
    },
    "banxico_survey": {
        "short": "Banxico, Encuesta de Expectativas",
        "full": "Banco de México. Encuesta sobre las Expectativas de los Especialistas en Economía del Sector Privado (mensual).",
    },
}

SOURCE_LINE = {
    "fx": {"es": "Fuente: Elaboración propia con datos de Banxico (SIE, serie SF43718).",
           "en": "Source: Author's elaboration with data from Banxico (SIE, series SF43718)."},
    "activity": {"es": "Fuente: Elaboración propia con datos de INEGI (BIE, serie 737219, desestacionalizada).",
                 "en": "Source: Author's elaboration with data from INEGI (BIE, series 737219, seasonally adjusted)."},
    "inflation": {"es": "Fuente: Elaboración propia con datos de INEGI y Banxico (SIE, series SP30578 y SP74662).",
                  "en": "Source: Author's elaboration with data from INEGI and Banxico (SIE, series SP30578, SP74662)."},
    "policy": {"es": "Fuente: Elaboración propia con datos de Banxico (SIE, series SF61745 y SR14194) y rango neutral de Banxico (2024).",
               "en": "Source: Author's elaboration with data from Banxico (SIE, series SF61745, SR14194) and Banxico's (2024) neutral range."},
    "dashboard": {"es": "Fuente: Elaboración propia con datos de Banxico (SIE), INEGI (BIE) y Reserva Federal (FRED).",
                  "en": "Source: Author's elaboration with data from Banxico (SIE), INEGI (BIE) and the Federal Reserve (FRED)."},
}


def _since_label(f: dict, lang: str) -> str:
    return month(f["largest_since"][:7], lang, long=True).replace(" ", " de " if lang == "es" else " ") if lang == "es" \
        else month(f["largest_since"][:7], lang, long=True)


def cards(s: dict, lang: str) -> Dict[str, dict]:
    es = lang == "es"
    i, e, p, f, a = s["inflation"], s.get("expectations") or {}, s["policy"], s["fx"], s.get("activity")
    out: Dict[str, dict] = {}

    # --- FX -----------------------------------------------------------------
    w = f["chg_1w_pct"]
    dep = w > 0
    if abs(w) < 0.25:
        title = "El peso, estable en la semana" if es else "The peso holds steady on the week"
    elif es:
        title = f"El peso se {'deprecia' if dep else 'aprecia'} {abs(w):.1f}% en la semana"
    else:
        title = f"The peso {'weakens' if dep else 'strengthens'} {abs(w):.1f}% on the week"
    if f["signal"] in ("unusual", "atypical") and f.get("largest_since"):
        kicker = (f"Su mayor movimiento semanal desde {_since_label(f, lang)}" if es
                  else f"Its largest weekly move since {_since_label(f, lang)}")
    else:
        kicker = (f"FIX: {f['value']:.2f} pesos por dólar" if es else f"FIX: {f['value']:.2f} MXN per USD")
    ext = ("máximo de 52 semanas" if f["pos_52w"] >= 99.5 else "mínimo de 52 semanas" if f["pos_52w"] <= 0.5 else "") if es else \
          ("a 52-week high" if f["pos_52w"] >= 99.5 else "a 52-week low" if f["pos_52w"] <= 0.5 else "")
    if es:
        read = (f"FIX: {f['value']:.2f} pesos por dólar el {day(f['date'], lang, False)}"
                + (f", {ext}" if ext else f"; {signed(f['chg_1m_pct'],1)}% en el mes") + ".")
        why = "En México, el traspaso del tipo de cambio a precios es bajo desde la adopción de metas de inflación."
    else:
        read = (f"FIX: {f['value']:.2f} MXN per USD on {day(f['date'], lang, False)}"
                + (f", {ext}" if ext else f"; {signed(f['chg_1m_pct'],1)}% on the month") + ".")
        why = "Mexico's exchange-rate pass-through to prices has been low since the adoption of inflation targeting."
    if abs(w) < 0.25:
        hero_label = "Tipo de cambio FIX, variación semanal" if es else "USD/MXN FIX, weekly change"
    else:
        hero_label = ((f"{'Depreciación' if dep else 'Apreciación'} del peso en la semana" if es
                       else f"Weekly {'depreciation' if dep else 'appreciation'} of the peso"))
    cover = (kicker if f["signal"] in ("unusual", "atypical") and f.get("largest_since") else title)
    out["fx"] = {"title": title, "kicker": kicker, "read": read, "why": why, "refs": ["capistran", "angeles"],
                 "hero": f"{abs(w):.1f}%" if abs(w) >= 0.25 else f"{signed(w,1)}%", "hero_label": hero_label,
                 "cover_line": cover, "cover_sub": read}

    # --- Activity -----------------------------------------------------------
    if a:
        mm = a["mom"]
        if abs(mm) < 0.05:
            title = (f"La actividad se mantiene estable en {month_only(a['period'], lang)}" if es
                     else f"Activity is flat in {month_only(a['period'], lang)}")
        elif es:
            title = f"La actividad {'avanza' if mm > 0 else 'retrocede'} {abs(mm):.1f}% en {month_only(a['period'], lang)}"
        else:
            title = f"Activity {'grows' if mm > 0 else 'contracts'} {abs(mm):.1f}% in {month_only(a['period'], lang)}"
        q = a["q3_vs_prev3"]
        trend_es = "al alza" if q > 0.05 else "a la baja" if q < -0.05 else "estable"
        trend_en = "up" if q > 0.05 else "down" if q < -0.05 else "flat"
        out["activity"] = {
            "title": title,
            "kicker": (f"IGAE desestacionalizado · {signed(a['yoy'],1)}% anual" if es else f"Seasonally adjusted IGAE · {signed(a['yoy'],1)}% y/y"),
            "read": (f"Promedio de 3 meses: {signed(q,1)}% vs. los 3 previos; tendencia {trend_es}." if es
                     else f"Three-month average: {signed(q,1)}% vs. the prior three; trend {trend_en}."),
            "why": ("El IGAE anticipa la lectura trimestral del PIB." if es
                    else "IGAE anticipates the quarterly GDP print."),
            "refs": ["heath"], "hero": f"{signed(mm,1)}%",
            "cover_line": ((f"La actividad económica {'avanza' if mm > 0 else 'retrocede'} en {month_only(a['period'], lang)}; "
                            f"la tendencia trimestral sigue {trend_es}") if es else
                           (f"Activity {'grows' if mm > 0 else 'contracts'} in {month_only(a['period'], lang)}; "
                            f"the quarterly trend is {trend_en}")),
            "cover_sub": (f"IGAE desestacionalizado · {signed(a['yoy'],1)}% anual" if es else f"Seasonally adjusted IGAE · {signed(a['yoy'],1)}% y/y"),
            "hero_label": (f"IGAE, variación mensual ({month(a['period'], lang)})" if es else f"IGAE, monthly change ({month(a['period'], lang)})"),
        }

    # --- Inflation ------------------------------------------------------------
    dpp = i["delta_pp"]
    verb_es = "sube a" if dpp >= 0.05 else "baja a" if dpp <= -0.05 else "se mantiene en"
    verb_en = "rises to" if dpp >= 0.05 else "falls to" if dpp <= -0.05 else "holds at"
    gap = i["yoy"] - i["target"]
    inside = i["band"][0] <= i["yoy"] <= i["band"][1]
    streak = i.get("streak", 0)
    if es:
        read = (f"{abs(gap):.2f} pp {'sobre' if gap > 0 else 'bajo'} la meta"
                + (f"; {abs(streak)} meses {'al alza' if streak > 0 else 'a la baja'}" if abs(streak) >= 2 else "")
                + ("." if inside else "; fuera del intervalo de 2% a 4%."))
        why = (f"Los analistas esperan {e.get('exp_12m_mean') or e.get('exp_12m'):.2f}% a 12 meses (encuesta de Banxico)."
               if e else "Sin dato de expectativas esta semana.")
    else:
        read = (f"{abs(gap):.2f} pp {'above' if gap > 0 else 'below'} target"
                + (f"; {abs(streak)} months {'up' if streak > 0 else 'down'} in a row" if abs(streak) >= 2 else "")
                + ("." if inside else "; outside the 2%–4% band."))
        why = (f"Analysts expect {e.get('exp_12m_mean') or e.get('exp_12m'):.2f}% over 12 months (Banxico survey)."
               if e else "No expectations data this week.")
    out["inflation"] = {
        "title": (f"La inflación {verb_es} {i['yoy']:.2f}% en {month_only(i['period'], lang)}" if es
                  else f"Inflation {verb_en} {i['yoy']:.2f}% in {month_only(i['period'], lang)}"),
        "kicker": (f"Subyacente: {i.get('core', 0):.2f}% · Meta de Banxico: 3% ± 1 pp" if es else f"Core: {i.get('core', 0):.2f}% · Banxico target: 3% ± 1 pp"),
        "read": read, "why": why, "refs": ["banxico_survey"], "hero": f"{i['yoy']:.2f}%",
        "cover_line": read[0].upper() + read[1:].rstrip("."),
        "cover_sub": (f"Subyacente: {i.get('core', 0):.2f}%" if es else f"Core: {i.get('core', 0):.2f}%"),
        "hero_label": (f"Inflación general anual ({month(i['period'], lang)})" if es else f"Headline inflation, y/y ({month(i['period'], lang)})"),
    }

    # --- Policy -----------------------------------------------------------------
    ra, st = p.get("real_ex_ante"), p.get("stance", "neutral")
    lo, hi = p.get("neutral_range", [1.8, 3.6])
    st_es = {"neutral": "dentro del rango neutral", "restrictive": "por encima del rango neutral",
             "accommodative": "por debajo del rango neutral"}[st]
    st_en = {"neutral": "inside the neutral range", "restrictive": "above the neutral range",
             "accommodative": "below the neutral range"}[st]
    sp, sp12 = p.get("spread_bp"), p.get("spread_12m_ago_bp")
    if es:
        read = f"Tasa objetivo: {p['rate']:.2f}%. Diferencial con la Fed: {sp:.0f} pb ({sp12:.0f} pb hace un año)."
        why = ("Un diferencial menor reduce el rendimiento relativo de los activos en pesos." if sp < sp12 else
               "Un diferencial mayor eleva el rendimiento relativo de los activos en pesos.")
    else:
        read = f"Policy rate: {p['rate']:.2f}%. Spread over the Fed: {sp:.0f} bp ({sp12:.0f} bp a year ago)."
        why = ("A narrower spread lowers the relative yield on peso assets." if sp < sp12 else
               "A wider spread raises the relative yield on peso assets.")
    out["policy"] = {
        "title": (f"Tasa real ex ante: {ra:.2f}%, {st_es}" if es else f"Ex-ante real rate: {ra:.2f}%, {st_en}"),
        "kicker": (f"Rango neutral estimado por Banxico: {lo:.1f}% a {hi:.1f}%" if es else f"Banxico's estimated neutral range: {lo:.1f}% to {hi:.1f}%"),
        "read": read, "why": why, "refs": ["banxico_neutral", "fama"], "hero": f"{ra:.2f}%",
        "cover_line": ((f"Con la tasa objetivo en {p['rate']:.2f}%, la postura monetaria queda {st_es}") if es
                       else f"With the policy rate at {p['rate']:.2f}%, the monetary stance sits {st_en}"),
        "cover_sub": (f"Rango neutral estimado por Banxico: {lo:.1f}% a {hi:.1f}%" if es else f"Banxico's neutral range: {lo:.1f}% to {hi:.1f}%"),
        "hero_label": ("Tasa real ex ante (tasa objetivo − expectativa de inflación)" if es
                       else "Ex-ante real rate (policy rate − expected inflation)"),
    }
    for k, c in out.items():
        c["source"] = SOURCE_LINE[k][lang]
        c["ref_line"] = "Ref.: " + "; ".join(REFERENCES[r]["short"] if es else REFERENCES[r]["short"].replace(" y ", " and ")
                                           .replace("Encuesta de Expectativas", "Expectations Survey") for r in c["refs"])
        c["words"] = len((c["title"] + " " + c["kicker"] + " " + c["read"] + " " + c["why"]).split())
    return out


def post_v3_es(s: dict, order: List[str], cd: Dict[str, dict], agenda_rows: List[dict]) -> str:
    lead = cd[order[0]]
    i, p, f, a = s["inflation"], s["policy"], s["fx"], s.get("activity")
    facts = {
        "fx": f"Tipo de cambio: {f['value']:.2f} pesos por dólar ({signed(f['chg_1w_pct'],1)}% semanal).",
        "inflation": f"Inflación: {i['yoy']:.2f}% anual en {month(i['period'], 'es')} (subyacente {i.get('core', 0):.2f}%).",
        "policy": f"Tasa real ex ante: {p.get('real_ex_ante'):.2f}%, {'dentro del' if p.get('stance') == 'neutral' else 'fuera del'} rango neutral de Banxico.",
        "activity": (f"IGAE: {signed(a['mom'],1)}% mensual y {signed(a['yoy'],1)}% anual en {month(a['period'], 'es')}." if a else ""),
    }
    bullets = "\n".join(f"▪ {facts[k]}" for k in order[1:] if facts.get(k))
    nxt = " · ".join(f"{r['day']}: {r['what']}" for r in agenda_rows[:2])
    return (f"{lead['title']}: {lead['kicker'][0].lower() + lead['kicker'][1:]}.\n\n"
            f"{lead['why']}\n\n"
            f"Lo demás de la semana:\n{bullets}\n\n"
            f"Qué sigue → {nxt}\n\n"
            f"{CTA_ES[order[0]]}\n\n"
            f"Datos oficiales de Banxico, INEGI y la Fed; metodología y referencias en el carrusel.\n\n"
            f"#EconomíaMexicana #Banxico #Macroeconomía")


def comment_v3_en(s: dict, order: List[str], cd: Dict[str, dict]) -> str:
    lead = cd[order[0]]
    lines = "\n".join(f"▪ {cd[k]['title']}." for k in order[1:] if k in cd)
    return (f"English version · {lead['title']}: {lead['kicker'][0].lower() + lead['kicker'][1:]}.\n\n{lines}\n\n"
            f"Official data from Banxico, INEGI and the Federal Reserve. Methodology, references and open-source code: {REPO_URL}")


# =====================================================================================
# v4 editorial layer: institutional two-layer copy (plain language + technical notes)
# =====================================================================================
def _mon_long(period: str, lang: str) -> str:
    return month_only(period, lang)


def editorial(s: dict, lang: str) -> Dict[str, dict]:
    es = lang == "es"
    i, e, p, f, a = s["inflation"], s.get("expectations") or {}, s["policy"], s["fx"], s.get("activity")
    out: Dict[str, dict] = {}
    obs = ("Última observación: " if es else "Last observation: ")

    # --- FX
    w = f["chg_1w_pct"]
    dep = w > 0
    atyp = f["signal"] in ("unusual", "atypical") and f.get("largest_since")
    since = _since_label(f, lang) if f.get("largest_since") else ""
    if abs(w) < 0.25:
        head = "El peso se mantiene estable frente al dólar" if es else "The peso holds steady against the dollar"
    elif es:
        head = (f"El peso registra su mayor {'depreciación' if dep else 'apreciación'} semanal desde {since}" if atyp
                else f"El peso se {'deprecia' if dep else 'aprecia'} {abs(w):.1f}% en la semana")
    else:
        head = (f"The peso posts its largest weekly {'loss' if dep else 'gain'} since {since}" if atyp
                else f"The peso {'weakens' if dep else 'strengthens'} {abs(w):.1f}% on the week")
    v0 = f.get("value_1w_ago")
    if es:
        dek = (f"El dólar pasó de {v0:.2f} a {f['value']:.2f} pesos en siete días ({signed(w,1)}%). "
               "El efecto sobre los precios suele ser acotado: el traspaso cambiario en México es bajo desde la "
               "adopción de metas de inflación (Capistrán et al., 2012).")
        q = "¿Qué tanto se notará en los precios?"
        ans = "La evidencia para México sugiere que poco: el traspaso del tipo de cambio a la inflación es bajo desde que Banxico adoptó metas de inflación."
    else:
        dek = (f"The dollar went from {v0:.2f} to {f['value']:.2f} pesos in seven days ({signed(w,1)}%). "
               "The effect on prices tends to be limited: Mexico's exchange-rate pass-through has been low since "
               "inflation targeting (Capistrán et al., 2012).")
        q = "How much will prices feel it?"
        ans = "Evidence for Mexico suggests not much: pass-through to inflation has been low since inflation targeting."
    out["fx"] = {
        "head": head, "dek": dek, "q": q, "ans": ans,
        "chart_title": "Tipo de cambio FIX" if es else "USD/MXN FIX exchange rate",
        "chart_sub": "Pesos por dólar, datos diarios, últimas 52 semanas" if es else "Pesos per dollar, daily, last 52 weeks",
        "note": (("Nota: un alza indica depreciación del peso. " if es else "Note: a rise means a weaker peso. ")
                 + obs + day_year(f["date"], lang) + "."),
        "source": SOURCE_LINE["fx"][lang],
    }

    # --- Activity
    if a:
        mm, q3 = a["mom"], a["q3_vs_prev3"]
        mon, prevmon = _mon_long(a["period"], lang), MES_L[(int(a["period"][5:7]) - 2) % 12] if es else MON_L[(int(a["period"][5:7]) - 2) % 12]
        if es:
            head = (f"La actividad económica {'retrocede' if mm < 0 else 'avanza'} {abs(mm):.1f}% en {mon}"
                    if abs(mm) >= 0.05 else f"La actividad económica se mantiene en {mon}")
            trend = "al alza" if q3 > 0.05 else "a la baja" if q3 < -0.05 else "estable"
            dek = (f"La actividad fue {abs(mm):.1f}% {'menor' if mm < 0 else 'mayor'} que en {prevmon}, según el IGAE, "
                   f"el indicador mensual que anticipa al PIB. El promedio de tres meses sigue {trend} ({signed(q3,1)}%): "
                   "un solo mes no define la tendencia (Heath, 2012).")
            q = "¿Es el inicio de una desaceleración?"
            ans = f"Un mes no basta para decirlo: el promedio de tres meses sigue {trend} ({signed(q3,1)}%)."
        else:
            head = (f"Economic activity {'contracts' if mm < 0 else 'grows'} {abs(mm):.1f}% in {mon}"
                    if abs(mm) >= 0.05 else f"Economic activity is flat in {mon}")
            trend = "up" if q3 > 0.05 else "down" if q3 < -0.05 else "flat"
            dek = (f"Activity was {abs(mm):.1f}% {'lower' if mm < 0 else 'higher'} than in {prevmon}, according to IGAE, "
                   f"the monthly indicator that anticipates GDP. The three-month average is still {trend} ({signed(q3,1)}%): "
                   "one month does not set the trend (Heath, 2012).")
            q = "Is this the start of a slowdown?"
            ans = f"One month is not enough to tell: the three-month average is still {trend} ({signed(q3,1)}%)."
        out["activity"] = {
            "head": head, "dek": dek, "q": q, "ans": ans,
            "chart_title": "Indicador Global de la Actividad Económica (IGAE)" if es else "Global Economic Activity Indicator (IGAE)",
            "chart_sub": "Variación % mensual, a.e., últimos 24 meses" if es else "Monthly % change, s.a., last 24 months",
            "note": (("a.e./ Cifras con ajuste estacional. " if es else "s.a./ Seasonally adjusted. ")
                     + obs + month(a["period"], lang) + "."),
            "source": SOURCE_LINE["activity"][lang],
        }

    # --- Inflation
    gap = i["yoy"] - i["target"]
    dpp = i["delta_pp"]
    if es:
        verb = "sube a" if dpp >= 0.05 else "baja a" if dpp <= -0.05 else "se mantiene en"
        head = f"La inflación {verb} {i['yoy']:.2f}% en {_mon_long(i['period'], lang)}"
        dek = (f"Los precios al consumidor subieron {i['yoy']:.2f}% en los últimos 12 meses, {abs(gap):.2f} pp "
               f"{'por encima' if gap > 0 else 'por debajo'} de la meta de 3% de Banxico. La inflación subyacente, que excluye "
               f"los precios más volátiles, se ubicó en {i.get('core', 0):.2f}%.")
        q = "¿Qué significa para Banxico?"
        ans = (f"La subyacente ({i.get('core', 0):.2f}%) es la medida que pesa en sus decisiones; sigue "
               f"{'por encima' if i.get('core', 0) > 3 else 'por debajo'} de la meta.")
    else:
        verb = "rises to" if dpp >= 0.05 else "falls to" if dpp <= -0.05 else "holds at"
        head = f"Inflation {verb} {i['yoy']:.2f}% in {_mon_long(i['period'], lang)}"
        dek = (f"Consumer prices rose {i['yoy']:.2f}% over 12 months, {abs(gap):.2f} pp {'above' if gap > 0 else 'below'} "
               f"Banxico's 3% target. Core inflation, which excludes the most volatile prices, stood at {i.get('core', 0):.2f}%.")
        q = "What does it mean for Banxico?"
        ans = f"Core inflation ({i.get('core', 0):.2f}%) weighs most in its decisions and remains {'above' if i.get('core', 0) > 3 else 'below'} target."
    out["inflation"] = {
        "head": head, "dek": dek, "q": q, "ans": ans,
        "chart_title": "Inflación general y subyacente" if es else "Headline and core inflation",
        "chart_sub": "Variación % anual, últimos 36 meses" if es else "Annual % change, last 36 months",
        "note": (("Nota: la banda sombreada es el intervalo de variabilidad de Banxico (2%–4%); la línea punteada, la meta de 3%. "
                  if es else "Note: the shaded band is Banxico's 2%–4% variability interval; the dotted line, the 3% target. ")
                 + obs + month(i["period"], lang) + "."),
        "source": SOURCE_LINE["inflation"][lang],
    }

    # --- Policy
    ra, st = p.get("real_ex_ante"), p.get("stance", "neutral")
    lo, hi = p.get("neutral_range", [1.8, 3.6])
    sp, sp12 = p.get("spread_bp"), p.get("spread_12m_ago_bp")
    if es:
        st_t = {"neutral": "dentro del rango neutral", "restrictive": "por encima del rango neutral",
                "accommodative": "por debajo del rango neutral"}[st]
        head = f"La tasa real de Banxico, {st_t}"
        dek = (f"Descontando la inflación esperada, la tasa de {p['rate']:.2f}% equivale a {ra:.2f}% real, "
               f"{st_t} que estima el banco central ({lo:.1f}%–{hi:.1f}%; Banxico, 2024). "
               f"El diferencial con la Fed es de {sp:.0f} pb, frente a {sp12:.0f} pb hace un año.").replace(
                   f"{st_t} que estima", "dentro del rango que estima" if st == "neutral" else f"{st_t} que estima")
        q = "¿Hay espacio para más recortes?"
        ans = f"Con la tasa real en {ra:.2f}%, la postura ya está {st_t} estimado por Banxico ({lo:.1f}%–{hi:.1f}%)."
    else:
        st_t = {"neutral": "inside the neutral range", "restrictive": "above the neutral range",
                "accommodative": "below the neutral range"}[st]
        head = f"Banxico's real rate, {st_t}"
        dek = (f"Net of expected inflation, the {p['rate']:.2f}% policy rate equals {ra:.2f}% in real terms, {st_t} "
               f"estimated by the central bank ({lo:.1f}%–{hi:.1f}%; Banxico, 2024). The spread over the Fed is {sp:.0f} bp, "
               f"versus {sp12:.0f} bp a year ago.")
        q = "Is there room for more cuts?"
        ans = f"With the real rate at {ra:.2f}%, the stance is already {st_t} ({lo:.1f}%–{hi:.1f}%)."
    out["policy"] = {
        "head": head, "dek": dek, "q": q, "ans": ans,
        "chart_title": "Tasa real ex ante" if es else "Ex-ante real policy rate",
        "chart_sub": ("%, tasa objetivo menos expectativa de inflación a 12 meses (media)" if es
                      else "%, policy rate minus mean 12-month inflation expectation"),
        "note": (("Nota: la banda sombreada es el rango estimado de la tasa neutral real (Banxico, 2024). " if es
                  else "Note: the shaded band is Banxico's (2024) estimated neutral real rate range. ")
                 + obs + day_year(p["date"], lang) + "."),
        "source": SOURCE_LINE["policy"][lang],
    }
    return out


def load_author_note(run_date: str) -> Optional[dict]:
    import yaml
    from config import ROOT
    path = ROOT / "config" / "nota_autor.yml"
    if not path.exists():
        return None
    d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    y, wk, _ = date.fromisoformat(run_date).isocalendar()
    if str(d.get("semana", "")).strip() != f"{y}-W{wk:02d}":
        return None
    es, en = (d.get("es") or "").strip(), (d.get("en") or "").strip()
    if not es:
        return None
    return {"es": es, "en": en or None, "estado": d.get("estado", "final"),
            "cita_es": (d.get("cita_es") or "").strip() or None, "cita_en": (d.get("cita_en") or "").strip() or None}


def post_v4_es(s: dict, order: List[str], ed: Dict[str, dict], agenda_rows: List[dict], note: Optional[dict]) -> str:
    lead = ed[order[0]]
    i, p, f, a = s["inflation"], s["policy"], s["fx"], s.get("activity")
    facts = {
        "fx": f"Tipo de cambio: {f['value']:.2f} pesos por dólar ({signed(f['chg_1w_pct'],1)}% en la semana).",
        "inflation": f"Inflación: {i['yoy']:.2f}% anual en {month_only(i['period'], 'es')}; subyacente, {i.get('core', 0):.2f}%.",
        "policy": f"Tasa real ex ante: {p.get('real_ex_ante'):.2f}%, {'dentro del' if p.get('stance') == 'neutral' else 'fuera del'} rango neutral de Banxico.",
        "activity": (f"IGAE: {signed(a['mom'],1)}% mensual en {month_only(a['period'], 'es')} ({signed(a['yoy'],1)}% anual)." if a else ""),
    }
    lead_line = lead["head"]
    if order[0] == "fx" and f.get("value_1w_ago"):
        lead_line += f": el dólar pasó de {f['value_1w_ago']:.2f} a {f['value']:.2f} pesos"
    others = "\n".join(facts[k] for k in order[1:] if facts.get(k))
    days: Dict[str, List[str]] = {}
    for r in agenda_rows[:3]:
        days.setdefault(r["day"], []).append(r["what"])
    nxt = "; ".join(f"{d_}, {' y '.join(w_)}" for d_, w_ in list(days.items())[:2])
    mine = ""
    if note:
        t_ = note["es"].strip()
        mine = f"Mi lectura: {t_[0].lower() + t_[1:]}\n\n"
    return (f"{lead_line}.\n\n"
            f"{lead['q']} {lead['ans']}\n\n"
            f"Los otros datos de la semana:\n{others}\n\n"
            f"{mine}"
            f"Esta semana: {nxt}.\n\n"
            f"{CTA_ES[order[0]]}\n\n"
            f"#EconomíaMexicana #Banxico #Macroeconomía")


def comment_v4_en(s: dict, order: List[str], ed: Dict[str, dict], note: Optional[dict]) -> str:
    lead = ed[order[0]]
    others = "\n".join(f"{ed[k]['head']}." for k in order[1:] if k in ed)
    mine = f"My take: {note['en']}\n\n" if note and note.get("en") else ""
    return (f"English version. {lead['head']}. {lead['q']} {lead['ans']}\n\n{others}\n\n{mine}"
            f"Official data from Banxico, INEGI and the Federal Reserve. Methodology, references and open-source code: {REPO_URL}")
