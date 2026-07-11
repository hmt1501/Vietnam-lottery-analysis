__author__ = 'hmt1501'
__github__ = 'https://github.com/hmt1501'
__email__ = 'hmt1501@users.noreply.github.com'

import numpy as np
import pandas as pd


def build_frames(
    records: list[dict],
    *,
    exclude: tuple[str, ...] = ('date',),
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the raw / 2-digits / sparse dataframes from a list of result dicts.

    `exclude` lists non-numeric columns (always includes 'date'; add 'province'
    for Central/Southern results). All remaining columns are treated as numbers.
    """
    raw = pd.DataFrame(records)
    raw['date'] = pd.to_datetime(raw['date'])
    number_cols = [c for c in raw.columns if c not in exclude]
    raw[number_cols] = raw[number_cols].astype('int64')

    two_digits = raw[['date', *number_cols]].copy()
    two_digits[number_cols] = two_digits[number_cols].apply(lambda x: x % 100)

    sparse = pd.concat(
        [
            two_digits.iloc[:, 0:1],
            pd.DataFrame(np.zeros((two_digits.shape[0], 100), dtype=int)),
        ],
        axis=1,
    )
    sparse.iloc[:, 1:] = sparse.iloc[:, 1:].astype('int64')
    numbers = two_digits[number_cols]
    for i in range(numbers.shape[0]):
        counts = numbers.iloc[i].value_counts()
        for k, v in counts.items():
            sparse.iloc[i, k + 1] = int(v)

    return raw, two_digits, sparse


def dump_frames(raw: pd.DataFrame, two_digits: pd.DataFrame, sparse: pd.DataFrame, name: str) -> None:
    """Write the three dataframes to data/{name}{,-2-digits,-sparse}.{csv,json,parquet}."""

    def _dump(df: pd.DataFrame, file_name: str) -> None:
        df.to_csv(f'data/{file_name}.csv', index=False)
        df.to_json(f'data/{file_name}.json', orient='records', date_format='iso', indent=2, index=False)
        df.to_parquet(f'data/{file_name}.parquet', index=False)

    _dump(raw, name)
    _dump(two_digits, f'{name}-2-digits')
    _dump(sparse, f'{name}-sparse')
