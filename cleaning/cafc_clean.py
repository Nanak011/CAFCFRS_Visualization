"""
cafc_clean.py - cleaning script for the CAFC fraud dataset (original 21-column bilingual layout).

What it does:
  1. Reads every column as text.
  2. Keeps the 13 English columns by POSITION and drops the 8 French duplicates.
  3. Fixes types: date, dollar loss, number of victims.
  4. Filters to 1 Jan 2024 - 30 Sep 2025.
  5. Checks and removes duplicate IDs.
  6. Strips the leading apostrophe from age range.
  7. Merges "Not Available / Not Specified / Unknown / blank" into one "Unknown".
  8. Adds Has_Loss, Year, Quarter, Month.
  9. Writes the clean CSV plus a summary file to help with data dictionary.

"""
import sys
import pandas as pd

START = pd.Timestamp("2024-01-01")
END = pd.Timestamp("2025-09-30")

# 0-based positions of the English columns in the original 21-column file
# (A=0 ... U=20). The French duplicates are positions 3, 5, 7, 9, 11, 13, 15, 18.
KEEP = {
    0: "ID",
    1: "Date",
    2: "Received_Type",
    4: "Country",
    6: "Province",
    8: "Fraud_Type",
    10: "Solicitation",
    12: "Gender",
    14: "Language",
    16: "Age_Range",
    17: "Complaint_Type",
    19: "Victims",
    20: "Loss",
}
CATEGORY_COLS = ["Received_Type", "Country", "Province", "Fraud_Type", "Solicitation",
                 "Gender", "Language", "Age_Range", "Complaint_Type"]
UNKNOWN_WORDS = {"not available", "not specified", "unknown", "n/a", "na", ""}
# a label that STARTS with one of these words, e.g. "Not Available / Non disponible"
UNKNOWN_PREFIX = r"^(not available|not specified|unknown|n/a)\b"


ROW_LOG = [] 


def log(step, df):
    ROW_LOG.append((step, len(df)))
    print(f"[rows] {step:<45} {len(df):>9,}")


def main(raw_path, out_path):
    df = pd.read_csv(raw_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    print(f"Columns found: {len(df.columns)}")
    for i, c in enumerate(df.columns):
        print(f"  {i:>2}  {c}")
    if len(df.columns) != 21:
        sys.exit("Expected 21 columns.")
    log("raw file", df)

    # 2. keep English columns, rename
    df = df.iloc[:, list(KEEP.keys())].copy()
    df.columns = list(KEEP.values())
    for c in df.columns:
        df[c] = df[c].str.strip()

    # 3. types
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    bad_dates = df["Date"].isna().sum()
    loss_text = df["Loss"].str.replace(r"[$,\s]", "", regex=True)
    df["Loss"] = pd.to_numeric(loss_text, errors="coerce")
    bad_loss = df["Loss"].isna().sum()
    df["Victims"] = pd.to_numeric(df["Victims"], errors="coerce")
    bad_vict = df["Victims"].isna().sum()
    print(f"[check] unparsed dates: {bad_dates}, unparsed loss: {bad_loss}, unparsed victims: {bad_vict}")
    print(f"[check] negative loss values: {(df['Loss'] < 0).sum()}")
    df = df[df["Date"].notna()]
    log("after dropping rows with unreadable dates", df)

    # 4. date filter
    df = df[(df["Date"] >= START) & (df["Date"] <= END)]
    log("after date filter 2024-01-01..2025-09-30", df)

    # 5. duplicate IDs
    dup_ids = df["ID"].duplicated(keep=False).sum()
    print(f"[check] rows sharing an ID with another row: {dup_ids}")
    df = df.drop_duplicates(subset="ID", keep="first")
    log("after removing duplicate IDs", df)

    # 6. age range apostrophe
    df["Age_Range"] = df["Age_Range"].str.lstrip("'")
    # 6b. Excel turns text like "10 - 19" into the date 19-Oct when a CSV is opened in it.
    # Rewriting "10 - 19" as "10 to 19" keeps the label readable and safe in Excel.
    is_band = df["Age_Range"].str.match(r"^\d+\s*-\s*\d+$")
    print(f"[check] Age_Range labels rewritten from 'N - M' to 'N to M': {int(is_band.sum()):,}")
    df["Age_Range"] = df["Age_Range"].str.replace(r"^(\d+)\s*-\s*(\d+)$", r"\1 to \2", regex=True)

    # 7. unknown harmonisation
    # Matches the whole word list OR a bilingual form such as "Not Available / Non disponible"
    for c in CATEGORY_COLS:
        low = df[c].str.lower().str.strip()
        mask = low.isin(UNKNOWN_WORDS) | low.str.match(UNKNOWN_PREFIX)
        print(f"[check] {c}: {int(mask.sum()):,} values set to Unknown")
        df.loc[mask, c] = "Unknown"

    # 7b. Keep only the English half of bilingual age labels, e.g. "Deceased / Décédé" -> "Deceased",
    # "Business / Entreprise" -> "Business". (Runs after step 7, so "Not Available / ..." is already Unknown.)
    bilingual = df["Age_Range"].str.contains(" / ", regex=False)
    print(f"[check] Age_Range bilingual labels reduced to English: {int(bilingual.sum()):,}")
    df.loc[bilingual, "Age_Range"] = df.loc[bilingual, "Age_Range"].str.split(" / ").str[0].str.strip()

    print("[check] Country counts:")
    print(df["Country"].value_counts().head(10).to_string())
    # df = df[df["Country"] == "Canada"]   
    # log("after keeping Canada only", df)

    # 8. derived fields
    df["Has_Loss"] = (df["Loss"] > 0).map({True: "Yes", False: "No"})
    df["Year"] = df["Date"].dt.year
    df["Quarter"] = "Q" + df["Date"].dt.quarter.astype(str)
    df["Month"] = df["Date"].dt.month
    log("final analysis rows", df)
    print(f"[rows] zero loss: {(df['Loss'] == 0).sum():,}   loss > 0: {(df['Loss'] > 0).sum():,}   "
          f"blank/unreadable loss: {df['Loss'].isna().sum():,}")

    # 9. outputs
    df.to_csv(out_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    rows = []
    for c in df.columns:
        s = df[c]
        is_number_or_date = pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s)
        rows.append({
            "column": c,
            "dtype": str(s.dtype),
            "distinct": s.nunique(dropna=True),
            "blank_or_NaN": int(s.isna().sum()),
            "unknown_label": 0 if is_number_or_date else int((s == "Unknown").sum()),
            "min": s.min() if is_number_or_date else "",
            "max": s.max() if is_number_or_date else "",
        })
    summary = pd.DataFrame(rows)
    summary["pct_missing_or_unknown"] = ((summary["blank_or_NaN"] + summary["unknown_label"]) / len(df) * 100).round(1)
    summary_path = out_path.rsplit(".", 1)[0] + "_summary.csv"
    summary.to_csv(summary_path, index=False)
    rowlog_path = out_path.rsplit(".", 1)[0] + "_rowlog.csv"
    pd.DataFrame(ROW_LOG, columns=["step", "rows_after"]).to_csv(rowlog_path, index=False)
    print(f"Wrote {out_path}, {summary_path} and {rowlog_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python cafc_clean.py raw.csv cafc_clean.csv")
    main(sys.argv[1], sys.argv[2])