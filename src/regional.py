__author__ = 'Khiem Doan'
__github__ = 'https://github.com/khiemdoan'
__email__ = 'doankhiem.crazy@gmail.com'

import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from cloudscraper import CloudScraper

import frames
from dtos import ResultCS, ResultCSList
from stations import Station, stations_of

# Prize tiers as they appear (top to bottom) on the region result grid,
# with how many numbers each tier has per đài. Total = 18 numbers.
TIER_COUNTS: dict[str, int] = {
    '8': 1,
    '7': 1,
    '6': 3,
    '5': 1,
    '4': 7,
    '3': 2,
    '2': 1,
    '1': 1,
    'ĐB': 1,
}

DATA_DIR = Path('data')


def parse_region_page(html: str, selected_date: date) -> dict[str, ResultCS]:
    """Parse a region page (xsmn/xsmt) into {đài_code: ResultCS}.

    Returns an empty dict if the page has no result grid, and skips any day whose
    numbers are incomplete (e.g. not drawn yet) so partial data is never stored.
    """
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='table-result')
    if table is None:
        return {}

    thead = table.find('thead')
    tbody = table.find('tbody')
    if thead is None or tbody is None:
        return {}

    # Column order = đài codes taken from the province links in the header.
    codes: list[str] = []
    for a in thead.find_all('a', href=True):
        if a['href'].startswith('/xo-so'):
            codes.append(a['href'].rstrip('/').split('/')[-1].split('-')[0])
    ncol = len(codes)
    if ncol == 0:
        return {}

    # Walk the body in document order, collecting each tier's numbers. Every tier
    # starts with a <th> label; numbers are <span class="xs_prize1" data-loto=..>.
    tiers: dict[str, list[str]] = {}
    current: str | None = None
    for el in tbody.descendants:
        name = getattr(el, 'name', None)
        if name == 'th':
            label = el.find(string=True, recursive=False)
            current = (label or '').strip()
            tiers.setdefault(current, [])
        elif name == 'span' and 'xs_prize1' in (el.get('class') or []):
            if current is not None:
                tiers[current].append(el.get('data-loto', '').strip())

    # Within a tier, numbers are grouped by đài in column order:
    # [đài0 x per_count][đài1 x per_count]... -> split into `ncol` chunks.
    per_station: dict[str, dict[str, list[str]]] = {code: {} for code in codes}
    for tier, per_count in TIER_COUNTS.items():
        values = tiers.get(tier, [])
        # Skip the whole day if incomplete or still showing '...' placeholders
        # (page for a day not drawn yet).
        if len(values) != per_count * ncol or any(not v.isdigit() for v in values):
            return {}
        for ci, code in enumerate(codes):
            per_station[code][tier] = values[ci * per_count:(ci + 1) * per_count]

    results: dict[str, ResultCS] = {}
    for code in codes:
        t = per_station[code]
        results[code] = ResultCS(
            date=selected_date,
            province=code,
            special=int(t['ĐB'][0]),
            prize1=int(t['1'][0]),
            prize2=int(t['2'][0]),
            prize3_1=int(t['3'][0]), prize3_2=int(t['3'][1]),
            prize4_1=int(t['4'][0]), prize4_2=int(t['4'][1]), prize4_3=int(t['4'][2]),
            prize4_4=int(t['4'][3]), prize4_5=int(t['4'][4]), prize4_6=int(t['4'][5]),
            prize4_7=int(t['4'][6]),
            prize5=int(t['5'][0]),
            prize6_1=int(t['6'][0]), prize6_2=int(t['6'][1]), prize6_3=int(t['6'][2]),
            prize7=int(t['7'][0]),
            prize8=int(t['8'][0]),
        )
    return results


class RegionLottery:
    """Per-đài storage + dataframe generation + file IO (data/<code>.*)."""

    def __init__(self, station: Station) -> None:
        self.station = station
        self.code = station.code
        self._data: dict[date, ResultCS] = {}
        self._raw_data = pd.DataFrame()
        self._2_digits_data = pd.DataFrame()
        self._sparse_data = pd.DataFrame()

    def load(self) -> None:
        path = DATA_DIR / f'{self.code}.json'
        if not path.exists():
            return
        data = ResultCSList.model_validate_json(path.read_text(encoding='utf-8'))
        for d in data.root:
            self._data[d.date] = d

    def add(self, result: ResultCS) -> None:
        self._data[result.date] = result

    def get_last_date(self) -> date | None:
        return max(self._data) if self._data else None

    def generate_dataframes(self) -> None:
        if not self._data:
            return
        records = [d.model_dump() for d in sorted(self._data.values(), key=lambda r: r.date)]
        self._raw_data, self._2_digits_data, self._sparse_data = frames.build_frames(
            records, exclude=('date', 'province')
        )

    def dump(self) -> None:
        if self._raw_data.empty:
            return
        frames.dump_frames(self._raw_data, self._2_digits_data, self._sparse_data, self.code)

    def get_raw_data(self) -> pd.DataFrame:
        return self._raw_data

    def get_2_digits_data(self) -> pd.DataFrame:
        return self._2_digits_data

    def get_sparse_data(self) -> pd.DataFrame:
        return self._sparse_data

    def has_data(self) -> bool:
        return bool(self._data)


def collect(
    http: CloudScraper,
    lotteries: dict[str, RegionLottery],
    start_date: date,
    end_date: date,
    *,
    delay: float = 1.0,
) -> None:
    """Fetch every region page from start_date..end_date and route results by đài.

    `lotteries` maps đài code -> RegionLottery (already loaded). Only dates on which
    a station is scheduled are requested per region, minimising HTTP calls.
    """
    for region in ('xsmn', 'xsmt'):
        region_codes = {s.code for s in stations_of(region)}
        region_weekdays = {wd for s in stations_of(region) for wd in s.weekdays}
        day = start_date
        while day <= end_date:
            if day.weekday() not in region_weekdays:
                day += timedelta(days=1)
                continue
            url = f'https://xoso.com.vn/{region}-{day:%d-%m-%Y}.html'
            try:
                resp = http.get(url)
            except Exception as exc:  # network hiccup -> skip, retry next run
                print(f'  ! {url}: {exc}')
                day += timedelta(days=1)
                continue
            if resp.status_code == 200:
                try:
                    results = parse_region_page(resp.text, day)
                except Exception as exc:  # never let one bad page abort the whole run
                    results = {}
                    print(f'  ! parse {region} {day}: {exc}')
                for code, result in results.items():
                    if code in lotteries and code in region_codes:
                        lotteries[code].add(result)
                print(f'  {region} {day}: {sorted(results)}', flush=True)
            else:
                print(f'  {region} {day}: HTTP {resp.status_code}', flush=True)
            time.sleep(delay)
            day += timedelta(days=1)
