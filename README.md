# CAFC fraud reports: data cleaning for ITS68404

Cleaning scripts and documentation for a Tableau dashboard on reported fraud in Canada (coursework, ITS68404 Data Visualization, Taylor's / IIMS College).


## Source data
- Dataset: Canadian Anti-Fraud Centre (RCMP), Fraud Reporting System Dataset, Open Government Portal of Canada.
- Page: https://open.canada.ca/data/en/dataset/6a09c998-cddb-4a22-beff-4dca67ab892f
- Coverage in the file: 2021-01-01 to 2025-09-30 (extract dated 2025-10-01). Downloaded on 24 Oct 2026.
- SHA-256 of the raw file I used: `C46F61591DA71EADD91C3E47ED3E3CB8102880A8861C027AB7A35182C8BD719C`
- The raw file (75.5 MB) is not in this repository. Download it from the page above and save it as `01_raw/cafc_raw.csv` (see `01_raw/README.md`).
- Contains information licensed under the Open Government Licence - Canada.

## Repository contents
| Path | What it is |
|---|---|
| `cleaning/cafc_clean.py` | Cleaning script |
| `cleaning/cafc_value_check.py` | Read-only checks on the cleaned file |
| `02_clean/cafc_clean.csv` | Cleaned data used in the dashboard (85,458 rows, 17 columns) |
| `02_clean/cafc_clean_rowlog.csv` | Row count after each cleaning step |
| `02_clean/cafc_clean_summary.csv` | Type, distinct values, range and % unknown per column |
| `02_clean/run_output.txt` | Console output of the cleaning run |
| `02_clean/value_check_output.txt` | Output of the value check |
| `change_log.xlsx` | Change log and decisions sheet |

## How to reproduce
1. Download the raw CSV and save it as `01_raw/cafc_raw.csv`.
2. Install pandas: `pip install pandas`.
3. From the repository folder run:
```
python cleaning/cafc_clean.py 01_raw/cafc_raw.csv 02_clean/cafc_clean.csv
python cleaning/cafc_value_check.py 02_clean/cafc_clean.csv
```
Expected: 350,361 raw rows, 85,458 after the date filter, 0 duplicate IDs.

## What the cleaning script does
1. Reads every column as text and keeps the 13 English columns by position. The 8 French duplicate columns are dropped (the raw file has 21 columns).
2. Converts Date (M/D/YYYY) to a date, Loss (e.g. "$1,234.00") to a number and Number of Victims to a number. No value failed to parse.
3. Keeps reports dated 2024-01-01 to 2025-09-30 (the last report in the data is 2025-09-29).
4. Checks for duplicate IDs (none found).
5. Removes the leading apostrophe from age ranges and rewrites "10 - 19" as "10 to 19", because Excel converts "10 - 19" into a date when a CSV is opened.
6. Sets labels such as "Not Available", "Not Specified", "Unknown", blank, or bilingual forms such as "Not Available / non disponible" to one label, "Unknown", in the nine category columns. Genuine categories such as "Other" are kept.
7. Reduces bilingual age labels to English ("Deceased / Décédé" becomes "Deceased", "Business / Entreprise" becomes "Business").
8. Adds Has_Loss (Yes/No), Year, Quarter and Month.
9. Writes the cleaned CSV, a summary file and a row-count log.

## Row counts
| Step | Rows |
|---|---|
| Raw file | 350,361 |
| After date filter (2024-01-01 to 2025-09-30) | 85,458 (264,903 removed) |
| After removing duplicate IDs | 85,458 (0 removed) |
| Final analysis rows | 85,458 |
| Rows with no financial loss | 58,933 (69.0%) |
| Rows with a loss above zero | 26,525 (31.0%) |

## Columns in the cleaned file
ID, Date, Received_Type, Country, Province, Fraud_Type, Solicitation, Gender, Language, Age_Range, Complaint_Type, Victims, Loss, Has_Loss, Year, Quarter, Month. Victims is a 0/1 flag (1 only on "Victim" complaints). Loss is in the currency stated by the CAFC definitions document.

## Checks
- `cafc_value_check.py` lists every distinct value per category column, flags case or language variants, and reports the largest losses, consistency checks and reports per month.
- Pivot tables in Excel gave the same totals as the script: 85,458 reports, 58,950 victim reports and $1,186,937,312 total loss.

## Decisions
- Non-Canadian rows are kept in the data; the dashboard map is filtered to Canada.
- Zero-loss reports are kept and flagged with Has_Loss.
- Outliers are kept (largest single loss $23,615,000).
- Full list of decisions: `change_log.xlsx`, sheet Decisions.

## Known issues in the data
- 69.0% of reports have no loss; only "Victim" complaints ever carry a loss.
- Identity Fraud has 16,779 victim reports and no recorded loss.
- Unknown values: Country 19.5%, Province 20.7%, Age_Range 28.2%, Gender 28.4%; Solicitation has 4.1% Unknown plus 26.7% "Other/unknown" (source category).
- Loss is heavy-tailed: median $5,000, mean $44,748 (reports with a loss), largest $23,615,000.
- Monthly report counts fall in late 2025 (Aug 3,215; Sep 2,198), possibly reporting lag.
- Reports are self-reported to the CAFC.
- Source encoding error: the Country value "C⌠te d'Ivoire" (2 rows) is unchanged.

## AI assistance
The cleaning and check scripts were written with the help of an AI assistant (Claude). I ran them on the real data, checked their output and chose which fixes to keep.