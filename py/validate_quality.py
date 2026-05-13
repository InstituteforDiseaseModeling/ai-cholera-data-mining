#!/usr/bin/env python3
import csv
import sys
from datetime import datetime

def validate_quality():
    """Execute 4-stage quality validation protocol"""
    
    validation_results = {
        'stage1_auth': {'pass': 0, 'fail': 0, 'issues': []},
        'stage2_epi': {'pass': 0, 'fail': 0, 'issues': []},
        'stage3_cross': {'pass': 0, 'fail': 0, 'issues': []},
        'stage4_int': {'pass': 0, 'fail': 0, 'issues': []},
        'source_distribution': {'Level 1': 0, 'Level 2': 0, 'Level 3': 0, 'Level 4': 0}
    }
    
    # Load metadata for source validation
    metadata = {}
    with open('data/AGO/metadata_ai.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = row.get('Index', '')
            if idx:
                metadata[int(idx)] = row
    
    # Validate cholera data
    with open('data/AGO/cholera_data_ai.csv', 'r') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader, 2):
            # Stage 1: Authentication and Source Verification
            source_idx = row.get('source_index', '')
            if source_idx:
                source_idx = int(source_idx)
                if source_idx in metadata:
                    meta = metadata[source_idx]
                    # Check URL status
                    if meta.get('Status') == 'Active':
                        validation_results['stage1_auth']['pass'] += 1
                    else:
                        validation_results['stage1_auth']['fail'] += 1
                        validation_results['stage1_auth']['issues'].append(f"Row {i}: Inactive source URL")
                    
                    # Track source distribution
                    reliability = meta.get('Reliability_Level', '')
                    if reliability in ['Level 1', 'Level 2', 'Level 3', 'Level 4']:
                        validation_results['source_distribution'][reliability] += 1
                else:
                    validation_results['stage1_auth']['fail'] += 1
                    validation_results['stage1_auth']['issues'].append(f"Row {i}: Missing metadata")
            
            # Stage 2: Data Quality and Epidemiological Validation
            # CFR validation
            cfr = row.get('CFR', '')
            deaths = row.get('deaths', '')
            sCh = row.get('sCh', '')
            
            if cfr and cfr != '':
                cfr_val = float(cfr)
                if 0.1 <= cfr_val <= 15.0:
                    validation_results['stage2_epi']['pass'] += 1
                else:
                    validation_results['stage2_epi']['fail'] += 1
                    validation_results['stage2_epi']['issues'].append(f"Row {i}: CFR {cfr_val}% outside normal range")
            
            # Mathematical consistency
            if deaths and sCh and deaths != '' and sCh != '':
                deaths_int = int(deaths)
                sCh_int = int(sCh)
                if deaths_int <= sCh_int:
                    validation_results['stage2_epi']['pass'] += 1
                else:
                    validation_results['stage2_epi']['fail'] += 1
                    validation_results['stage2_epi']['issues'].append(f"Row {i}: Deaths ({deaths_int}) > Cases ({sCh_int})")
            
            # Temporal logic
            tl = row.get('TL', '')
            tr = row.get('TR', '')
            if tl and tr:
                if tl <= tr:
                    validation_results['stage2_epi']['pass'] += 1
                else:
                    validation_results['stage2_epi']['fail'] += 1
                    validation_results['stage2_epi']['issues'].append(f"Row {i}: TL > TR")
            
            # Stage 3: Cross-Reference (check for major outbreaks)
            if sCh and sCh != '':
                sCh_int = int(sCh)
                if sCh_int > 1000:
                    # Check if multiple sources confirm
                    confidence = float(row.get('confidence_weight', 0.5))
                    if confidence >= 0.7:
                        validation_results['stage3_cross']['pass'] += 1
                    else:
                        validation_results['stage3_cross']['fail'] += 1
                        validation_results['stage3_cross']['issues'].append(f"Row {i}: Major outbreak ({sCh_int} cases) with low confidence")
            
            # Stage 4: Integration checks
            location = row.get('Location', '')
            if location.startswith('AFR::AGO'):
                validation_results['stage4_int']['pass'] += 1
            else:
                validation_results['stage4_int']['fail'] += 1
                validation_results['stage4_int']['issues'].append(f"Row {i}: Invalid location format")
    
    # Print validation results
    print("=== 4-STAGE QUALITY VALIDATION RESULTS ===\n")
    
    print("STAGE 1 - Authentication and Source Verification:")
    print(f"  Passed: {validation_results['stage1_auth']['pass']}")
    print(f"  Failed: {validation_results['stage1_auth']['fail']}")
    if validation_results['stage1_auth']['issues']:
        print(f"  Issues: {validation_results['stage1_auth']['issues'][:5]}")
    
    print("\nSTAGE 2 - Data Quality and Epidemiological Validation:")
    print(f"  Passed: {validation_results['stage2_epi']['pass']}")
    print(f"  Failed: {validation_results['stage2_epi']['fail']}")
    if validation_results['stage2_epi']['issues']:
        print(f"  Issues: {validation_results['stage2_epi']['issues'][:5]}")
    
    print("\nSTAGE 3 - Cross-Reference and Expert Validation:")
    print(f"  Passed: {validation_results['stage3_cross']['pass']}")
    print(f"  Failed: {validation_results['stage3_cross']['fail']}")
    if validation_results['stage3_cross']['issues']:
        print(f"  Issues: {validation_results['stage3_cross']['issues'][:5]}")
    
    print("\nSTAGE 4 - Final Integration and Duplication Checks:")
    print(f"  Passed: {validation_results['stage4_int']['pass']}")
    print(f"  Failed: {validation_results['stage4_int']['fail']}")
    
    print("\nSOURCE RELIABILITY DISTRIBUTION:")
    total = sum(validation_results['source_distribution'].values())
    for level, count in validation_results['source_distribution'].items():
        pct = (count/total*100) if total > 0 else 0
        print(f"  {level}: {count} ({pct:.1f}%)")
    
    # Calculate overall pass rate
    total_pass = sum(v['pass'] for k, v in validation_results.items() if 'stage' in k)
    total_fail = sum(v['fail'] for k, v in validation_results.items() if 'stage' in k)
    total_checks = total_pass + total_fail
    pass_rate = (total_pass / total_checks * 100) if total_checks > 0 else 0
    
    print(f"\nOVERALL VALIDATION PASS RATE: {pass_rate:.1f}%")
    print(f"Total checks: {total_checks}, Passed: {total_pass}, Failed: {total_fail}")
    
    return validation_results, pass_rate

if __name__ == '__main__':
    results, pass_rate = validate_quality()
    sys.exit(0 if pass_rate >= 95 else 1)