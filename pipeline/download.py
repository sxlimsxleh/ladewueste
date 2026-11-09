"""Download the raw inputs: the BNetzA Ladesäulenregister CSV and the Germany boundary.

Both sources are legally free to download:
- Ladesäulenregister: CC BY 4.0, attribution "Bundesnetzagentur.de" (stated on the landing page).
- Natural Earth: public domain.

The register CSV goes to data/raw/ (gitignored). A manifest records URL, SHA-256 and
download time so every pipeline run can say exactly which file it was built from.
The Germany polygon is extracted once into data/ref/germany.geojson (committed).
"""

import hashlib
import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from pipeline.config import GERMANY_GEOJSON, MANIFEST_PATH, RAW_DIR, load_config

USER_AGENT = "ladewueste-pipeline/0.1 (open-data research project)"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def find_csv_url(landing_html: str, pattern: str) -> str:
    """Return the newest register CSV link on the landing page; fail loudly if none."""
    links = sorted(set(re.findall(pattern, landing_html)))
    if not links:
        raise RuntimeError(
            "No Ladesäulenregister CSV link found on the landing page. "
            "The page layout may have changed; check config.yaml source.csv_link_pattern."
        )
    # File names embed an ISO date (..._2026-09-01.csv), so the lexicographic max is the newest.
    return links[-1]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_register(config: dict) -> Path:
    source = config["source"]
    landing_html = fetch(source["landing_page"]).decode("utf-8", errors="replace")
    csv_url = find_csv_url(landing_html, source["csv_link_pattern"])
    target = RAW_DIR / csv_url.rsplit("/", 1)[-1]

    if target.exists():
        print(f"Register already downloaded: {target.name}")
    else:
        print(f"Downloading {csv_url}")
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        target.write_bytes(fetch(csv_url))

    manifest = {
        "file": target.name,
        "url": csv_url,
        "sha256": sha256_of(target),
        "bytes": target.stat().st_size,
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "licence": source["licence"],
        "attribution": source["attribution"],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return target


def extract_germany(config: dict) -> None:
    """Write the single Germany feature from Natural Earth to data/ref/germany.geojson."""
    if GERMANY_GEOJSON.exists():
        print(f"Boundary already present: {GERMANY_GEOJSON.name}")
        return
    boundary = config["boundary"]
    print(f"Downloading {boundary['url']}")
    countries = json.loads(fetch(boundary["url"]))
    matches = [
        f for f in countries["features"] if f["properties"].get("ADM0_A3") == boundary["iso_a3"]
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {boundary['iso_a3']} feature, got {len(matches)}")
    germany = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Germany",
                    "source": "Natural Earth 1:10m admin-0 countries v5.1.2 (public domain)",
                },
                "geometry": matches[0]["geometry"],
            }
        ],
    }
    GERMANY_GEOJSON.parent.mkdir(parents=True, exist_ok=True)
    GERMANY_GEOJSON.write_text(json.dumps(germany), encoding="utf-8")


def main() -> None:
    config = load_config()
    path = download_register(config)
    extract_germany(config)
    print(f"Done: {path}")


if __name__ == "__main__":
    main()
