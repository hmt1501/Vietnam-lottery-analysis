__author__ = 'hmt1501'
__github__ = 'https://github.com/hmt1501'
__email__ = 'hmt1501@users.noreply.github.com'

"""Generate loto & special-prize analysis charts for every Central/Southern đài.

For each đài with data it writes four charts under images/<code>/ and appends a
section to ANALYSIS.md. XSMB keeps its own analysis in analyze.py / README.md.
"""

from pathlib import Path

import matplotlib

matplotlib.use('Agg')

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from matplotlib import pyplot as plt  # noqa: E402

from regional import RegionLottery  # noqa: E402
from stations import REGIONS, stations_of  # noqa: E402

IMAGES = Path('images')

REGION_NAMES = {'xsmn': 'Miền Nam (Southern)', 'xsmt': 'Miền Trung (Central)'}


def colors_from_values(values: pd.Series, palette_name: str) -> np.ndarray:
    spread = max(values) - min(values)
    if spread == 0:
        normalized = np.zeros(len(values))
    else:
        normalized = (values - min(values)) / spread
    indices = np.round(normalized * (len(values) - 1)).astype(np.int32)
    palette = sns.color_palette(palette_name, len(values))
    return np.array(palette).take(indices, axis=0)


def _heatmap(series_by_value: pd.Series, title: str, out_path: Path) -> None:
    frame = series_by_value.rename('value').to_frame()
    frame['tens'] = series_by_value.index // 10
    frame['ones'] = series_by_value.index % 10
    frame = frame.pivot(index='tens', columns='ones', values='value').fillna(0).astype(int)

    fig, ax = plt.subplots()
    sns.heatmap(frame, annot=True, fmt='d', cmap='RdYlGn', ax=ax)
    ax.set_title(title)
    fig.savefig(out_path)
    plt.close(fig)


def _top10_bar(series_by_value: pd.Series, title: str, out_path: Path) -> None:
    bar = series_by_value.sort_values(ascending=False).iloc[:10].reset_index()
    bar.columns = ['value', 'count']
    bar['value'] = bar['value'].apply(lambda r: f'{r:02d}')

    fig, ax = plt.subplots()
    palette = list(reversed(colors_from_values(bar['count'], 'summer')))
    sns.barplot(bar, x='value', y='count', hue='value', palette=palette, legend=False, ax=ax)
    for container in ax.containers:
        ax.bar_label(container, fmt='%d')
    ax.set_title(title)
    fig.savefig(out_path)
    plt.close(fig)


def loto_frequency(sparse: pd.DataFrame, out_dir: Path) -> dict:
    """Total occurrences of each 2-digit number (00..99) across all draws."""
    counts = sparse.drop(columns=['date']).sum(axis=0)
    counts.index = counts.index.astype(int)

    _heatmap(counts, 'Loto frequency', out_dir / 'loto.jpg')
    _top10_bar(counts, 'Loto top 10', out_dir / 'loto_top10.jpg')

    return {
        'max': int(counts.max()),
        'min': int(counts.min()),
        'mean': round(float(counts.mean()), 2),
        'std': round(float(counts.std()), 2),
    }


def special_last_appearing(raw: pd.DataFrame, out_dir: Path) -> None:
    """Days since each 2-digit tail of the special prize last appeared."""
    numbers = raw[['special']].reset_index()
    predict_index = numbers['index'].max() + 1
    numbers['value'] = numbers['special'] % 100
    last_index = numbers.groupby('value')['index'].max()
    delta = (predict_index - last_index).astype(int)

    _heatmap(delta, 'Special delta', out_dir / 'special_delta.jpg')
    _top10_bar(delta, 'Special delta top 10', out_dir / 'special_delta_top10.jpg')


def analyse_station(station) -> dict | None:
    lottery = RegionLottery(station)
    lottery.load()
    if not lottery.has_data():
        return None
    lottery.generate_dataframes()

    out_dir = IMAGES / station.code
    out_dir.mkdir(parents=True, exist_ok=True)

    stats = loto_frequency(lottery.get_sparse_data(), out_dir)
    special_last_appearing(lottery.get_raw_data(), out_dir)

    rows = len(lottery.get_raw_data())
    return {'station': station, 'rows': rows, **stats}


def render_markdown(results: dict[str, list[dict]]) -> str:
    lines: list[str] = []
    lines.append('# Regional Lottery Analysis (Phân tích xổ số các tỉnh)\n')
    lines.append(
        'Loto (2-digit) frequency and special-prize delta charts for every Central '
        '(XSMT) and Southern (XSMN) đài. Regenerated daily by `src/analyze_regional.py`. '
        'For the North (XSMB) see [README.md](README.md).\n'
    )
    for region in REGIONS:
        items = results.get(region, [])
        if not items:
            continue
        lines.append(f'\n## {REGION_NAMES.get(region, region)}\n')
        for item in items:
            s = item['station']
            code = s.code
            lines.append(f'<details>\n  <summary><b>{s.name}</b> (<code>{code}</code>) — {item["rows"]} kỳ</summary>\n')
            lines.append(
                f'\n  Loto count — Max: {item["max"]} · Min: {item["min"]} · '
                f'Mean: {item["mean"]} · Std: {item["std"]}\n'
            )
            lines.append(f'\n  ![Loto](images/{code}/loto.jpg)')
            lines.append(f'\n  ![Loto top 10](images/{code}/loto_top10.jpg)')
            lines.append(f'\n  ![Special delta](images/{code}/special_delta.jpg)')
            lines.append(f'\n  ![Special delta top 10](images/{code}/special_delta_top10.jpg)\n')
            lines.append('</details>\n')
    return '\n'.join(lines)


if __name__ == '__main__':
    results: dict[str, list[dict]] = {region: [] for region in REGIONS}
    for region in REGIONS:
        for station in stations_of(region):
            print(f'Analyzing: {station.code} ({station.name})')
            item = analyse_station(station)
            if item is not None:
                results[region].append(item)

    content = render_markdown(results)
    Path('ANALYSIS.md').write_text(content, encoding='utf-8')
    total = sum(len(v) for v in results.values())
    print(f'Done. {total} đài analysed -> ANALYSIS.md')
