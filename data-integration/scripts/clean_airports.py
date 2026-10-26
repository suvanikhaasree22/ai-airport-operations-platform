
from pathlib import Path

import pandas as pd


# Resolve paths relative to this script, not the terminal's current directory.
PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"

AIRPORTS_FILE = RAW_DIR / "airports.csv"
SELECTED_FILE = RAW_DIR / "airports_selected.csv"
RUNWAYS_FILE = RAW_DIR / "runways.csv"


def require_file(path):
    """Stop with a clear message if an input file is missing."""
    if not path.is_file():
        raise FileNotFoundError(f"Required input file not found: {path}")


def require_columns(df, columns, filename):
    """Check that an input CSV contains the required columns."""
    missing = sorted(set(columns) - set(df.columns))
    if missing:
        raise ValueError(
            f"{filename} is missing required columns: {missing}"
        )


def report_missing_values(df, fields, label):
    """Report missing or blank values in important fields."""
    print(f"\nMissing-value report: {label}")
    for field in fields:
        if field not in df.columns:
            continue

        values = df[field]
        missing = values.isna()

        if pd.api.types.is_string_dtype(values.dtype) or values.dtype == object:
            missing = missing | values.astype("string").str.strip().eq("").fillna(False)

        print(f"  {field}: {int(missing.sum())}")


def remove_exact_duplicates(df, label):
    """Remove identical rows and return the cleaned data and count removed."""
    before = len(df)
    result = df.drop_duplicates().copy()
    removed = before - len(result)

    print(f"{label} exact duplicate rows removed: {removed}")
    return result, removed


