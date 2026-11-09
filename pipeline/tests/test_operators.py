"""R07/R08 operator normalisation on small hand-made inputs."""

import pandas as pd
import pytest

from pipeline.operators import build_operator_map, legal_key, surface_key

NO_OVERRIDES = pd.DataFrame(columns=["from_name", "to_name"])


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("CUBOS Service GmbH", "Cubos Service GmbH"),
        ("Orange  Charging B.V.", "Orange Charging B.V."),
        ("Elektro-Rosin GmbH", "Elektro Rosin GmbH"),
        ("Stadtwerke Schloß Holte", "Stadtwerke Schloss Holte"),
        ("Auto König GmbH&Co.KG", "Auto König GmbH & Co.KG"),
        ("Christian\xa0 Dillschneider", "Christian Dillschneider"),
    ],
)
def test_surface_key_merges_formatting_variants(a: str, b: str) -> None:
    assert surface_key(a) == surface_key(b)


def test_surface_key_keeps_different_names_apart() -> None:
    assert surface_key("Stadtwerke Kempen GmbH") != surface_key("Stadtwerke Kerpen GmbH")
    assert surface_key("Autohaus Schneider GmbH") != surface_key("Autohaus Schneider e.K.")


def test_legal_key_ignores_legal_form() -> None:
    assert legal_key("Autohaus Schneider GmbH & Co. KG") == legal_key("Autohaus Schneider e.K.") == "autohaus schneider"


def counts(*rows: tuple[str, int]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["operator_clean", "n_records"])


def test_r07_canonical_is_most_frequent_spelling() -> None:
    result = build_operator_map(counts(("nonoxx pro GmbH", 153), ("Nonoxx Pro GmbH", 2)), NO_OVERRIDES, 96)
    assert set(result["operator_canonical"]) == {"nonoxx pro GmbH"}


def test_r08_legal_form_is_suggested_but_not_applied() -> None:
    result = build_operator_map(
        counts(("Autohaus Schneider GmbH", 6), ("Autohaus Schneider e.K.", 1)), NO_OVERRIDES, 96
    ).set_index("operator_clean")
    small = result.loc["Autohaus Schneider e.K."]
    assert small["suggested_target"] == "Autohaus Schneider GmbH"
    assert small["suggestion_reason"] == "legal_form"
    assert small["operator_canonical"] == "Autohaus Schneider e.K."  # not merged without approval
    assert pd.isna(result.loc["Autohaus Schneider GmbH", "suggested_target"])  # never points to a smaller one


def test_r08_approved_override_is_applied() -> None:
    overrides = pd.DataFrame([("Autohaus Schneider e.K.", "Autohaus Schneider GmbH")], columns=["from_name", "to_name"])
    result = build_operator_map(
        counts(("Autohaus Schneider GmbH", 6), ("Autohaus Schneider e.K.", 1)), overrides, 96
    ).set_index("operator_clean")
    assert result.loc["Autohaus Schneider e.K.", "operator_canonical"] == "Autohaus Schneider GmbH"
    assert bool(result.loc["Autohaus Schneider e.K.", "approved"])


def test_r08_fuzzy_respects_threshold() -> None:
    names = counts(("Autohaus Hofmann GmbH", 8), ("Autohaus Hoffmann GmbH", 3))
    assert build_operator_map(names, NO_OVERRIDES, 96)["suggested_target"].notna().any()
    assert build_operator_map(names, NO_OVERRIDES, 99.5)["suggested_target"].isna().all()
