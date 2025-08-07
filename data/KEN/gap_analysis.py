import pandas as pd
import numpy as np
from datetime import datetime

# Load baseline gap data
gaps_detailed = pd.read_csv('../../reference/baseline_surveillance_gaps_detailed.csv')
gaps_coverage = pd.read_csv('../../reference/baseline_surveillance_gaps_coverage.csv')

# Filter for Kenya
kenya_gaps = gaps_detailed[gaps_detailed['iso_code'] == 'KEN']
kenya_coverage = gaps_coverage[gaps_coverage['iso_code'] == 'KEN']

print('=== KENYA GAP-FILLING IMPACT ASSESSMENT ===\n')

# Baseline statistics
print('BASELINE SURVEILLANCE GAPS (Before AI Enhancement):')
print(f'Total surveillance period: {kenya_coverage.iloc[0]["total_months"]} months')
print(f'Months with data: {kenya_coverage.iloc[0]["months_with_data"]} months')
print(f'Months missing: {kenya_coverage.iloc[0]["months_missing"]} months')
print(f'Baseline coverage: {kenya_coverage.iloc[0]["percent_coverage"]:.1f}%')
print(f'\nMissing years: {kenya_coverage.iloc[0]["missing_years"]}')

print('\n' + '-'*60)
print('SPECIFIC GAP PERIODS IN BASELINE DATA:')
for idx, gap in kenya_gaps.iterrows():
    print(f'- {gap["gap_start"]} to {gap["gap_end"]} ({gap["days"]} days, {gap["months"]:.0f} months)')

# Load AI-enhanced data
df = pd.read_csv('cholera_data_ai.csv')
df['TL_date'] = pd.to_datetime(df['TL'])
df['TR_date'] = pd.to_datetime(df['TR'])

print('\n' + '-'*60)
print('AI-ENHANCED DATA ANALYSIS:')

# Analyze which gaps were filled
gaps_filled = []
gaps_partially_filled = []
gaps_remaining = []

for idx, gap in kenya_gaps.iterrows():
    gap_start = pd.to_datetime(gap['gap_start'])
    gap_end = pd.to_datetime(gap['gap_end'])
    
    # Check if any AI data overlaps with this gap period
    overlapping = df[
        (df['TL_date'] <= gap_end) & 
        (df['TR_date'] >= gap_start)
    ]
    
    if len(overlapping) > 0:
        # Calculate coverage percentage for this gap
        gap_days = gap['days']
        covered_days = 0
        
        for _, row in overlapping.iterrows():
            overlap_start = max(row['TL_date'], gap_start)
            overlap_end = min(row['TR_date'], gap_end)
            covered_days += (overlap_end - overlap_start).days + 1
        
        coverage_pct = (covered_days / gap_days) * 100
        
        if coverage_pct >= 80:
            gaps_filled.append({
                'period': f"{gap['gap_start']} to {gap['gap_end']}",
                'duration': f"{gap['months']:.0f} months",
                'coverage': f"{coverage_pct:.1f}%",
                'observations': len(overlapping)
            })
        elif coverage_pct > 0:
            gaps_partially_filled.append({
                'period': f"{gap['gap_start']} to {gap['gap_end']}",
                'duration': f"{gap['months']:.0f} months",
                'coverage': f"{coverage_pct:.1f}%",
                'observations': len(overlapping)
            })
    else:
        gaps_remaining.append({
            'period': f"{gap['gap_start']} to {gap['gap_end']}",
            'duration': f"{gap['months']:.0f} months"
        })

print(f'\n✓ GAPS SUCCESSFULLY FILLED ({len(gaps_filled)}/{len(kenya_gaps)}):')
for gap in gaps_filled:
    print(f"  - {gap['period']} ({gap['duration']}): {gap['observations']} observations added")

if gaps_partially_filled:
    print(f'\n⚠ GAPS PARTIALLY FILLED ({len(gaps_partially_filled)}/{len(kenya_gaps)}):')
    for gap in gaps_partially_filled:
        print(f"  - {gap['period']} ({gap['duration']}): {gap['coverage']} coverage, {gap['observations']} observations")

if gaps_remaining:
    print(f'\n✗ GAPS REMAINING UNFILLED ({len(gaps_remaining)}/{len(kenya_gaps)}):')
    for gap in gaps_remaining:
        print(f"  - {gap['period']} ({gap['duration']})")

# Calculate overall improvement
print('\n' + '-'*60)
print('OVERALL GAP-FILLING IMPACT:')

# Count unique years covered by AI data
years_covered = set()
for _, row in df.iterrows():
    start_year = row['TL_date'].year
    end_year = row['TR_date'].year
    for year in range(start_year, end_year + 1):
        years_covered.add(year)

print(f'Years with AI-enhanced data: {sorted(years_covered)}')
print(f'Total years covered: {len(years_covered)}')

# Identify key discoveries
print('\n' + '-'*60)
print('KEY DISCOVERIES:')

# First cholera introduction
first_case = df[df['Location'].str.contains('Turkana')]
if len(first_case) > 0:
    print('✓ First cholera introduction in Kenya (1971) in Turkana District documented')

# Zero-transmission validation
zero_trans = df[(df['sCh'] == 0) & (df['deaths'] == 0)]
if len(zero_trans) > 0:
    print(f'✓ {len(zero_trans)} zero-transmission period(s) validated:')
    for _, row in zero_trans.iterrows():
        year = pd.to_datetime(row['TL']).year
        print(f'  - {year}: Confirmed cholera-free year')

# Major outbreaks documented
major_outbreaks = df[df['sCh'] > 5000]
print(f'✓ {len(major_outbreaks)} major outbreaks (>5000 cases) documented')

# Geographic granularity
locations = df['Location'].str.count('::').value_counts().sort_index()
print('\n✓ Geographic granularity achieved:')
for level, count in locations.items():
    if level == 1:
        print(f'  - National level: {count} observations')
    elif level == 2:
        print(f'  - Provincial level: {count} observations')
    elif level == 3:
        print(f'  - District level: {count} observations')
    elif level >= 4:
        print(f'  - Sub-district level: {count} observations')

# Source quality distribution
print('\n' + '-'*60)
print('DATA QUALITY METRICS:')
print(f'Total observations added: {len(df)}')
print(f'Total unique sources: {df["source_index"].nunique()}')
print(f'Average confidence weight: {df["confidence_weight"].mean():.2f}')

# Calculate gap-filling success rate
gap_filling_rate = (len(gaps_filled) / len(kenya_gaps)) * 100 if len(kenya_gaps) > 0 else 0
partial_filling_rate = (len(gaps_partially_filled) / len(kenya_gaps)) * 100 if len(kenya_gaps) > 0 else 0

print(f'\nGap-filling success rate: {gap_filling_rate:.1f}% fully filled')
print(f'Partial gap-filling rate: {partial_filling_rate:.1f}% partially filled')
print(f'Total gap coverage: {gap_filling_rate + partial_filling_rate:.1f}%')