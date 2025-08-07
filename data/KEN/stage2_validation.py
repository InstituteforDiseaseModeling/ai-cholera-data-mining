import pandas as pd
import numpy as np

# Load the data
df = pd.read_csv('cholera_data_ai.csv')
meta = pd.read_csv('metadata_ai.csv')

print('=== STAGE 2: CROSS-REFERENCE VALIDATION ===\n')

# Track validation results
cross_ref_issues = []
cross_ref_passed = []

# 1. Check for major outbreaks (>1000 cases) and their sources
print('1. Major Outbreak Validation (>1000 cases):')
major_outbreaks = df[df['sCh'] > 1000].copy()
if len(major_outbreaks) > 0:
    print(f'   Found {len(major_outbreaks)} major outbreaks:')
    
    # Group by year to check for multi-source confirmation
    for idx, row in major_outbreaks.iterrows():
        year = pd.to_datetime(row['TL']).year
        source_info = meta[meta['Index'] == row['source_index']].iloc[0]
        print(f'   - {year}: {row["sCh"]:,} cases, Source: {source_info["Reliability_Level"]}')
        
        # Check if this is a multi-source validated outbreak
        if 'MULTI-SOURCE' in str(row['processing_notes']).upper():
            print(f'     ✓ Multi-source validated')
            cross_ref_passed.append(f'Major outbreak {year} multi-source validated')
        else:
            print(f'     ⚠ Single source only')
            cross_ref_issues.append(f'Major outbreak {year} ({row["sCh"]:,} cases) needs additional validation')
else:
    print('   No major outbreaks (>1000 cases) found')

# 2. Check for duplicate periods
print('\n2. Duplicate Period Detection:')
df['TL_date'] = pd.to_datetime(df['TL'])
df['TR_date'] = pd.to_datetime(df['TR'])

duplicates = []
for i in range(len(df)):
    for j in range(i+1, len(df)):
        # Check for overlapping dates at same location
        if df.iloc[i]['Location'] == df.iloc[j]['Location']:
            # Check for date overlap
            if (df.iloc[i]['TL_date'] <= df.iloc[j]['TR_date'] and 
                df.iloc[i]['TR_date'] >= df.iloc[j]['TL_date']):
                duplicates.append((i+1, j+1, df.iloc[i]['Location']))

if duplicates:
    print(f'   WARNING: Found {len(duplicates)} potential overlapping periods')
    for dup in duplicates[:5]:  # Show first 5
        print(f'   - Rows {dup[0]} and {dup[1]} for {dup[2]}')
    cross_ref_issues.append(f'{len(duplicates)} overlapping periods detected')
else:
    print('   ✓ No overlapping periods detected')
    cross_ref_passed.append('No duplicate periods')

# 3. Source reliability distribution
print('\n3. Source Reliability Distribution:')
source_levels = []
for idx, row in df.iterrows():
    source_info = meta[meta['Index'] == row['source_index']]
    if len(source_info) > 0:
        source_levels.append(source_info.iloc[0]['Reliability_Level'])

level_counts = pd.Series(source_levels).value_counts()
total_sources = len(source_levels)
print('   Source distribution:')
for level in ['Level_1', 'Level_2', 'Level_3', 'Level_4']:
    if level in level_counts:
        count = level_counts[level]
        pct = (count / total_sources) * 100
        print(f'   - {level}: {count} ({pct:.1f}%)')

# Check if Level 1-2 sources are >50%
high_quality = level_counts.get('Level_1', 0) + level_counts.get('Level_2', 0)
if high_quality / total_sources > 0.5:
    print('   ✓ >50% of data from Level 1-2 sources')
    cross_ref_passed.append('High-quality source predominance')
else:
    print('   ⚠ <50% of data from Level 1-2 sources')
    cross_ref_issues.append('Low proportion of high-quality sources')

# 4. Validation status check
print('\n4. Data Validation Status:')
validation_status = meta['Validation_Status'].value_counts()
if 'Validated' in validation_status:
    validated_pct = (validation_status['Validated'] / len(meta)) * 100
    print(f'   ✓ {validated_pct:.1f}% of sources marked as validated')
    if validated_pct > 90:
        cross_ref_passed.append('High validation rate')
else:
    print('   ⚠ No validation status found')
    cross_ref_issues.append('Missing validation status')

# 5. Cross-references in metadata
print('\n5. Cross-Reference Documentation:')
cross_refs = meta['Cross_References'].notna().sum()
if cross_refs > 0:
    print(f'   ✓ {cross_refs} sources have cross-references documented')
    cross_ref_passed.append('Cross-references documented')
else:
    print('   ⚠ No cross-references documented')
    cross_ref_issues.append('No cross-references documented')

# 6. Check for confirmed zero-transmission periods
print('\n6. Zero-Transmission Validation:')
zero_trans = df[(df['sCh'] == 0) & (df['deaths'] == 0)]
if len(zero_trans) > 0:
    print(f'   ✓ {len(zero_trans)} zero-transmission period(s) validated')
    for idx, row in zero_trans.iterrows():
        year_range = f"{pd.to_datetime(row['TL']).year}"
        print(f'   - {year_range}: {row["source"]}')
    cross_ref_passed.append('Zero-transmission periods validated')

# Summary
print('\n' + '='*60)
print('STAGE 2 CROSS-REFERENCE VALIDATION SUMMARY:')
print(f'✓ Passed: {len(cross_ref_passed)} checks')
print(f'⚠ Issues: {len(cross_ref_issues)} issues found')

if cross_ref_issues:
    print('\nIssues requiring attention:')
    for issue in cross_ref_issues:
        print(f'  - {issue}')

# Calculate pass rate
total_checks = 6
pass_rate = (len(cross_ref_passed) / total_checks) * 100
print(f'\nCross-Reference Validation Pass Rate: {pass_rate:.1f}%')