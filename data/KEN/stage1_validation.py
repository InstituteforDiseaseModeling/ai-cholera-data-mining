import pandas as pd
import numpy as np
from datetime import datetime

# Load the data
df = pd.read_csv('cholera_data_ai.csv')
meta = pd.read_csv('metadata_ai.csv')

print('=== STAGE 1: AUTOMATED EPIDEMIOLOGICAL VALIDATION ===\n')

# Track validation results
validation_issues = []
validation_passed = []

# 1. CFR Range Validation (0.1% - 15%)
print('1. CFR Range Validation:')
cfr_mask = df['CFR'].notna()
cfr_values = df.loc[cfr_mask, 'CFR']
invalid_cfr = df[(cfr_mask) & ((df['CFR'] < 0.1) | (df['CFR'] > 15))]
if len(invalid_cfr) > 0:
    print(f'   WARNING: {len(invalid_cfr)} rows with CFR outside 0.1-15% range')
    for idx, row in invalid_cfr.iterrows():
        print(f'   - Row {row["Index"]}: CFR={row["CFR"]}% for {row["Location"]} ({row["TL"]})')
        validation_issues.append(f'Row {row["Index"]}: CFR={row["CFR"]}% outside normal range')
else:
    print('   ✓ All CFR values within epidemiological range')
    validation_passed.append('CFR validation')

# 2. Mathematical Consistency (deaths <= sCh)
print('\n2. Mathematical Consistency:')
death_mask = df['deaths'].notna() & df['sCh'].notna()
invalid_math = df[(death_mask) & (df['deaths'] > df['sCh'])]
if len(invalid_math) > 0:
    print(f'   ERROR: {len(invalid_math)} rows where deaths > suspected cases')
    for idx, row in invalid_math.iterrows():
        print(f'   - Row {row["Index"]}: deaths={row["deaths"]}, sCh={row["sCh"]}')
        validation_issues.append(f'Row {row["Index"]}: deaths exceed suspected cases')
else:
    print('   ✓ All death counts consistent with case counts')
    validation_passed.append('Mathematical consistency')

# 3. Temporal Logic (TL <= TR, reporting_date >= TR)
print('\n3. Temporal Logic Validation:')
df['TL_date'] = pd.to_datetime(df['TL'])
df['TR_date'] = pd.to_datetime(df['TR'])
df['reporting_date_dt'] = pd.to_datetime(df['reporting_date'])

temporal_issues = []
# Check TL <= TR
invalid_period = df[df['TL_date'] > df['TR_date']]
if len(invalid_period) > 0:
    temporal_issues.append(f'{len(invalid_period)} rows where start date > end date')
    
# Check reporting_date >= TR
invalid_reporting = df[df['reporting_date_dt'] < df['TR_date']]
if len(invalid_reporting) > 0:
    temporal_issues.append(f'{len(invalid_reporting)} rows where reporting date < end date')

if temporal_issues:
    print(f'   WARNING: {", ".join(temporal_issues)}')
    validation_issues.extend(temporal_issues)
else:
    print('   ✓ All temporal relationships valid')
    validation_passed.append('Temporal logic')

# 4. Outbreak Duration (1 week to 2 years)
print('\n4. Outbreak Duration Validation:')
df['duration_days'] = (df['TR_date'] - df['TL_date']).dt.days
unusual_duration = df[(df['duration_days'] < 7) | (df['duration_days'] > 730)]
if len(unusual_duration) > 0:
    print(f'   INFO: {len(unusual_duration)} rows with unusual duration (<7 days or >2 years)')
    for idx, row in unusual_duration.iterrows():
        print(f'   - Row {row["Index"]}: {row["duration_days"]} days for {row["Location"]}')
else:
    print('   ✓ All outbreak durations within typical range')
    validation_passed.append('Duration validation')

# 5. Geographic Standardization
print('\n5. Geographic Standardization:')
invalid_geo = df[~df['Location'].str.match(r'^AFR::[A-Z]{3}')]
if len(invalid_geo) > 0:
    print(f'   ERROR: {len(invalid_geo)} rows with invalid geographic codes')
    validation_issues.append(f'{len(invalid_geo)} invalid geographic codes')
else:
    print('   ✓ All geographic codes properly formatted')
    validation_passed.append('Geographic standardization')

# 6. Confidence Weight Range (0.1 - 1.0)
print('\n6. Confidence Weight Validation:')
invalid_weight = df[(df['confidence_weight'] < 0.1) | (df['confidence_weight'] > 1.0)]
if len(invalid_weight) > 0:
    print(f'   ERROR: {len(invalid_weight)} rows with invalid confidence weights')
    validation_issues.append(f'{len(invalid_weight)} invalid confidence weights')
else:
    print('   ✓ All confidence weights within valid range')
    validation_passed.append('Confidence weight validation')

# 7. Source Database Values
print('\n7. Source Database Validation:')
valid_dbs = ['JHU', 'WHO', 'AI']
invalid_db = df[~df['source_database'].isin(valid_dbs)]
if len(invalid_db) > 0:
    print(f'   ERROR: {len(invalid_db)} rows with invalid source_database values')
    validation_issues.append(f'{len(invalid_db)} invalid source_database values')
else:
    print('   ✓ All source_database values valid')
    validation_passed.append('Source database validation')

# 8. Check for zero-transmission entries
print('\n8. Zero-Transmission Documentation:')
zero_trans = df[(df['sCh'] == 0) & (df['deaths'] == 0)]
if len(zero_trans) > 0:
    print(f'   ✓ Found {len(zero_trans)} zero-transmission period(s) documented')
    validation_passed.append('Zero-transmission documentation')
else:
    print('   INFO: No zero-transmission periods documented')

# Summary
print('\n' + '='*60)
print('STAGE 1 VALIDATION SUMMARY:')
print(f'✓ Passed: {len(validation_passed)} checks')
print(f'⚠ Issues: {len(validation_issues)} issues found')

if validation_issues:
    print('\nIssues requiring attention:')
    for issue in validation_issues:
        print(f'  - {issue}')
        
# Calculate pass rate
total_checks = 8
pass_rate = (len(validation_passed) / total_checks) * 100
print(f'\nValidation Pass Rate: {pass_rate:.1f}%')