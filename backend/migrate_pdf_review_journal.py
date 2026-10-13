"""Operator-only, dry-run-by-default import; never grants manufacturer verification."""
import argparse
import json
from app.database import SessionLocal
from app.services.manufacturer_pdf_reviews_db import import_legacy_reviews, DecisionError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--journal', required=True)
    parser.add_argument('--actor-user-id', required=True, type=int)
    parser.add_argument('--commit', action='store_true', help='Write legacy snapshots after reviewing a dry run')
    args = parser.parse_args()
    try:
        with SessionLocal() as db:
            print(json.dumps(import_legacy_reviews(db, args.journal, args.actor_user_id, args.commit)))
    except DecisionError as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
