import csv
import os

countries = ['AGO', 'BDI', 'BEN', 'BFA', 'BWA', 'CAF', 'CIV', 'CMR', 'COD', 'COG', 'ERI', 'ETH', 'GAB', 'GHA', 'GIN', 'GMB', 'KEN', 'NGA']

print('=== DUAL-REFERENCE INDEXING VERIFICATION ===\n')

compliance_count = 0

for country in countries:
    data_file = f'data/{country}/cholera_data.csv'
    meta_file = f'data/{country}/metadata.csv'
    
    if os.path.exists(data_file) and os.path.exists(meta_file):
        try:
            # Check data file has required headers
            with open(data_file, 'r', encoding='utf-8') as f:
                data_header = f.readline().strip().split(',')
            
            # Check metadata file has required headers  
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta_header = f.readline().strip().split(',')
            
            # Verify headers
            data_has_index = 'Index' in data_header
            data_has_source_index = 'source_index' in data_header
            meta_has_index = 'Index' in meta_header
            
            issues = []
            if not data_has_index:
                issues.append('Missing Index column in cholera_data.csv')
            if not data_has_source_index:
                issues.append('Missing source_index column in cholera_data.csv')
            if not meta_has_index:
                issues.append('Missing Index column in metadata.csv')
            if len(data_header) != 13:
                issues.append(f'cholera_data.csv has {len(data_header)} columns, need 13')
            if len(meta_header) != 14:
                issues.append(f'metadata.csv has {len(meta_header)} columns, need 14')
            
            if issues:
                print(f'❌ {country}: {" | ".join(issues)}')
            else:
                print(f'✅ {country}: All headers correct (data: {len(data_header)} cols, meta: {len(meta_header)} cols)')
                compliance_count += 1
                
        except Exception as e:
            print(f'❌ {country}: Error reading files - {str(e)}')
    else:
        print(f'❌ {country}: Missing files')

print(f'\n=== SUMMARY ===')
print(f'Format compliance: {compliance_count}/{len(countries)} countries ({compliance_count/len(countries)*100:.1f}%)')
print(f'CLAUDE.md standards: {"✅ FULLY COMPLIANT" if compliance_count == len(countries) else "❌ NEEDS FIXES"}')