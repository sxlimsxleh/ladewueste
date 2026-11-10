"""Write api/openapi.json from the FastAPI app (no server needed).
The web app's TypeScript types are generated from this file (make types)."""

import json
from pathlib import Path

from api.app.main import create_app

OPENAPI_PATH = Path(__file__).resolve().parent / "openapi.json"


def openapi_json() -> str:
    return json.dumps(create_app().openapi(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> None:
    OPENAPI_PATH.write_text(openapi_json(), encoding="utf-8")
    print(f"Wrote {OPENAPI_PATH}")


if __name__ == "__main__":
    main()
