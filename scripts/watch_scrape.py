"""
Live scrape progress monitor.
Polls the DB every 30s and prints a status table.

Usage:
    set DATABASE_URL=postgresql://postgres:PASSWORD@159.69.153.234:5432/assetlens
    python scripts/watch_scrape.py

Or with the .env.scraper file:
    python scripts/watch_scrape.py --env backend/.env.scraper
"""
import argparse
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def load_env(path: str):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_stats(db):
    from sqlalchemy import func, text
    from backend.models.rental import Rental
    from backend.models.property import Property, PropertyScore

    total_props = db.query(Property).filter(Property.status == 'active').count()
    total_listings = db.query(Rental).filter(Rental.is_aggregated == False).count()
    total_agg = db.query(Rental).filter(Rental.is_aggregated == True).count()

    by_source = dict(
        db.query(Rental.source, func.count(Rental.id))
        .filter(Rental.is_aggregated == False)
        .group_by(Rental.source)
        .all()
    )

    districts = (
        db.query(func.count(func.distinct(func.split_part(Rental.postcode, ' ', 1))))
        .filter(Rental.is_aggregated == False)
        .scalar()
    ) or 0

    with_yield = (
        db.query(PropertyScore)
        .filter(PropertyScore.yield_score != 10.0)
        .count()
    )

    last_score = (
        db.query(func.max(PropertyScore.calculated_at))
        .scalar()
    )

    return {
        'total_props': total_props,
        'listings': total_listings,
        'aggregates': total_agg,
        'districts': districts,
        'by_source': by_source,
        'with_yield': with_yield,
        'last_score': last_score,
    }


def print_stats(stats, prev, poll_n: int):
    now = datetime.now().strftime('%H:%M:%S')
    listings = stats['listings']
    agg = stats['aggregates']
    districts = stats['districts']
    with_yield = stats['with_yield']
    total = stats['total_props']

    delta = ''
    if prev:
        d = listings - prev['listings']
        delta = f'  (+{d} since last poll)' if d > 0 else ''

    print(f'\n{"="*55}')
    print(f'  AssetLens Scrape Monitor — {now}  (poll #{poll_n})')
    print(f'{"="*55}')
    print(f'  Listings scraped : {listings:>6}{delta}')
    print(f'  Aggregates built : {agg:>6}  ({districts} districts)')
    src = stats['by_source']
    for source, count in sorted(src.items()):
        print(f'    {source:<18}: {count}')
    print(f'  Props with yield : {with_yield:>6} / {total}')
    if stats['last_score']:
        print(f'  Last re-score    : {stats["last_score"].strftime("%H:%M:%S")}')
    print(f'{"="*55}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', default='backend/.env.scraper')
    parser.add_argument('--interval', type=int, default=30)
    args = parser.parse_args()

    if os.path.exists(args.env):
        load_env(args.env)

    from backend.models.base import SessionLocal

    print(f'Watching scrape progress (polling every {args.interval}s). Ctrl+C to stop.\n')
    prev = None
    poll_n = 0
    try:
        while True:
            poll_n += 1
            db = SessionLocal()
            try:
                stats = get_stats(db)
            finally:
                db.close()
            print_stats(stats, prev, poll_n)
            prev = stats
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main()
