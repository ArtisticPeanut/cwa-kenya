"""One-shot bootstrap: create tables, seed reference data, import responses.

Usage:
    python scripts/bootstrap.py
    python scripts/bootstrap.py --csv "path/to/responses.csv"
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.services import importer, seeding  # noqa: E402

DEFAULT_CSV = (
    "Kenyan Cybersecurity Translation Project  (Responses) - Form responses 1.csv"
)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap the CWA platform.")
    parser.add_argument("--csv", default=None, help="Path to the responses CSV.")
    parser.add_argument("--no-import", action="store_true",
                        help="Only create tables and seed reference data.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Seeding reference data...")
        seeding.seed_all(verbose=True)

        if not args.no_import:
            csv_path = args.csv or DEFAULT_CSV
            if not os.path.isabs(csv_path):
                csv_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    csv_path,
                )
            if os.path.exists(csv_path):
                print(f"Importing responses from: {csv_path}")
                stats = importer.import_csv(csv_path)
                print(stats)
            else:
                print(f"CSV not found, skipping import: {csv_path}")

        print("Bootstrap complete.")


if __name__ == "__main__":
    main()
