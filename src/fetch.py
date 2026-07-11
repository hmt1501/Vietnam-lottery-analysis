__author__ = 'Khiem Doan'
__github__ = 'https://github.com/khiemdoan'
__email__ = 'doankhiem.crazy@gmail.com'

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from cloudscraper import CloudScraper

import regional
from lottery import Lottery
from regional import RegionLottery
from stations import STATIONS


def _latest_available_date(now: datetime, cutoff: time = time(18, 35)) -> object:
    """Latest date whose results are already published (all regions drawn by 18:35 VN)."""
    last_date = now.date()
    if now.time() < cutoff:
        last_date -= timedelta(days=1)
    return last_date


if __name__ == '__main__':
    tz = ZoneInfo('Asia/Ho_Chi_Minh')
    now = datetime.now(tz)
    last_date = _latest_available_date(now)

    # ----- Miền Bắc (XSMB): single result per day -----
    lottery = Lottery()
    lottery.load()

    begin_date = lottery.get_last_date()
    delta = (last_date - begin_date).days + 1
    for i in range(1, delta):
        selected_date = begin_date + timedelta(days=i)
        print(f'XSMB fetching: {selected_date}')
        lottery.fetch(selected_date)

    lottery.generate_dataframes()
    lottery.dump()

    # ----- Miền Trung (XSMT) & Miền Nam (XSMN): many đài per day -----
    lotteries = {s.code: RegionLottery(s) for s in STATIONS}
    for lot in lotteries.values():
        lot.load()

    known_last = [d for d in (lot.get_last_date() for lot in lotteries.values()) if d is not None]
    # No history yet -> only fetch today; run backfill.py for the full history.
    start_date = min(known_last) + timedelta(days=1) if known_last else last_date

    http = CloudScraper()
    regional.collect(http, lotteries, start_date, last_date)

    for lot in lotteries.values():
        lot.generate_dataframes()
        lot.dump()
