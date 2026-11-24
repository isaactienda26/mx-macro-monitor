"""One-off helper: print Banxico SIE metadata (title, frequency, period) for candidate IDs."""
import os, sys, requests
tok = os.environ["BANXICO_TOKEN"]
ids = []
for spec in sys.argv[1:]:
    if "-" in spec:
        pre = spec.rstrip("0123456789-").split("-")[0]
        a, b = spec[len(pre):].split("-")
        ids += [f"{pre}{i}" for i in range(int(a), int(b) + 1)]
    else:
        ids.append(spec)
for i in range(0, len(ids), 80):
    chunk = ",".join(ids[i:i+80])
    r = requests.get(f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{chunk}",
                     headers={"Bmx-Token": tok}, timeout=60)
    if r.status_code != 200:
        print("HTTP", r.status_code, chunk[:60]); continue
    for s in r.json()["bmx"]["series"]:
        print(f'{s["idSerie"]}\t{s.get("periodicidad")}\t{s.get("fechaInicio")}-{s.get("fechaFin")}\t{s.get("titulo")}')
for sid in ["DFEDTARU"]:
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=60)
    print("FRED", sid, r.status_code, r.text.strip().splitlines()[-1] if r.ok else "")
