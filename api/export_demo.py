"""Export the API answers the static demo needs (GitHub Pages) as JSON files.

The files come from the real FastAPI app, called in-process, so the demo shows exactly what the API
would return and cannot drift from its contract. The file names must match web/src/lib/demo.ts.

Usage: python -m api.export_demo [output dir]   (default: web/public/demo-data, gitignored)
"""

import json
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.app.main import create_app
from pipeline.config import REPO_ROOT, load_config

DEFAULT_OUT = REPO_ROOT / "web" / "public" / "demo-data"
POWER_CLASSES = [None, 50, 150, 300]  # must match POWER_CLASSES in web/src/lib/scales.ts
PLAN_BUDGET = 10  # must match PLAY_BUDGET in web/src/pages/DesertMap.tsx


def rounded(value: Any, digits: int = 4) -> Any:
    """Round floats to 4 decimals (about 10 m for coordinates) to keep the files small."""
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, list):
        return [rounded(v, digits) for v in value]
    if isinstance(value, dict):
        return {k: rounded(v, digits) for k, v in value.items()}
    return value


def requests() -> dict[str, tuple[str, dict[str, Any]]]:
    res = load_config()["coverage"]["h3_resolutions"]["map"]
    files: dict[str, tuple[str, dict[str, Any]]] = {
        "config.json": ("/config", {}),
        "quality.json": ("/quality", {}),
        f"plan-{PLAN_BUDGET}.json": ("/plan", {"n": PLAN_BUDGET}),
    }
    for min_kw in POWER_CLASSES:
        params: dict[str, Any] = {"res": res} | ({"min_kw": min_kw} if min_kw is not None else {})
        files[f"hexes-{res}-{min_kw if min_kw is not None else 'all'}.json"] = ("/hexes", params)
    return files


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    out.mkdir(parents=True, exist_ok=True)
    client = TestClient(create_app())
    for name, (path, params) in requests().items():
        response = client.get(path, params=params)
        if response.status_code != 200:
            sys.exit(f"{path} {params} -> {response.status_code}: {response.text[:200]}")
        (out / name).write_text(json.dumps(rounded(response.json()), separators=(",", ":")), encoding="utf-8")
        print(f"{name:<22} {(out / name).stat().st_size / 1e6:6.2f} MB")


if __name__ == "__main__":
    main()
