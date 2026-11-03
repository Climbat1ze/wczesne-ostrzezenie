"""Koncentracja wojsk przy granicy: siły przeciwnika tak, własne i sojusznicze nie (poprawka 2026-11-03)."""
import pytest

import ostrzezenie as o

S = o.Slownik()


@pytest.mark.parametrize("t", [
    "Russia is massing troops near the Lithuanian border, satellite images show",
    "Rosja gromadzi wojska przy granicy z Polską",
    "Belarus redeploys brigades to the Polish border, Lithuanian intelligence warns",
    "Polish forces observe Russian troops massing near border",
    "Russian troops deploy to Belarus ahead of Zapad drills",
    "Iskander missiles deployed to Kaliningrad",
])
def test_sily_przeciwnika_wykrywane(t):
    assert "wojska_granica" in S.kategorie(t)


@pytest.mark.parametrize("t", [
    "Poland deploys additional forces to Russian border: purpose of special operation",
    "Poland deploys additional police forces to border with Russia",
    "UK troops deploy to Poland to test mission to rebuild Ukraine's army",
    "Nearly 3,000 European troops to rehearse deployment to Ukraine in Poland",
    "Polska wysyła dodatkowe siły na granicę z Białorusią",
])
def test_wlasne_i_sojusznicze_sily_nie(t):
    assert "wojska_granica" not in S.kategorie(t)
