import pandas as pd
import os

KBO_DIR = os.path.expanduser("~/kansenradar_kbo")
OUT_DIR = os.path.expanduser("~/Documents/kansenradar/output")
os.makedirs(OUT_DIR, exist_ok=True)

NACE_PREFIXES = ["7311", "7312", "7021", "7022", "9003"]

# ─── STAP 2: Filter activity.csv in chunks ────────────────────────────────────
print("Stap 2 — activity.csv filteren in chunks...")

nace_counts = {p: 0 for p in NACE_PREFIXES}
chunks_filtered = []
total_rows = 0

for chunk in pd.read_csv(
    os.path.join(KBO_DIR, "activity.csv"),
    chunksize=100_000,
    dtype=str,
):
    total_rows += len(chunk)
    mask = chunk["NaceCode"].str.startswith(tuple(NACE_PREFIXES), na=False)
    filtered = chunk[mask].copy()
    if not filtered.empty:
        for prefix in NACE_PREFIXES:
            nace_counts[prefix] += filtered["NaceCode"].str.startswith(prefix).sum()
        chunks_filtered.append(filtered)

activity_filtered = pd.concat(chunks_filtered, ignore_index=True)
activity_filtered.to_csv(os.path.join(KBO_DIR, "activity_filtered.csv"), index=False)

print(f"  Totaal gescand: {total_rows:,} rijen")
print(f"  Gefilterd:      {len(activity_filtered):,} rijen")
for prefix, count in nace_counts.items():
    print(f"  NACE {prefix}xx: {count:,}")

# ─── STAP 3: Filter enterprise.csv ────────────────────────────────────────────
print("\nStap 3 — enterprise.csv filteren...")

enterprise = pd.read_csv(os.path.join(KBO_DIR, "enterprise.csv"), dtype=str)
print(f"  TypeOfEnterprise waarden: {enterprise['TypeOfEnterprise'].value_counts().to_dict()}")

enterprise_filtered = enterprise[
    (enterprise["Status"] == "AC") &
    (enterprise["TypeOfEnterprise"] == "2")
].copy()

enterprise_filtered.to_csv(os.path.join(KBO_DIR, "enterprise_filtered.csv"), index=False)
print(f"  Actieve rechtspersonen: {len(enterprise_filtered):,}")

# ─── STAP 4: Join activity + enterprise ───────────────────────────────────────
print("\nStap 4 — activity + enterprise joinen...")

joined = activity_filtered.merge(
    enterprise_filtered[["EnterpriseNumber", "Status", "TypeOfEnterprise", "JuridicalForm", "StartDate"]],
    left_on="EntityNumber",
    right_on="EnterpriseNumber",
    how="inner"
)
joined.drop(columns=["EnterpriseNumber"], inplace=True)
joined.to_csv(os.path.join(KBO_DIR, "joined.csv"), index=False)
print(f"  Na join: {len(joined):,} rijen ({joined['EntityNumber'].nunique():,} unieke ondernemingen)")

# ─── STAP 5: Adressen toevoegen ───────────────────────────────────────────────
print("\nStap 5 — adressen toevoegen...")

address = pd.read_csv(os.path.join(KBO_DIR, "address.csv"), dtype=str)
print(f"  TypeOfAddress waarden: {address['TypeOfAddress'].value_counts().to_dict()}")

# Voorkeur: REGO (maatschappelijke zetel), anders eerste beschikbare
address_prio = address[address["TypeOfAddress"] == "REGO"].copy()
address_other = address[address["TypeOfAddress"] != "REGO"].copy()

# Per bedrijf: neem REGO als die bestaat, anders eerste andere
address_main = pd.concat([address_prio, address_other]).drop_duplicates(
    subset=["EntityNumber"], keep="first"
)[["EntityNumber", "Zipcode", "MunicipalityNL", "StreetNL", "HouseNumber"]].copy()

address_main.rename(columns={
    "Zipcode": "postcode",
    "MunicipalityNL": "gemeente",
    "StreetNL": "straat",
    "HouseNumber": "huisnummer"
}, inplace=True)

joined_addr = joined.merge(address_main, on="EntityNumber", how="left")
print(f"  Adressen toegevoegd: {joined_addr['postcode'].notna().sum():,}/{len(joined_addr):,}")

# ─── STAP 6: Namen toevoegen ──────────────────────────────────────────────────
print("\nStap 6 — namen toevoegen...")

denom = pd.read_csv(os.path.join(KBO_DIR, "denomination.csv"), dtype=str)

# Voorkeur: TypeOfDenomination 001 in NL (Language=2), anders eerste beschikbare
denom_nl = denom[(denom["Language"] == "2") & (denom["TypeOfDenomination"] == "001")].copy()
denom_fallback = denom[denom["TypeOfDenomination"] == "001"].copy()
denom_any = denom.copy()

