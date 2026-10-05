"""Build site/nz-biodiversity.html from the case-study template and the
analysis outputs. Re-run after run.py to refresh the numbers.

    ../.venv/bin/python build_page.py
"""
import json
import pathlib
import re
import shutil

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parents[1] / 'site'
R = json.loads((HERE / 'results.json').read_text())

N, ST = R['now'], R['study_2024']
G = R['groups']
C = R['categories']
DD = R['data_deficient']
K = R['kingdoms']
GS = R['grid_summary']
ret = R['returns']
Y = {r['year']: r for r in R['years']}
pc = lambda v: f'{round(v * 100)}%'
n = lambda v: f'{round(v):,}'
REPO = 'https://github.com/s0larpunk/iNaturalist_NZ_Biodiversity'
POSTER = 'https://maximvelli.com/wp-content/uploads/2025/10/Group_A2_hor_min.pdf'

birds, fungi = G['Aves']['obs_per_species'], G['Fungi']['obs_per_species']
early = next(r for r in ret if r['span'].startswith('2014'))
late = ret[-1]


def kv(k, v, cls=''):
    c = f' class="{cls}"' if cls else ''
    return f'<div{c}><span class="ui k">{k}</span><p class="v">{v}</p></div>'


def sec(i, tag, h2, body, center=False, sid=''):
    style = ' style=color:var(--orange)' if center else ''
    ident = f' id="{sid}"' if sid else ''
    return (f'<section class="sec{" center" if center else ""}"{ident}>\n    <span class="ui"{style}>{i:02d} / {tag}</span>\n'
            f'    <h2>{h2}</h2>\n    {body}\n    </section>')


def lead(t):
    return f'<p class="lead">{t}</p>'


def fig(host, legend, cap):
    leg = ''.join(f'<span><i style="background:{c}"></i>{t}</span>' for t, c in legend)
    return (f'<figure class="mt-fig"><div id="{host}"></div>'
            + (f'<div class="mt-legend">{leg}</div>' if leg else '') + f'<p class="mt-cap">{cap}</p></figure>')


