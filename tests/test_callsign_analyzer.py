"""Tests unitarios para app/callsign_analyzer.py."""

import os
from unittest.mock import patch

import pytest

# Ruta al prefix_data.json real (relativa a la raíz del proyecto)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REAL_PREFIX_DATA = os.path.join(_PROJECT_ROOT, "data", "prefix_data.json")


@pytest.fixture(scope="module")
def analyzer():
    """CallsignAnalyzer usando el prefix_data.json real del proyecto."""
    with patch("app.callsign_analyzer._data_path", return_value=_REAL_PREFIX_DATA):
        from app.callsign_analyzer import CallsignAnalyzer

        return CallsignAnalyzer()


class TestClean:
    def test_uppercase(self, analyzer):
        assert analyzer.clean("iberia1") == "IBERIA1"

    def test_removes_dashes(self, analyzer):
        assert analyzer.clean("EC-LVL") == "ECLVL"

    def test_removes_spaces(self, analyzer):
        assert analyzer.clean("G ABCD") == "GABCD"


class TestAirlineCallsigns:
    """Callsigns de aerolínea OACI: 3 letras + dígito → comercial."""

    def test_iberia(self, analyzer):
        result = analyzer.check("IBE123")
        assert result["is_private"] is False

    def test_vueling(self, analyzer):
        result = analyzer.check("VLG4321")
        assert result["is_private"] is False

    def test_ryanair(self, analyzer):
        result = analyzer.check("RYR1234")
        assert result["is_private"] is False

    def test_easyjet(self, analyzer):
        result = analyzer.check("EZY8765")
        assert result["is_private"] is False


class TestRegistrations:
    """Matrículas de aviación general → privado."""

    def test_spanish_registration(self, analyzer):
        result = analyzer.check("ECLVL")
        assert result["is_private"] is True

    def test_uk_registration(self, analyzer):
        result = analyzer.check("GABCD")
        assert result["is_private"] is True

    def test_usa_registration_n(self, analyzer):
        result = analyzer.check("N12345")
        assert result["is_private"] is True

    def test_usa_short_registration(self, analyzer):
        result = analyzer.check("N123")
        assert result["is_private"] is True


class TestEdgeCases:
    def test_too_short(self, analyzer):
        result = analyzer.check("AB")
        assert result["is_private"] is False
        assert result["type"] == "Invalid"

    def test_lowercase_airline(self, analyzer):
        result = analyzer.check("ibe123")
        assert result["is_private"] is False
