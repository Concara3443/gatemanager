"""Tests unitarios para app/parking_finder.py (lógica pura, sin GUI)."""
from unittest.mock import patch

import pytest

import app.parking_finder as pf


# ---------------------------------------------------------------------------
# get_numeric_id
# ---------------------------------------------------------------------------

class TestGetNumericId:
    def test_stand_with_number(self):
        assert pf.get_numeric_id("101") == 101

    def test_stand_with_number_and_suffix(self):
        assert pf.get_numeric_id("204L") == 204

    def test_stand_no_number(self):
        assert pf.get_numeric_id("A") == -1

    def test_stand_empty(self):
        assert pf.get_numeric_id("") == -1

    def test_stand_pure_alpha(self):
        assert pf.get_numeric_id("GA1") == -1


# ---------------------------------------------------------------------------
# schengen_ok
# ---------------------------------------------------------------------------

class TestSchengenOk:
    def test_mixed_schengen_flight(self):
        assert pf.schengen_ok({"schengen": "mixed"}, True) is True

    def test_mixed_non_schengen_flight(self):
        assert pf.schengen_ok({"schengen": "mixed"}, False) is True

    def test_schengen_only_accepts_schengen(self):
        assert pf.schengen_ok({"schengen": "schengen_only"}, True) is True

    def test_schengen_only_rejects_non_schengen(self):
        assert pf.schengen_ok({"schengen": "schengen_only"}, False) is False

    def test_non_schengen_only_accepts_non_schengen(self):
        assert pf.schengen_ok({"schengen": "non_schengen_only"}, False) is True

    def test_non_schengen_only_rejects_schengen(self):
        assert pf.schengen_ok({"schengen": "non_schengen_only"}, True) is False

    def test_custom_dedicated_always_ok(self):
        # Categorías personalizadas (dedicados) se tratan como mixed
        assert pf.schengen_ok({"schengen": "ibe_dedicated"}, True) is True
        assert pf.schengen_ok({"schengen": "ibe_dedicated"}, False) is True

    def test_default_no_key(self):
        # Sin clave 'schengen' se asume mixed
        assert pf.schengen_ok({}, True) is True
        assert pf.schengen_ok({}, False) is True


# ---------------------------------------------------------------------------
# _sort_key
# ---------------------------------------------------------------------------

class TestSortKey:
    def test_normal_stand(self):
        data = {"max_wingspan": 36.0, "schengen": "mixed", "excludes": ["102", "103"], "remote": False}
        with patch("app.parking_finder.random.random", return_value=0.42):
            key = pf._sort_key("101", data, "mixed", True)
        assert key == (36.0, 2, 0, 0.42)

    def test_no_wingspan_returns_high_values(self):
        key = pf._sort_key("101", {}, "mixed", True)
        assert key == (9999, 9999, 1, "101")

    def test_remote_non_preferred_gets_penalty(self):
        data = {"max_wingspan": 60.0, "schengen": "schengen_only", "excludes": [], "remote": True}
        with patch("app.parking_finder.random.random", return_value=0.1):
            key = pf._sort_key("R01", data, "non_schengen_only", False)
        # remote=True y stype != prefer_type → gate_pen=1
        assert key[2] == 1

    def test_remote_preferred_no_penalty(self):
        data = {"max_wingspan": 60.0, "schengen": "schengen_only", "excludes": [], "remote": True}
        with patch("app.parking_finder.random.random", return_value=0.1):
            key = pf._sort_key("R01", data, "schengen_only", False)
        # remote=True pero stype == prefer_type → gate_pen=0
        assert key[2] == 0

    def test_tiebreak_is_random(self):
        data = {"max_wingspan": 36.0, "schengen": "mixed", "excludes": [], "remote": False}
        # Dos llamadas producen claves distintas en el tiebreak
        key1 = pf._sort_key("101", data, "mixed", True)
        key2 = pf._sort_key("102", data, "mixed", True)
        # Los tres primeros elementos son iguales; el cuarto es aleatorio
        assert key1[:3] == key2[:3]


# ---------------------------------------------------------------------------
# filter_parkings
# ---------------------------------------------------------------------------

PARKINGS = {
    "101": {"max_wingspan": 36.0, "terminal": "T1", "schengen": "mixed",          "remote": False},
    "102": {"max_wingspan": 24.0, "terminal": "T1", "schengen": "schengen_only",   "remote": False},
    "103": {"max_wingspan": 36.0, "terminal": "T2", "schengen": "mixed",           "remote": False},
    "104": {"max_wingspan": 36.0, "terminal": "T1", "schengen": "non_schengen_only","remote": False},
    "105": {"max_wingspan": 36.0, "terminal": "T1", "schengen": "ga",              "remote": False},
    "106": {"max_wingspan": 36.0, "terminal": "T1", "schengen": "ibe_dedicated",   "remote": False},
}


class TestFilterParkings:
    def test_filters_by_terminal(self):
        result = pf.filter_parkings(PARKINGS, "T2", "IBE", 36.0, True, set())
        assert set(result.keys()) == {"103"}

    def test_filters_by_wingspan(self):
        # wingspan 30 → stand 102 (max 24) should be excluded
        result = pf.filter_parkings(PARKINGS, "T1", "IBE", 30.0, True, set())
        # 101 (36>=30 ok), 102 (24<30 excluded), 104 non-sch rejected for schengen flight
        assert "102" not in result
        assert "101" in result

    def test_filters_occupied(self):
        result = pf.filter_parkings(PARKINGS, "T1", "IBE", 36.0, True, {"101"})
        assert "101" not in result

    def test_filters_schengen_only_for_non_schengen_flight(self):
        result = pf.filter_parkings(PARKINGS, "T1", "IBE", 36.0, False, set())
        assert "102" not in result  # schengen_only excluded for non-schengen flight

    def test_filters_non_schengen_only_for_schengen_flight(self):
        result = pf.filter_parkings(PARKINGS, "T1", "IBE", 36.0, True, set())
        assert "104" not in result  # non_schengen_only excluded for schengen flight

    def test_skips_ga_and_special_categories(self):
        result = pf.filter_parkings(PARKINGS, "T1", "IBE", 36.0, True, set())
        assert "105" not in result  # ga stands excluded

    def test_dedicated_excluded_if_airline_not_in_map(self):
        # ibe_dedicated stand 106 should be excluded for airline VLG (not in map)
        result = pf.filter_parkings(PARKINGS, "T1", "VLG", 36.0, True, set(),
                                    dedicated_map={"IBE": "ibe_dedicated"})
        assert "106" not in result

    def test_dedicated_included_if_airline_in_map(self):
        result = pf.filter_parkings(PARKINGS, "T1", "IBE", 36.0, True, set(),
                                    dedicated_map={"IBE": "ibe_dedicated"})
        assert "106" in result