body = f'''<header class="hero">
    <div class="eyebrow"><span class="layertag">Method — Data analysis · Open science · Web tool</span><span class="ui">Learning Planet Institute, Paris · 2024, re-run 2026</span></div>
    <h1>Counted by the <span class="lo">Crowd</span></h1>
    <p class="thesis">Volunteers with phones have now recorded {n(N['species'])} species in New Zealand, and the useful part of their work is where it could fill gaps that experts <span class="lo">cannot reach</span>.</p>
    <p class="sub">In 2024 Lola Kengen, Eva Koskova, Tarek Nouneh and I asked how close iNaturalist, the citizen science platform where anyone can photograph an organism and the community identifies it, comes to the official picture of New Zealand's biodiversity. In October 2026 I pulled the data again, two and a half years on, and asked a sharper question: where crowd knowledge can add something the official record lacks.</p>
  </header>

  <section class="strip">
    {kv('Brief', 'An open science project at the Learning Planet Institute: test how far a crowdsourced platform can stand in for expert biodiversity surveys, which are slow and expensive to run across a whole country.')}
    {kv('Insight', f'The crowd does not converge on the full count of species. It converges on what people can reach and recognise, and its estimate of the total has stayed near {n(N["chao1"] / 1000)} thousand species while new records keep arriving. Its value lies in the gaps it happens to cover.')}
    {kv('Outcome', f'A re-run on {Y[2026]["observations"] / 1e6:.1f} million verified records, a measure of how much effort each new species now costs, a map of where the crowd looks, a match against the official threat list, and a tool that finds the species experts lack data on and volunteers have already photographed.')}
    {kv('Future', 'Biodiversity monitoring combines expert surveys with crowd records that are steered toward the species and places experts cannot reach.', 'future')}
  </section>
  <section class="meta">
    {kv('Role', 'Research question, data extraction and analysis in 2024; the 2026 re-run, analysis and tool')}
    {kv('Where', 'Learning Planet Institute, Paris · open science course, 2024 · re-run October 2026')}
    {kv('With', 'Lola Kengen, Eva Koskova, Tarek Nouneh · supervision Ignacio Atal, Rona Aviram, Marc Santolini')}
  </section>
  <nav class="btnrow"><a class="btn" href="#nz-try">Find the gaps ↓</a><a class="btn" href="{POSTER}">2024 poster ↗</a><a class="btn" href="{REPO}">Code on GitHub ↗</a></nav>

  {sec(1, 'The question', 'How much of a country can a crowd count?', lead(
      f'New Zealand is a good test case: about {n(R["known_total"])} species are known to science there, the national threat classification is public, and iNaturalist is widely used. In February 2024 the platform held records of {n(ST["species"])} species. Using the standard estimators ecologists apply when a survey cannot be complete, which extrapolate from how many species have been seen only once or twice, we estimated that the crowd would level off at around {n(ST["chao1"])} species, well short of the official figure. We put the gap down to uneven sampling: people record what is near roads, towns and trails.'))}

  {sec(2, 'Two and a half years later', 'More records, the same ceiling', lead(
      f'By October 2026 the verified records had grown to {Y[2026]["observations"] / 1e6:.1f} million and the species count to {n(N["species"])}. The estimate of where the crowd will level off barely moved: {n(N["chao1"])}, with a 95% range of {n(N["chao1_ci"][0])} to {n(N["chao1_ci"][1])}.')
      + fig('nz-growth', [('species recorded', 'var(--orange)'), ('verified observations', 'var(--olive)')],
            'Cumulative species and verified observations in New Zealand on iNaturalist, by year. Hover over a point for the number of people observing that year.')
      + fig('nz-est', [], 'Species recorded by the crowd and estimated from its records (Chao1, with its 95% range as a line), in 2024 and 2026, against the number known to science. The 2024 counts come from a GBIF export that included subspecies; the 2026 counts are species only, so the true growth is slightly larger than the bars suggest.')
      + lead(f'Each new species now takes far more effort to find. In {early["span"]} every 100,000 new observations added about {n(early["per100k"])} species; in {late["span"]} they added about {n(late["per100k"])}. The estimators are measuring the ceiling of what this crowd, with its habits, can reach, which is a useful number in its own right and a different one from New Zealand\'s biodiversity.'))}

  {sec(3, 'What the crowd looks at', 'Birds over fungi', lead(
      f'Attention is spread very unevenly. Each bird species has on average {n(birds)} verified observations; each fungus {n(fungi)}, and each slime mould or other single-celled organism even fewer. Bacteria and archaea, which make up much of the life in any soil or gut, do not appear at all, because nobody can photograph them.')
      + fig('nz-att', [], 'Average verified observations per species, by group, on a logarithmic scale. Groups with fewer than 20 species recorded are left out.')
      + lead('For my own field this is the striking result. Biotechnology works mostly with fungi, microbes and other organisms that are small, hidden or hard to identify, and those are exactly the groups the crowd sees least. A public that knows its birds well knows very little about the organisms that a bio-based economy would depend on.'))}

  {sec(4, 'Where the crowd looks', 'Close to home', lead(
      f'Counting records on a half-degree grid shows the other bias. The busiest tenth of the grid cells hold {pc(GS["top10pct_share"])} of all observations, most of them around the cities, from Auckland and Wellington to Christchurch and Dunedin, while large parts of the backcountry have a few hundred records per cell or fewer.')
      + fig('nz-map', [], 'Verified iNaturalist observations per half-degree cell; larger and warmer dots mean more records. Hover for the count.'))}

  {sec(5, 'Where it could matter', 'The species experts know least about', lead(
      f'Matching the crowd\'s records against the {n(R["matched_assessed"]["n"])} species in New Zealand\'s official threat classification (counting plain species only, since subspecies and varieties cannot be told apart in the crowd data) gives a more useful picture than the total. The crowd has recorded {pc(C["Threatened"]["seen"])} of the species classed as Threatened, often many times, because rare birds and plants attract photographers. It has recorded only {pc(C["Data Deficient"]["seen"])} of the {n(DD["total"])} species classed as Data Deficient, the ones the experts cannot assess for lack of information.')
      + fig('nz-threat', [('recorded at least once', 'var(--olive)'), ('recorded five times or more (darker)', 'color-mix(in srgb,var(--ink) 40%,var(--olive))')],
            'Share of species in each category of New Zealand\'s threat classification that have at least one verified iNaturalist record.')
      + lead(f'That small overlap is where the opportunity lies. {n(DD["seen"])} Data Deficient species have crowd records, {n(DD["seen10"])} of them ten or more and {n(DD["seen50"])} fifty or more, a set of locations and dates that the next assessment could start from.')
      + '<p class="pull">The crowd\'s value is less in how much it sees than in <em>which gaps</em> it happens to cover.</p>'
      + '<div class="honest"><span class="ui">The honest part</span><p class="lead">Crowd records only show that a species was there, never that it was absent, and they follow people rather than a survey design, so they cannot by themselves show whether a population is growing or shrinking. Research-grade identifications are right about 85% of the time. And our 2024 comparison set the crowd against the threat classification as if it were a full species list, which it is not; this version compares like with like.</p></div>', center=True)}

  {sec(6, 'Find the gaps', 'Species the crowd could help reassess', lead(
      'The tool lists every species in the official classification with its number of verified crowd records. By default it shows the Data Deficient species that volunteers have already photographed, sorted by how often, which is where the two kinds of knowledge could meet first. Each count links to the records on iNaturalist.')
      + '<div id="nz-finder"></div><p class="mt-cap">Species-level matches by name between the New Zealand Threat Classification System export and iNaturalist research-grade records, October 2026. Subspecies and varieties show the count for their whole species.</p>',
      sid='nz-try')}

  <section class="reflect">
    <span class="ui" style="display:block;margin-bottom:1rem">Reflection</span>
    <h2>Designing where people look</h2>
    <p class="lead" style=margin-top:1.2rem>In 2024 we asked whether the crowd could replace expert surveys, and the answer was no. The more useful question turned out to be how to point the crowd at what the experts are missing, since its effort already exists at a scale no survey programme could pay for.</p><p class="lead">The demand for that is growing outside science too. Europe's sustainability reporting standards ask companies to report their impacts on biodiversity, and the data to do that at scale is patchy at best. The product that would help is less a bigger database than a way of steering attention: telling a volunteer, a farmer or a site manager which organism, in which place, would add the most to what is known.</p>
  </section>
</div>

<div class="aph gg"><div class="wrap"><p>The crowd counts what it can reach. The work is deciding where it should look next.</p><span class="ui" style="display:block;margin-top:.8rem">From the 2026 re-run</span></div></div>

<div class="wrap">
  <div class="next"><span class="ui">Next</span><a href="music-trends.html">The Sound of the Mainstream →</a></div>
  '''


def main():
    tpl = (SITE / 'scentopia.html').read_text(encoding='utf-8')
    s = re.sub(r' data-ed="e\d+"', '', tpl)
    s = re.sub(r'<title>[^<]*</title>', '<title>Counted by the Crowd — Maxim Velli</title>', s)
    for var in ('--p1', '--p2', '--p3'):
        i = s.find(f'{var}:url(')
        j = s.index(')', i) + 1
        s = s[:i] + f'{var}:none' + s[j:]
    a, b = s.find('<header class="hero">'), s.find('<div class="foot">')
    s = s[:a] + body + s[b:]
    k = s.rfind('</style>')
    s = s[:k] + (HERE / 'page.css').read_text() + s[k:]
    js = (HERE / 'page.js').read_text()
    k = s.rfind('</body>')
    s = s[:k] + f'<script type="application/json" id="nz-results">{json.dumps(R)}</script>\n<script>{js}</script>\n' + s[k:]
    (SITE / 'nz-biodiversity.html').write_text(s, encoding='utf-8')
    shutil.copy(HERE / 'species.json', SITE / 'nz-species.json')
    print('wrote', SITE / 'nz-biodiversity.html')


if __name__ == '__main__':
    main()
