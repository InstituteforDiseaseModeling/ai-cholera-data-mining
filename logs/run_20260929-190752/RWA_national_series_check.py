"""READ-ONLY diagnostic: emulate py/build_weekly_timeseries.py in memory for one country
(no files written) and compare the built national weekly series, per year, with the
annual national rows and with the sum of sub-national rows. Usage:
    python /tmp/rwa_orch/national_series_check.py RWA [year_from]
"""
import sys, io, contextlib, collections
sys.path.insert(0, 'py')
import pandas as pd
import build_weekly_timeseries as b

iso = sys.argv[1] if len(sys.argv) > 1 else 'RWA'
y0 = int(sys.argv[2]) if len(sys.argv) > 2 else 1970
cm = b.load_country_map()
with contextlib.redirect_stdout(io.StringIO()):
    templates = b.build_all_templates(cm)
    merged = b.process_country(iso, templates[iso] if isinstance(templates, dict) and iso in templates else templates)
built = collections.defaultdict(float); meth = collections.defaultdict(collections.Counter)
for k, v in merged.items():
    built[v['monday'].year] += v['sch'] or 0.0
    meth[v['monday'].year][v['method']] += 1
d = pd.read_csv(f'data/{iso}/cholera_data_ai.csv', parse_dates=['TL', 'TR'])
nat = d[d.Location == f'AFR::{iso}']; sub = d[d.Location != f'AFR::{iso}']
ann = nat[(nat.TR - nat.TL).dt.days >= 300]
rows = []
for y in sorted(set(built) | set(ann.TL.dt.year)):
    if y < y0: continue
    a = ann[ann.TL.dt.year == y].sCh.sum() if (ann.TL.dt.year == y).any() else None
    s = sub[(sub.TL.dt.year == y)].sCh.sum()
    rows.append((y, round(built.get(y, 0.0), 1), a, s, dict(meth[y])))
print(f"{'year':>4} {'built_national':>14} {'annual_row':>10} {'subnat_sum':>10}  methods")
for y, bv, a, s, m in rows:
    flag = ''
    if a is not None and a > 0 and bv < 0.8 * a: flag = '  <-- built < 80% of annual row'
    elif s and bv < 0.8 * s: flag = '  <-- built < 80% of sub-national sum'
    print(f"{y:>4} {bv:>14} {str(a):>10} {s:>10}  {m}{flag}")
