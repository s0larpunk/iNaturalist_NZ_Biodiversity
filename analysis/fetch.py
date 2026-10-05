"""Pull today's New Zealand data from the iNaturalist API, politely.

Every response is cached in analysis/cache/ so the analysis can be re-run
without hitting the API again. One request per second, well inside the
API's published limit of 60 per minute.

    ../.venv/bin/python fetch.py
"""
import json
import pathlib
import time

import requests

HERE = pathlib.Path(__file__).resolve().parent
CACHE = HERE / 'cache'
CACHE.mkdir(exist_ok=True)
API = 'https://api.inaturalist.org/v1/'
NZ = 6803
UA = {'User-Agent': 'maximvelli.com biodiversity re-analysis (maxim.velli@icloud.com)'}
BASE = {'place_id': NZ, 'quality_grade': 'research'}


def get(path, params, name):
    f = CACHE / f'{name}.json'
    if f.exists():
        return json.loads(f.read_text())
    for attempt in range(5):
        try:
            r = requests.get(API + path, params=params, headers=UA, timeout=60)
        except requests.exceptions.RequestException:
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        data = r.json()
        f.write_text(json.dumps(data))
        time.sleep(1.0)
        return data
    raise RuntimeError(f'gave up on {name}')


def species_list():
    """Every species with a research-grade observation, with its count."""
    out, page = [], 1
    while True:
        d = get('observations/species_counts', {**BASE, 'rank': 'species', 'per_page': 500, 'page': page},
                f'species_p{page:03d}')
        out += d['results']
        if page * 500 >= d['total_results'] or not d['results']:
            break
        page += 1
    print('species', len(out))


def by_year():
    """Cumulative species and observations up to the end of each year, and
    the people who observed in that year."""
    for y in range(2005, 2027):
        get('observations/species_counts', {**BASE, 'rank': 'species', 'd2': f'{y}-12-31', 'per_page': 1}, f'cum_species_{y}')
        get('observations', {**BASE, 'd2': f'{y}-12-31', 'per_page': 0}, f'cum_obs_{y}')
        get('observations/observers', {**BASE, 'd1': f'{y}-01-01', 'd2': f'{y}-12-31', 'per_page': 1}, f'observers_{y}')
    print('years done')


def grid(step=0.5):
    """Observation counts on a half-degree grid over New Zealand."""
    lat = -47.5
    n = 0
    while lat < -34.0:
        lng = 166.0
        while lng < 179.0:
            key = f'grid_{lat:+.1f}_{lng:+.1f}'
            get('observations', {**BASE, 'swlat': lat, 'swlng': lng, 'nelat': lat + step, 'nelng': lng + step,
                                 'per_page': 0}, key)
            lng += step
            n += 1
        lat += step
    print('grid cells', n)


if __name__ == '__main__':
    species_list()
    by_year()
    grid()
