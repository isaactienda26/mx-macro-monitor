"""Temporary: fetch BIS peer data with the production code and print a summary."""
import sys
sys.path.insert(0, "src")
import sources
d, w = sources.fetch_peers()
print("warnings", w)
for k, df in d.items():
    print("==", k, df.shape)
    print(df.sort_values("TIME_PERIOD").groupby("REF_AREA").tail(1).to_string())