def clean_airports():
    # Check inputs before attempting to read them.
    for path in (AIRPORTS_FILE, SELECTED_FILE, RUNWAYS_FILE):
        require_file(path)

    # Read raw files without modifying them.
    airports = pd.read_csv(AIRPORTS_FILE)
    selected = pd.read_csv(
        SELECTED_FILE,
        dtype={"iata_code": "string"},
    )
    runways = pd.read_csv(RUNWAYS_FILE)

    require_columns(
        airports,
        ["id", "iata_code", "name", "latitude_deg", "longitude_deg"],
        "airports.csv",
    )
    require_columns(
        selected,
        ["iata_code"],
        "airports_selected.csv",
    )
    require_columns(
        runways,
        ["id", "airport_ref", "airport_ident"],
        "runways.csv",
    )

    print("Source record counts:")
    print(f"  Airports: {len(airports)}")
    print(f"  Selected-airport entries: {len(selected)}")
    print(f"  Runways: {len(runways)}")

    # Normalize selection codes and reject blank or duplicate selections.
    selected["iata_code"] = (
        selected["iata_code"].astype("string").str.strip().str.upper()
    )
    airports["iata_code"] = (
        airports["iata_code"].astype("string").str.strip().str.upper()
    )

    if selected["iata_code"].isna().any() or selected["iata_code"].eq("").any():
        raise ValueError(
            "airports_selected.csv contains missing or blank IATA codes."
        )

    selected_codes = selected["iata_code"]

    if selected_codes.duplicated().any():
        duplicates = selected_codes[
            selected_codes.duplicated(keep=False)
        ].unique().tolist()
        raise ValueError(f"Duplicate selected IATA codes: {duplicates}")

    # Keep only source records for the agreed target airports.
    selected_airports = airports[
        airports["iata_code"].isin(selected_codes)
    ].copy()

    # Remove only fully identical rows; don't arbitrarily choose between
    # different records that happen to share an IATA code.
    selected_airports, airport_duplicates_removed = remove_exact_duplicates(
        selected_airports, "Selected airport"
    )

    match_counts = selected_airports["iata_code"].value_counts()
    missing_codes = sorted(set(selected_codes) - set(match_counts.index))
    ambiguous_codes = sorted(
        match_counts[match_counts > 1].index.tolist()
    )

    if missing_codes or ambiguous_codes:
        raise ValueError(
            "Airport matching failed. "
            f"Unmatched IATA codes: {missing_codes}; "
            f"IATA codes with conflicting/multiple records: {ambiguous_codes}"
        )

    if selected_airports["id"].isna().any():
        raise ValueError("Selected airport records contain missing airport IDs.")

    if selected_airports["id"].duplicated().any():
        raise ValueError("Selected airport records contain duplicate airport IDs.")

    # Coordinates are essential for locating airports; reject invalid values.
    for column in ("latitude_deg", "longitude_deg"):
        selected_airports[column] = pd.to_numeric(
            selected_airports[column], errors="coerce"
        )

    invalid_coordinates = (
        selected_airports["latitude_deg"].isna()
        | selected_airports["longitude_deg"].isna()
        | ~selected_airports["latitude_deg"].between(-90, 90)
        | ~selected_airports["longitude_deg"].between(-180, 180)
    )

    if invalid_coordinates.any():
        bad_codes = selected_airports.loc[
            invalid_coordinates, "iata_code"
        ].tolist()
        raise ValueError(
            f"Selected airports have missing or invalid coordinates: {bad_codes}"
        )

    # Report missing fields in the selected airport records.
    report_missing_values(
        selected_airports,
        ["id", "iata_code", "name", "latitude_deg", "longitude_deg"],
        "selected airports",
    )

    # OurAirports runways.airport_ref references airports.id.
    runways["airport_ref"] = pd.to_numeric(
        runways["airport_ref"], errors="coerce"
    )

    airport_ids = selected_airports["id"]
    selected_runways = runways[
        runways["airport_ref"].isin(airport_ids)
    ].copy()

    # A runway without an ID or airport reference cannot be reliably used.
    before_identifier_filter = len(selected_runways)
    selected_runways = selected_runways.dropna(
        subset=["id", "airport_ref"]
    ).copy()
    missing_identifiers_removed = (
        before_identifier_filter - len(selected_runways)
    )

    print(
        "Selected runway rows removed for missing runway ID "
        f"or airport reference: {missing_identifiers_removed}"
    )

    # Remove identical runway rows; fail on conflicting duplicate runway IDs.
    selected_runways, runway_duplicates_removed = remove_exact_duplicates(
        selected_runways, "Selected runway"
    )

    if selected_runways["id"].duplicated().any():
        duplicate_ids = selected_runways.loc[
            selected_runways["id"].duplicated(keep=False), "id"
        ].unique().tolist()
        raise ValueError(
            "Conflicting runway records share runway IDs: "
            f"{duplicate_ids[:20]}"
        )

    # Ensure each retained runway references one of the selected airports.
    if not selected_runways["airport_ref"].isin(airport_ids).all():
        raise ValueError(
            "Some processed runways reference airports outside the selection."
        )

    report_missing_values(
        selected_runways,
        [
            "id",
            "airport_ref",
            "airport_ident",
            "length_ft",
            "width_ft",
            "surface",
            "le_ident",
            "he_ident",
        ],
        "selected runways",
    )

    # Write processed files only. Never write to the raw input paths.
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    airport_output = PROCESSED_DIR / "airports.csv"
    runway_output = PROCESSED_DIR / "runways.csv"

    selected_airports.to_csv(airport_output, index=False)
    selected_runways.to_csv(runway_output, index=False)

    print("\nCleaning summary")
    print(f"  Selected airport codes: {len(selected_codes)}")
    print(f"  Processed airports: {len(selected_airports)}")
    print(f"  Processed runways: {len(selected_runways)}")
    print(f"  Exact airport duplicates removed: {airport_duplicates_removed}")
    print(f"  Exact runway duplicates removed: {runway_duplicates_removed}")
    print(f"  Runways removed for missing identifiers: {missing_identifiers_removed}")
    print(f"  Airports saved to: {airport_output}")
    print(f"  Runways saved to: {runway_output}")


if __name__ == "__main__":
    clean_airports()
