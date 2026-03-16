import pandas as pd
import sys
from pathlib import Path


def clean_csv(input_file, output_file=None, remove_duplicates=True, remove_empty=True):
    """
    Clean CSV file by removing empty rows and optionally removing duplicates.
    
    Args:
        input_file (str): Path to input CSV file
        output_file (str): Path to output CSV file. If None, overwrites input file.
        remove_duplicates (bool): Whether to remove duplicate rows
        remove_empty (bool): Whether to remove rows with missing values
    
    Returns:
        pd.DataFrame: Cleaned dataframe
    """
    
    # Read CSV file with encoding detection
    try:
        df = pd.read_csv(input_file)
    except UnicodeDecodeError:
        # Try with Latin-1 encoding if UTF-8 fails
        df = pd.read_csv(input_file, encoding='latin-1')
    
    print(f"Original file: {len(df)} rows")
    
    # Remove rows with all NaN values
    if remove_empty:
        df = df.dropna(how='all')
        print(f"After removing all-empty rows: {len(df)} rows")
    
    # Remove rows with any NaN values (missing values)
    df = df.dropna()
    print(f"After removing rows with missing values: {len(df)} rows")
    
    # Remove duplicate rows
    if remove_duplicates:
        initial_count = len(df)
        df = df.drop_duplicates()
        removed = initial_count - len(df)
        print(f"After removing duplicates: {len(df)} rows (removed {removed} duplicates)")
    
    # Set output file
    if output_file is None:
        output_file = input_file
    
    # Write cleaned data
    df.to_csv(output_file, index=False)
    print(f"\nCleaned file saved to: {output_file}")
    
    return df


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python clean_csv.py <input_file> [output_file]")
        print("\nExample:")
        print("  python clean_csv.py test/seed_data_rss.csv")
        print("  python clean_csv.py test/seed_data_rss.csv test/seed_data_rss_clean.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(input_file).exists():
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)
    
    clean_csv(input_file, output_file)
