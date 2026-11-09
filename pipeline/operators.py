"""Operator name normalisation (rules R07 and R08).

R07 (safe, applied automatically): spellings that differ only in case, whitespace or
    '.'/',' are the same operator. The canonical spelling is the most frequent one.
R08 (unsafe, review only): names that match after removing the legal form, or that are
    very similar (rapidfuzz), are SUGGESTED merges. They are applied only when a human
    lists them in seeds/operator_overrides.csv, because 'Autohaus Meier GmbH' and
    'Autohaus Maier e.K.' can be two different companies.
"""

import re

import pandas as pd
from rapidfuzz import fuzz, process

LEGAL_SUFFIX = re.compile(
    r"\b(gmbh\s*&\s*co\.?\s*kg|ag\s*(&|und)\s*co\.?\s*kg|ug\s*\(haftungsbeschränkt\)"
    r"|gmbh|mbh|ag|se|kg|ug|ohg|e\.?\s?k\.?|eg|kgaa|b\.?v\.?)\.?\s*$"
)


def surface_key(name: str) -> str:
    """Key that ignores differences no one would call a different company:
    case, whitespace (incl. non-breaking space), '.', ',', apostrophes, hyphen vs space,
    spacing around '&', and 'ß' vs 'ss'."""
    s = name.replace("\xa0", " ").lower().replace("ß", "ss")
    s = re.sub(r"[.,'’]", "", s)
    s = re.sub(r"\s*-\s*", " ", s)
    s = re.sub(r"\s*&\s*", " & ", s)
    return re.sub(r"\s+", " ", s).strip()


def legal_key(name: str) -> str:
    """surface_key with a trailing legal form removed."""
    s = re.sub(r"\s+", " ", name.replace("\xa0", " ").lower()).strip()
    return surface_key(LEGAL_SUFFIX.sub("", s))


def pick_canonical(group: pd.DataFrame) -> str:
    """Most frequent spelling; ties broken alphabetically so the result is deterministic."""
    ranked = group.sort_values(["n_records", "operator_clean"], ascending=[False, True])
    return str(ranked["operator_clean"].iloc[0])


def suggest_merges(canon: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """For each canonical name, suggest merging it into a BIGGER operator (more records).

    Pass 1, legal form: same legal_key, different surface_key.
    Pass 2, fuzzy: token_sort_ratio on legal_key >= threshold, compared only within
    names that start with the same character (blocking keeps it to seconds, not minutes).
    Merging only ever points to a bigger operator, so suggestions cannot form cycles.
    """
    canon = canon.sort_values(["n_records", "name"], ascending=[False, True]).reset_index(drop=True)
    canon["rank"] = canon.index  # 0 = biggest operator
    suggestions: dict[str, tuple[str, str, float]] = {}

    for _, group in canon.groupby("legal_key"):
        if len(group) > 1:
            target = group.iloc[0]["name"]  # already sorted biggest first
            for name in group["name"].iloc[1:]:
                suggestions[name] = (target, "legal_form", 100.0)

    canon["block"] = canon["legal_key"].str[:1]
    for _, block in canon.groupby("block"):
        if len(block) < 2:
            continue
        keys = block["legal_key"].tolist()
        scores = process.cdist(keys, keys, scorer=fuzz.token_sort_ratio, score_cutoff=threshold, workers=-1)
        names, ranks = block["name"].tolist(), block["rank"].tolist()
        for i, name in enumerate(names):
            if name in suggestions:
                continue
            best_j, best_score = None, 0.0
            for j in range(len(names)):
                bigger = ranks[j] < ranks[i]
                if bigger and keys[j] != keys[i] and scores[i][j] > best_score:
                    best_j, best_score = j, float(scores[i][j])
            if best_j is not None:
                suggestions[name] = (names[best_j], "fuzzy", best_score)

    return pd.DataFrame(
        [(name, target, reason, score) for name, (target, reason, score) in suggestions.items()],
        columns=["surface_canonical", "suggested_target", "suggestion_reason", "suggestion_score"],
    )


def build_operator_map(counts: pd.DataFrame, overrides: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """counts: operator_clean, n_records. overrides: from_name, to_name (human-approved R08 merges).

    Returns one row per operator_clean spelling with its R07 canonical, any R08 suggestion,
    and the final operator_canonical (override applied only if approved).
    """
    df = counts.copy()
    df["surface_key"] = df["operator_clean"].map(surface_key)
    canonical = df.groupby("surface_key").apply(pick_canonical, include_groups=False).rename("surface_canonical")
    df = df.merge(canonical, left_on="surface_key", right_index=True)

    canon = df.groupby("surface_canonical", as_index=False)["n_records"].sum().rename(columns={"surface_canonical": "name"})
    canon["legal_key"] = canon["name"].map(legal_key)
    df = df.merge(suggest_merges(canon, threshold), on="surface_canonical", how="left")

    approved = dict(zip(overrides["from_name"], overrides["to_name"]))
    df["approved"] = df["surface_canonical"].isin(approved.keys())
    df["operator_canonical"] = df["surface_canonical"].map(lambda n: approved.get(n, n))
    return df.sort_values("operator_clean").reset_index(drop=True)
