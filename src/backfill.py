__author__ = 'hmt1501'
__github__ = 'https://github.com/hmt1501'
__email__ = 'hmt1501@users.noreply.github.com'

"""One-time historical back-fill for Central (XSMT) & Southern (XSMN) đài.

Unlike XSMB, the new đài ship without a seed data file. This script walks every
region page from --start to today and writes one dataset per đài. It is resumable:
already-collected days are re-read via load(); raise --start to skip ahead.

Usage:
    uv run src/backfill.py --start 2017-01-01 --delay 1.5
"""

import argparse
from datetime import date, datetime
from zoneinfo import ZoneInfo

from cloudscraper import CloudScraper

import regional
from regional import RegionLottery
from stations import STATIONS

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default='2017-01-01', help='earliest date to fetch (YYYY-MM-DD)')
    parser.add_argument('--delay', type=float, default=1.5, help='seconds between HTTP requests')
    args = parser.parse_args()

    start_date = date.fromisoformat(args.start)
    end_date = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date()

    lotteries = {s.code: RegionLottery(s) for s in STATIONS}
    for lot in lotteries.values():
        lot.load()

    http = CloudScraper()
    regional.collect(http, lotteries, start_date, end_date, delay=args.delay)

    for lot in lotteries.values():
        lot.generate_dataframes()
        lot.dump()
        last = lot.get_last_date()
        print(f'{lot.code}: {len(lot._data)} rows, last {last}')
