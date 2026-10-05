"""2026 re-analysis: what the crowd can and cannot tell New Zealand about its
own living world. Reads the cached API responses from fetch.py and the
official NZTCS export, writes results.json for the write-up and gaps.json
for the in-browser tool.

    ../.venv/bin/python run.py
"""
import json
import pathlib
import re

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
CACHE = HERE / 'cache'
rng = np.random.default_rng(11)

# iNaturalist's "iconic" groups, folded into the kingdoms NZTCS uses
KINGDOM = {'Aves': 'Animalia', 'Insecta': 'Animalia', 'Mollusca': 'Animalia', 'Arachnida': 'Animalia',
           'Mammalia': 'Animalia', 'Reptilia': 'Animalia', 'Amphibia': 'Animalia', 'Actinopterygii': 'Animalia',
           'Animalia': 'Animalia', 'Plantae': 'Plantae', 'Fungi': 'Fungi', 'Chromista': 'Chromista',
           'Protozoa': 'Protozoa'}
KNOWN_TOTAL = 52000          # described species known from NZ (Gordon 2013)
STUDY_2024 = dict(species=15710, chao1=19843, ace=21675, snapshot='2024-02-01')


def clean_name(s):
    """Genus + species epithet, lower case: the level both sources share."""
    s = re.sub(r'[^A-Za-z ]', ' ', str(s)).split()
    return ' '.join(s[:2]).lower() if len(s) >= 2 else ''


def load_inat():
    rows = []
    for f in sorted(CACHE.glob('species_p*.json')):
        for r in json.loads(f.read_text())['results']:
            t = r['taxon']
            rows.append(dict(id=t['id'], name=t['name'], common=t.get('preferred_common_name') or '',
                             group=t.get('iconic_taxon_name') or 'Other', count=r['count'],
                             native=bool(t.get('endemic') or t.get('native')),
                             threatened=bool(t.get('threatened'))))
    d = pd.DataFrame(rows).drop_duplicates('id')
    d['kingdom'] = d.group.map(KINGDOM).fillna('Other')
    d['key'] = d.name.map(clean_name)
    return d


def chao1(counts):
    s, f1, f2 = len(counts), int((counts == 1).sum()), int((counts == 2).sum())
    return s + (f1 * f1 / (2 * f2) if f2 else f1 * (f1 - 1) / 2), f1, f2


def ace(counts, cutoff=10):
    counts = np.asarray(counts)
    rare, abundant = counts[counts <= cutoff], counts[counts > cutoff]
    n_rare = rare.sum()
    f1 = (rare == 1).sum()
    c = 1 - f1 / n_rare
    fk = np.array([(rare == k).sum() for k in range(1, cutoff + 1)])
    k = np.arange(1, cutoff + 1)
    g2 = max(len(rare) / c * (k * (k - 1) * fk).sum() / (n_rare * (n_rare - 1)) - 1, 0)
    return len(abundant) + len(rare) / c + f1 / c * g2


