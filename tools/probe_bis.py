"""Temporary: fetch peer data (BIS + FRED H.10) with production code and save cache."""
import sys
sys.path.insert(0, "src")
import sources
d, w = sources.fetch_peers()
print("warnings", w)
s = sources.build_session()
data = {k: sources.fetch_fred(s, sid) for k, sid in {"usd_brl": "DEXBZUS", "usd_mxn_h10": "DEXMXUS", "usd_broad": "DTWEXBGS"}.items()}
sources.save_cache(data)
for k, v in data.items():
    print(k, v.tail(8).to_dict())