denom_best = pd.concat([denom_nl, denom_fallback, denom_any]).drop_duplicates(
    subset=["EntityNumber"], keep="first"
)[["EntityNumber", "Denomination"]].copy()

denom_best.rename(columns={"Denomination": "naam"}, inplace=True)

joined_named = joined_addr.merge(denom_best, on="EntityNumber", how="left")
print(f"  Namen toegevoegd: {joined_named['naam'].notna().sum():,}/{len(joined_named):,}")

# ─── STAP 7: Regio ────────────────────────────────────────────────────────────
print("\nStap 7 — regio bepalen...")

def bepaal_regio(postcode):
    try:
        pc = int(postcode)
    except (ValueError, TypeError):
        return "Onbekend"
    if 2000 <= pc <= 2999:
        return "Antwerpen"
    elif 9000 <= pc <= 9999:
        return "Oost-Vlaanderen"
    elif 8000 <= pc <= 8999:
        return "West-Vlaanderen"
    elif 3000 <= pc <= 3499:
        return "Vlaams-Brabant"
    elif 3500 <= pc <= 3999:
        return "Limburg"
    elif 1000 <= pc <= 1299:
        return "Brussel"
    else:
        return "Overig België"

joined_named["regio"] = joined_named["postcode"].apply(bepaal_regio)
print(f"  Regio-verdeling:\n{joined_named['regio'].value_counts().to_string()}")

# ─── STAP 8: Prioriteit ───────────────────────────────────────────────────────
print("\nStap 8 — prioriteit berekenen...")

VLAANDEREN = {"Antwerpen", "Oost-Vlaanderen", "West-Vlaanderen", "Vlaams-Brabant", "Limburg"}

def bepaal_prioriteit(row):
    regio = row["regio"]
    nace = str(row["NaceCode"])
    if nace.startswith("7311") and regio in VLAANDEREN:
        return 1
    elif (nace.startswith("7021") or nace.startswith("7312")) and regio in VLAANDEREN:
        return 2
    else:
        return 3

joined_named["prioriteit"] = joined_named.apply(bepaal_prioriteit, axis=1)
print(f"  Prioriteit 1: {(joined_named['prioriteit'] == 1).sum():,}")
print(f"  Prioriteit 2: {(joined_named['prioriteit'] == 2).sum():,}")
print(f"  Prioriteit 3: {(joined_named['prioriteit'] == 3).sum():,}")

# ─── STAP 9: Exporteer ────────────────────────────────────────────────────────
print("\nStap 9 — exporteren...")

EXPORT_COLS = ["EntityNumber", "naam", "straat", "gemeente", "postcode", "regio", "NaceCode", "prioriteit"]

# Dedupliceer op EntityNumber — bewaar rij met laagste prioriteit (beste NACE-match)
final = joined_named.sort_values("prioriteit").drop_duplicates(subset=["EntityNumber"], keep="first")
final = final.rename(columns={"EntityNumber": "ondernemingsnummer", "NaceCode": "nace_code"})

export_cols_renamed = ["ondernemingsnummer", "naam", "straat", "gemeente", "postcode", "regio", "nace_code", "prioriteit"]

# Alle bureaus
alle = final[export_cols_renamed].sort_values(["prioriteit", "gemeente"])
alle.to_csv(os.path.join(OUT_DIR, "kansenradar_alle_bureaus.csv"), index=False)
print(f"  kansenradar_alle_bureaus.csv: {len(alle):,} bedrijven")

# Top prospects
top = final[
    (final["prioriteit"].isin([1, 2])) &
    (final["regio"].isin(VLAANDEREN))
][export_cols_renamed].sort_values(["prioriteit", "naam"]).head(500)
top.to_csv(os.path.join(OUT_DIR, "kansenradar_top_prospects.csv"), index=False)
print(f"  kansenradar_top_prospects.csv: {len(top):,} bedrijven")

# ─── STAP 10: Eindrapport ─────────────────────────────────────────────────────
print("\n" + "="*60)
print("EINDRAPPORT")
print("="*60)
print(f"Totaal unieke bedrijven:  {final['ondernemingsnummer'].nunique():,}")
print(f"\nVerdeling per NACE-prefix:")
for prefix in NACE_PREFIXES:
    n = final["nace_code"].str.startswith(prefix).sum()
    print(f"  {prefix}xx: {n:,}")
print(f"\nVerdeling per regio:")
print(final["regio"].value_counts().to_string())
print(f"\nTop prospects (prio 1+2, Vlaanderen): {len(top):,}")
print(f"\nDatakwaliteit:")
print(f"  Zonder naam:    {final['naam'].isna().sum():,}")
print(f"  Zonder adres:   {final['postcode'].isna().sum():,}")
print(f"  Zonder gemeente:{final['gemeente'].isna().sum():,}")
print("\nKlaar. Output staat in ~/Documents/kansenradar/output/")