def main():
    inat = load_inat()
    nz = pd.read_excel(HERE.parent / 'nztcs_export.xlsx')
    nz['key'] = nz['Current Species Name'].map(clean_name)
    nz = nz[nz.key != ''].drop_duplicates('Current Species Name').copy()
    # Subspecies, varieties and informal forms share a genus+species key with
    # their parent species, whose crowd records would be wrongly credited to
    # them. Threat and gap statistics use plain binomials only.
    nz['binomial'] = nz['Current Species Name'].str.strip().str.fullmatch(r'[A-Z][a-z]+ [a-z][a-z-]+')
    out = {'study_2024': STUDY_2024, 'known_total': KNOWN_TOTAL}

    # ------------------------------------------------ 1. how much the crowd has seen
    counts = inat['count'].values
    c1, f1, f2 = chao1(counts)
    out['now'] = dict(species=int(len(inat)), observations_research=int(counts.sum()),
                      chao1=float(c1), ace=float(ace(counts)), singletons=f1, doubletons=f2)
    # bootstrap the Chao1 estimate by resampling species
    boots = [chao1(counts[rng.integers(0, len(counts), len(counts))])[0] for _ in range(500)]
    out['now']['chao1_ci'] = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]

    # ------------------------------------------------ 2. over time
    years = []
    for y in range(2005, 2027):
        sp = json.loads((CACHE / f'cum_species_{y}.json').read_text())['total_results']
        ob = json.loads((CACHE / f'cum_obs_{y}.json').read_text())['total_results']
        pe = json.loads((CACHE / f'observers_{y}.json').read_text())['total_results']
        years.append(dict(year=y, species=sp, observations=ob, observers=pe))
    out['years'] = years
    # new species per 100,000 new observations, in two-year steps
    ret = []
    for a, b in zip(years[3::2], years[5::2]):
        d_obs = b['observations'] - a['observations']
        if d_obs > 0:
            ret.append(dict(span=f"{a['year']}–{b['year']}", per100k=(b['species'] - a['species']) / d_obs * 1e5))
    out['returns'] = ret

    # ------------------------------------------------ 3. groups: what the crowd sees
    g = inat.groupby('kingdom').agg(species=('id', 'size'), observations=('count', 'sum'))
    off = nz.groupby('Kingdom').size()
    nbk = nz[nz.binomial]
    seen_by_kingdom = nbk[nbk.key.isin(set(inat.key))].groupby('Kingdom').size()
    off = nbk.groupby('Kingdom').size()
    out['kingdoms'] = {k: dict(crowd_species=int(g.species.get(k, 0)), crowd_obs=int(g.observations.get(k, 0)),
                               assessed=int(off.get(k, 0)), assessed_seen=int(seen_by_kingdom.get(k, 0)))
                       for k in ['Animalia', 'Plantae', 'Fungi', 'Chromista', 'Protozoa']}
    grp = inat.groupby('group').agg(species=('id', 'size'), observations=('count', 'sum')).sort_values('observations', ascending=False)
    out['groups'] = {k: dict(species=int(v.species), observations=int(v.observations),
                             obs_per_species=float(v.observations / v.species)) for k, v in grp.iterrows()}

    # ------------------------------------------------ 4. threat categories vs the crowd
    obs = inat.groupby('key')['count'].sum()
    nz['crowd_obs'] = nz.key.map(obs).fillna(0).astype(int)
    out['binomial_share'] = float(nz.binomial.mean())
    nb = nz[nz.binomial]
    cats = {}
    for cat, s in nb.groupby('Category'):
        if len(s) < 50:
            continue
        cats[cat] = dict(n=int(len(s)), seen=float((s.crowd_obs > 0).mean()),
                         seen5=float((s.crowd_obs >= 5).mean()), median_obs=float(s.crowd_obs.median()))
    out['categories'] = dict(sorted(cats.items(), key=lambda kv: -kv[1]['seen']))
    out['matched_assessed'] = dict(n=int(len(nb)), seen=int((nb.crowd_obs > 0).sum()))

    # Data Deficient species the crowd has photographed: the candidates where
    # citizen data could feed the next assessment
    dd = nb[(nb.Category == 'Data Deficient') & (nb.crowd_obs > 0)].sort_values('crowd_obs', ascending=False)
    out['data_deficient'] = dict(total=int((nb.Category == 'Data Deficient').sum()), seen=int(len(dd)),
                                 seen10=int((dd.crowd_obs >= 10).sum()), seen50=int((dd.crowd_obs >= 50).sum()))
    by_k = dd.groupby('Kingdom').size().to_dict()
    out['data_deficient']['by_kingdom'] = {k: int(v) for k, v in by_k.items()}

    # ------------------------------------------------ 5. where the crowd looks
    cells = []
    for f in CACHE.glob('grid_*.json'):
        _, lat, lng = f.stem.split('_')
        n = json.loads(f.read_text())['total_results']
        if n:
            cells.append([float(lat), float(lng), int(n)])
    cells.sort()
    out['grid'] = cells
    tot = sum(c[2] for c in cells)
    top = sorted((c[2] for c in cells), reverse=True)
    k10 = max(1, round(len(top) * .1))
    out['grid_summary'] = dict(cells=len(cells), total=tot, top10pct_share=float(sum(top[:k10]) / tot),
                               median=float(np.median(top)), max=int(top[0]))

    (HERE / 'results.json').write_text(json.dumps(out, indent=1))

    # tool data: every assessed species with its crowd count
    cols = ['Current Species Name', 'Preferred Common Name', 'Preferred Māori Name', 'Category', 'Status', 'Kingdom',
            'Phylum', 'Bio Status', 'crowd_obs']
    tool = nz[cols].fillna('')
    flags = nz['binomial'].values
    rows = [[r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], int(r[8]), int(bool(f))]
            for r, f in zip(tool.itertuples(index=False), flags)]
    (HERE / 'species.json').write_text(json.dumps(rows, ensure_ascii=False, separators=(',', ':')))
    print('written', json.dumps({k: out[k] for k in ('now', 'matched_assessed', 'data_deficient', 'grid_summary')}, indent=1))


if __name__ == '__main__':
    main()
