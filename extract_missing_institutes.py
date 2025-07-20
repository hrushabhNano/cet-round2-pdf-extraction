import pandas as pd
import re
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract_institutes.log'),
        logging.StreamHandler()
    ]
)

def extract_institutes_from_text(text_file_path):
    """Extract all unique institute codes and names from the text file."""
    institutes = {}
    institute_pattern = re.compile(r"^(\d{5}) - (.+)$")
    
    try:
        with open(text_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            logging.info(f"Reading {len(lines)} lines from {text_file_path}")
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                match = institute_pattern.match(line)
                
                if match:
                    institute_code = match.group(1)
                    institute_name = match.group(2)
                    
                    # Remove leading zeros from institute code for consistency with CSV
                    institute_code_clean = institute_code.lstrip('0')
                    
                    # Store the institute (only if not already present to avoid duplicates)
                    if institute_code_clean not in institutes:
                        institutes[institute_code_clean] = institute_name
                        logging.debug(f"Line {line_num}: Found institute {institute_code_clean} - {institute_name}")
                    
        logging.info(f"Extracted {len(institutes)} unique institutes from text file")
        return institutes
        
    except FileNotFoundError:
        logging.error(f"Text file '{text_file_path}' not found")
        return {}
    except Exception as e:
        logging.error(f"Error reading text file: {str(e)}")
        return {}

def load_existing_csv(csv_file_path):
    """Load existing institute mapping CSV."""
    try:
        df = pd.read_csv(csv_file_path)
        logging.info(f"Loaded {len(df)} existing institutes from CSV")
        
        # Convert Institute Code to string and remove any leading zeros for consistency
        df['Institute Code'] = df['Institute Code'].astype(str).str.lstrip('0')
        
        # Create a set of existing institute codes for quick lookup
        existing_codes = set(df['Institute Code'].tolist())
        
        return df, existing_codes
        
    except FileNotFoundError:
        logging.error(f"CSV file '{csv_file_path}' not found")
        return pd.DataFrame(columns=['Institute Code', 'Institute Name']), set()
    except Exception as e:
        logging.error(f"Error reading CSV file: {str(e)}")
        return pd.DataFrame(columns=['Institute Code', 'Institute Name']), set()

def find_missing_institutes(extracted_institutes, existing_codes):
    """Find institutes that are missing from the CSV."""
    missing_institutes = {}
    
    for code, name in extracted_institutes.items():
        if code not in existing_codes:
            missing_institutes[code] = name
    
    logging.info(f"Found {len(missing_institutes)} missing institutes")
    return missing_institutes

def update_csv_file(df, missing_institutes, csv_file_path):
    """Update the CSV file with missing institutes."""
    if not missing_institutes:
        logging.info("No missing institutes to add")
        return
    
    # Create new rows for missing institutes
    new_rows = []
    for code, name in missing_institutes.items():
        new_rows.append({
            'Institute Code': code,
            'Institute Name': name
        })
    
    # Create DataFrame from new rows
    new_df = pd.DataFrame(new_rows)
    
    # Combine existing and new data
    updated_df = pd.concat([df, new_df], ignore_index=True)
    
    # Sort by Institute Code (as integer for proper sorting)
    updated_df['Institute Code'] = updated_df['Institute Code'].astype(str)
    updated_df = updated_df.sort_values('Institute Code', key=lambda x: x.astype(int))
    
    # Save updated CSV
    try:
        # Create backup of original file
        backup_file = csv_file_path.replace('.csv', '_backup.csv')
        df.to_csv(backup_file, index=False)
        logging.info(f"Created backup: {backup_file}")
        
        # Save updated file
        updated_df.to_csv(csv_file_path, index=False)
        logging.info(f"Updated CSV saved with {len(new_rows)} new institutes")
        
        # Print summary of what was added
        print(f"\n{'='*60}")
        print(f"SUMMARY: Added {len(new_rows)} missing institutes")
        print(f"{'='*60}")
        for code, name in missing_institutes.items():
            print(f"{code:>6} - {name}")
        print(f"{'='*60}")
        
    except Exception as e:
        logging.error(f"Error saving updated CSV: {str(e)}")

def main():
    """Main function to orchestrate the institute extraction and CSV update."""
    print("Institute Code Extraction and CSV Update Tool")
    print("=" * 50)
    
    # File paths - Updated to use the uncropped file
    text_file = "documents/pdf__2024ENGG_CAP2_CutOff.txt"
    csv_file = "documents/institute_code_names_mapping_r2.csv"
    
    # Step 1: Extract institutes from text file
    print("Step 1: Extracting institutes from uncropped text file...")
    extracted_institutes = extract_institutes_from_text(text_file)
    
    if not extracted_institutes:
        print("No institutes found in text file. Exiting.")
        return
    
    print(f"Found {len(extracted_institutes)} unique institutes in text file")
    
    # Step 2: Load existing CSV
    print("\nStep 2: Loading existing CSV mapping...")
    existing_df, existing_codes = load_existing_csv(csv_file)
    print(f"Loaded {len(existing_codes)} existing institutes from CSV")
    
    # Step 3: Find missing institutes
    print("\nStep 3: Identifying missing institutes...")
    missing_institutes = find_missing_institutes(extracted_institutes, existing_codes)
    
    if not missing_institutes:
        print("✅ All institutes from text file are already in the CSV mapping!")
        return
    
    print(f"Found {len(missing_institutes)} missing institutes")
    
    # Step 4: Update CSV file
    print("\nStep 4: Updating CSV file...")
    update_csv_file(existing_df, missing_institutes, csv_file)
    
    print("\n✅ Process completed successfully!")
    print(f"📝 Check 'extract_institutes.log' for detailed logs")

if __name__ == "__main__":
    main() 