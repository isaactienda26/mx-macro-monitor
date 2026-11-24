"""Temporary probe: check BIS SDMX endpoints for peer data (no key needed)."""
import requests
B = "https://stats.bis.org/api/v1/data"
tests = {
  "cbpol": f"{B}/WS_CBPOL/D.BR+CL+CO+PE+MX+US/all?startPeriod=2026-10-01&format=csv",
  "cbpol_m": f"{B}/WS_CBPOL/M.BR+CL+CO+PE+MX+US/all?startPeriod=2026-06-01&format=csv",
  "cpi": f"{B}/WS_LONG_CPI/M.BR+CL+CO+PE+MX+US.771/all?startPeriod=2026-06&format=csv",
  "xru_d": f"{B}/WS_XRU/D.BR+CL+CO+PE+MX.BRL+CLP+COP+PEN+MXN.A/all?startPeriod=2026-11-01&format=csv",
  "xru_d2": f"{B}/WS_XRU/D..../all?startPeriod=2026-11-15&format=csv",
}
for k, u in tests.items():
    try:
        r = requests.get(u, timeout=60)
        lines = r.text.strip().splitlines()
        print("==", k, r.status_code, len(lines))
        for ln in (lines[:2] + lines[-6:]):
            print("   ", ln[:220])
    except Exception as e:
        print("==", k, "ERR", e)
# FRED fallbacks
for sid in ["DEXBZUS", "DEXMXUS", "DTWEXBGS"]:
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=2026-11-01", timeout=60)
    print("FRED", sid, r.status_code, r.text.strip().splitlines()[-2:])
