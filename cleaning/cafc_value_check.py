"""
cafc_value_check.py - read-only checks on the cleaned CAFC file. It changes nothing.

Usage:  python cafc_value_check.py 02_clean\\cafc_clean.csv
Save the output as evidence:  python cafc_value_check.py 02_clean\\cafc_clean.csv | Tee-Object 02_clean\\value_check_output.txt   (PowerShell)

What it prints:
  1. Every distinct value of each category column with its row count (so you can scan for odd labels)
  2. Warnings: labels that differ only by capital letters, labels with non-English letters (e.g. French leftovers)
  3. The 10 largest losses and their share of total loss
  4. Consistency checks: Complaint_Type vs Has_Loss, Victims vs Loss
  5. Reports per month (to spot gaps)
"""
import sys
import pandas as pd

CATS = ["Received_Type", "Country", "Province", "Fraud_Type", "Solicitation",
        "Gender", "Language", "Age_Range", "Complaint_Type"]


def heading(t):
    print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


def main(path):
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"ID": str})
    print(f"Rows: {len(df):,}   Columns: {len(df.columns)}")

    heading("1. DISTINCT VALUES PER CATEGORY COLUMN")
    for c in CATS:
        vc = df[c].value_counts(dropna=False)
        print(f"\n--- {c}: {len(vc)} distinct values")
        print(vc.head(80).to_string())
        if len(vc) > 80:
            print(f"... {len(vc) - 80} more values not shown (rarest ones)")

    heading("2. WARNINGS")
    found = False
    for c in CATS:
        vals = df[c].dropna().astype(str).unique()
        lower = {}
        for v in vals:
            lower.setdefault(v.lower().strip(), []).append(v)
        for k, group in lower.items():
            if len(group) > 1:
                found = True
                print(f"[case/space variants] {c}: {group}")
        for v in vals:
            if not v.isascii():
                found = True
                print(f"[non-ASCII characters] {c}: {v!r}")
        for v in vals:
            if " / " in v:
                found = True
                print(f"[bilingual label?] {c}: {v!r}")
    if not found:
        print("No warnings.")

    heading("3. TEN LARGEST LOSSES")
    top = df.sort_values("Loss", ascending=False).head(10)
    print(top[["ID", "Date", "Fraud_Type", "Solicitation", "Province", "Victims", "Loss"]].to_string(index=False))
    total = df["Loss"].sum()
    print(f"\nTotal loss: {total:,.2f}")
    print(f"Top 1 share: {top['Loss'].iloc[0] / total:.1%}   Top 10 share: {top['Loss'].sum() / total:.1%}")
    pos = df[df["Loss"] > 0]["Loss"]
    print(f"Median loss (loss > 0): {pos.median():,.2f}   Mean loss (loss > 0): {pos.mean():,.2f}")

    heading("4. CONSISTENCY CHECKS")
    print("\nComplaint_Type x Has_Loss (row counts):")
    print(pd.crosstab(df["Complaint_Type"], df["Has_Loss"]).to_string())
    print("\nVictims by Complaint_Type (sum):")
    print(df.groupby("Complaint_Type")["Victims"].sum().to_string())
    print(f"\nRows with Loss > 0 but Victims == 0: {((df['Loss'] > 0) & (df['Victims'] == 0)).sum():,}")
    print(f"Rows with Loss == 0 but Victims == 1: {((df['Loss'] == 0) & (df['Victims'] == 1)).sum():,}")
    print(f"Distinct values of Victims: {sorted(df['Victims'].unique().tolist())}")

    heading("5. REPORTS PER MONTH")
    d = pd.to_datetime(df["Date"])
    print(df.groupby([d.dt.year.rename("Year"), d.dt.month.rename("Month")]).size().to_string())
    print(f"\nFirst date: {d.min().date()}   Last date: {d.max().date()}   Distinct days: {d.nunique()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python cafc_value_check.py cafc_clean.csv")
    main(sys.argv[1])