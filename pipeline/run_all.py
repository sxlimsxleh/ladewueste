"""The whole pipeline in one command: raw CSV -> bronze -> mess report -> dbt build -> gold -> report.

Used by `make pipeline`, by the Docker `pipeline` service and by CI, so all three run the same steps.
Downloads the register first only if no CSV is present (pass --no-download to forbid it, e.g. in CI
on the synthetic fixture).
"""

import sys

from pipeline import download, export, load_bronze, profile, report, run_dbt
from pipeline.config import RAW_DIR


def main() -> None:
    have_raw = any(RAW_DIR.glob("Ladesaeulenregister*.csv"))
    if not have_raw:
        if "--no-download" in sys.argv:
            sys.exit(f"No register CSV in {RAW_DIR} and --no-download was given.")
        download.main()
    load_bronze.main()
    profile.main()
    if not run_dbt.run(["build"]):
        sys.exit("dbt build failed: see the test output above.")
    export.main()
    report.main()


if __name__ == "__main__":
    main()
