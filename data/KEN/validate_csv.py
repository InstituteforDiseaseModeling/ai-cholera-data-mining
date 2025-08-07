import pandas as pd
import numpy as np

# Load the data
try:
    df = pd.read_csv('cholera_data_ai.csv')
    meta = pd.read_csv('metadata_ai.csv')
    
    print('=== CHOLERA DATA VALIDATION ===')
    print(f'Shape: {df.shape}')
    print(f'Columns: {list(df.columns)}')
    
    # Check for required columns
    required_cols = ['Index', 'Location', 'TL', 'TR', 'deaths', 'sCh', 'cCh', 'CFR', 
                     'reporting_date', 'source_index', 'source', 'confidence_weight', 
                     'processing_notes', 'source_database']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f'ERROR: Missing columns: {missing_cols}')
    else:
        print('✓ All required columns present')
    
    # Check numeric columns for invalid values
    numeric_cols = ['deaths', 'sCh', 'cCh', 'CFR', 'confidence_weight']
    for col in numeric_cols:
        if col in df.columns:
            # Check for NaN, None, 'nan' strings
            invalid = df[col].apply(lambda x: str(x).lower() in ['nan', 'none'] if pd.notna(x) else False)
            if invalid.any():
                print(f'WARNING: {col} has invalid string values: {df[col][invalid].unique()}')
    
    # Check date formats
    date_cols = ['TL', 'TR', 'reporting_date']
    for col in date_cols:
        try:
            pd.to_datetime(df[col])
            print(f'✓ {col} dates valid')
        except:
            print(f'ERROR: Invalid dates in {col}')
    
    # Check Index column
    if df['Index'].dtype != 'int64':
        print(f'ERROR: Index column is not integer type: {df["Index"].dtype}')
    else:
        print('✓ Index column is integer')
    
    # Check source_index references
    invalid_refs = ~df['source_index'].isin(meta['Index'])
    if invalid_refs.any():
        print(f'ERROR: {invalid_refs.sum()} rows have invalid source_index references')
    else:
        print('✓ All source_index references valid')
    
    # Check Location format
    invalid_locs = ~df['Location'].str.startswith('AFR::')
    if invalid_locs.any():
        print(f'ERROR: {invalid_locs.sum()} rows have invalid Location format')
    else:
        print('✓ All Locations start with AFR::')
    
    # Check for sequential Index
    expected_index = list(range(1, len(df) + 1))
    if list(df['Index']) != expected_index:
        print(f'ERROR: Index column not sequential')
    else:
        print('✓ Index column is sequential')
        
    print()
    print('=== METADATA VALIDATION ===')
    print(f'Shape: {meta.shape}')
    print(f'Columns: {list(meta.columns)}')
    
    # Check Index column in metadata
    if 'Index' not in meta.columns:
        print('ERROR: Missing Index column in metadata')
    elif meta['Index'].dtype != 'int64':
        print(f'ERROR: Index column is not integer: {meta["Index"].dtype}')
    else:
        print('✓ Metadata Index column is integer')
    
    # Check for sequential Index in metadata
    expected_meta_index = list(range(1, len(meta) + 1))
    if list(meta['Index']) != expected_meta_index:
        print(f'ERROR: Metadata Index column not sequential')
    else:
        print('✓ Metadata Index column is sequential')
        
except Exception as e:
    print(f'ERROR loading files: {e}')