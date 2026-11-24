# Mexico Macro Monitor

Automated Python ETL pipeline that queries official Mexican macroeconomic series from **Banxico (SIE API)** and **INEGI (BIE API v2.0)**, computes month-over-month (MoM) and year-over-year (YoY) changes, flags movements exceeding 1 standard deviation over a 60-month rolling window, publishes bilingual one-page Markdown bulletins, and exports high-resolution PNG tables (300 DPI) ready for LinkedIn every Monday.

## Indicators Tracked

| Indicator | Source | Series ID | Frequency | Variation Metric |
| :--- | :--- | :---: | :---: | :---: |
| Headline Inflation (CPI / INPC) | Banxico SIE | `SP1` | Monthly | % MoM / % YoY |
| Policy Interest Rate | Banxico SIE | `SF61745` | Daily | bps MoM / bps YoY |
| USD/MXN FIX Exchange Rate | Banxico SIE | `SF43718` | Daily (Close) | % MoM / % YoY |
| Economic Activity (IGAE SA, 2018=100) | INEGI BIE | `737121` | Monthly | % MoM / % YoY |

## Outputs Generated

- `bulletins/latest_es.md` and `bulletins/latest_en.md`: One-page executive Markdown bulletins.
- `bulletins/table_es.png` and `bulletins/table_en.png`: 300 DPI institutional table visuals formatted for LinkedIn.

## Methodological Design

- **60-Month Rolling Window:** Standard deviations are evaluated over a 60-month rolling window to avoid distortion from historical regime breaks (e.g., pre-2001 monetary policy regimes).
- **Basis Points for Policy Rate:** Policy rate shifts are computed in basis points rather than percentage changes.
- **Exact Calendar Lookup (`asof`):** Daily series (FIX and Policy Rate) compare the latest business day close against the nearest prior observation 1 month and 12 months earlier.

## Setup

1. Clone the repository and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Obtain free API tokens from [Banxico SIE](https://www.banxico.org.mx/SieAPIRest/service/v1/token) and [INEGI API](https://www.inegi.org.mx/app/api/indicadores/interna_v1_1/tokenVerify.aspx).
3. Copy `.env.example` to `.env` and add your tokens.
4. Run locally:
   ```bash
   python src/macro_monitor.py
   ```
5. For GitHub Actions automation, add `BANXICO_TOKEN` and `INEGI_TOKEN` under **Settings > Secrets and variables > Actions**.

## Author

**Isaac Tienda**
