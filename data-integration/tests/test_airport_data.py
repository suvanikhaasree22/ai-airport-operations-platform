from pathlib import Path
import unittest

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"


def test_all_selected_airports_are_present():
    selected = pd.read_csv(RAW_DIR / "airports_selected.csv")
    processed = pd.read_csv(PROCESSED_DIR / "airports.csv")

    selected_codes = set(selected["iata_code"].dropna().str.strip().str.upper())
    processed_codes = set(processed["iata_code"].dropna().str.strip().str.upper())

    assert selected_codes == processed_codes


def test_airport_ids_are_present_and_unique():
    airports = pd.read_csv(PROCESSED_DIR / "airports.csv")

    assert airports["id"].notna().all()
    assert airports["id"].is_unique


def test_airport_coordinates_are_valid():
    airports = pd.read_csv(PROCESSED_DIR / "airports.csv")

    assert airports["latitude_deg"].notna().all()
    assert airports["longitude_deg"].notna().all()
    assert airports["latitude_deg"].between(-90, 90).all()
    assert airports["longitude_deg"].between(-180, 180).all()


def test_runways_belong_to_selected_airports():
    airports = pd.read_csv(PROCESSED_DIR / "airports.csv")
    runways = pd.read_csv(PROCESSED_DIR / "runways.csv")

    airport_ids = set(airports["id"])
    runway_airport_ids = set(runways["airport_ref"].dropna())

    assert runway_airport_ids.issubset(airport_ids)


def test_runway_ids_are_present_and_unique():
    runways = pd.read_csv(PROCESSED_DIR / "runways.csv")

    assert runways["id"].notna().all()
    assert runways["id"].is_unique


class TestAirportMasterData(unittest.TestCase):
    def test_all_selected_airports_are_present(self):
        test_all_selected_airports_are_present()

    def test_airport_ids_are_present_and_unique(self):
        test_airport_ids_are_present_and_unique()

    def test_airport_coordinates_are_valid(self):
        test_airport_coordinates_are_valid()

    def test_runways_belong_to_selected_airports(self):
        test_runways_belong_to_selected_airports()

    def test_runway_ids_are_present_and_unique(self):
        test_runway_ids_are_present_and_unique()


if __name__ == "__main__":
    unittest.main()
