import pandas as pd
import re
import uuid
import logging
from datetime import datetime
from collections import deque
import os

# Set up logging to console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parsing_debug.log'),
        logging.StreamHandler()
    ]
)

# Initialize lists to store parsed data and extraction log
data = []
extraction_log = []
current_institute = {}
current_branch = {}
current_status = ""
current_seat_desc = ""
current_stage = ""
pending_categories = []
last_categories = []  # Store categories from previous stage
category_index = 0
buffered_rank = None
in_branch_block = False  # Track if we're inside a branch block
skipped_categories = []  # Track categories that were skipped in previous stages
i_non_detected = False  # Track if I-Non was detected

# Input file configuration
input_filename = "documents/2024ENGG_CAP3_CutOff_cropped_1.txt"
input_base_name = os.path.splitext(os.path.basename(input_filename))[0]

# Regex patterns
institute_pattern = re.compile(r"(\d{5}) - (.+), (.+)")
branch_pattern = re.compile(r"(\d{10}) - (.+)")
rank_pattern = re.compile(r"(\d+)\s*\(([\d.]+)\)")
stage_pattern = re.compile(r"^(I|II|III|IV|V|VI|VII|I-Non|Defence|PWD|MH)$")

# Statistics
stats = {
    "institutes_processed": 0,
    "branches_processed": 0,
    "stages_processed": 0,
    "total_rows": 0
}

try:
    # Read the actual data file
    with open(input_filename, "r", encoding='utf-8') as file:
        lines = file.readlines()
        logging.info(f"Read {len(lines)} lines from {input_filename}")
        extraction_log.append(f"{datetime.now()} - INFO - Read {len(lines)} lines from {input_filename}\n")

        collecting_categories = False
        i_non_detected = False
        last_incomplete_branch = None
        last_line_type = None  # 'rank', 'category', 'stage', 'branch', 'other'
        overflow_categories = []
        skip_lines = 0
        for line_num, line in enumerate(lines, 1):
            if skip_lines > 0:
                skip_lines -= 1
                continue
            line = line.strip()
            
            logging.debug(f"Line {line_num}: Processing line - {line}")
            extraction_log.append(f"{datetime.now()} - DEBUG - Line {line_num}: Processing line - {line}\n")

            # Generalized I-Non stage handling
            if i_non_detected and line:
                current_stage = f"I-Non {line}"
                stats["stages_processed"] += 1
                i_non_detected = False
                logging.info(f"Line {line_num}: Parsed stage - {current_stage}")
                extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Parsed stage - {current_stage}\n")
                # Reuse categories from previous stage for I-Non X
                if not pending_categories and last_categories:
                    pending_categories = last_categories.copy()
                    logging.info(f"Line {line_num}: Reusing {len(pending_categories)} categories from previous stage for {current_stage}")
                    extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Reusing {len(pending_categories)} categories from previous stage for {current_stage}\n")
                # Reset category index for new stage
                category_index = 0
                last_line_type = 'stage'
                continue

            if line == "I-Non":
                i_non_detected = True
                logging.debug(f"Line {line_num}: Detected I-Non, waiting for next stage qualifier")
                extraction_log.append(f"{datetime.now()} - DEBUG - Line {line_num}: Detected I-Non, waiting for next stage qualifier\n")
                last_line_type = 'stage'
                continue

            # Skip empty lines outside branch blocks
            if not line:
                if collecting_categories:
                    collecting_categories = False
                if in_branch_block:
                    if pending_categories and category_index < len(pending_categories):
                        cat = pending_categories[category_index]
                        logging.debug(f"Line {line_num}: Blank line for category index {category_index} ({cat}) in stage {current_stage}")
                        extraction_log.append(f"{datetime.now()} - DEBUG - Line {line_num}: Blank line for category index {category_index} ({cat}) in stage {current_stage}\n")
                        row = {
                            "Institute Code": "",  # Will be filled later
                            "Institute Name": "",  # Will be filled later
                            "District": "",  # Will be filled later
                            "Branch Code": str(current_branch.get("Branch Code", "")),  # Ensure string
                            "Branch Name": current_branch.get("Branch Name", ""),
                            "Status": current_status,
                            "Seat Description": current_seat_desc,
                            "Stage": current_stage,
                            "Category": cat,
                            "Rank": "",
                            "Percentile": ""
                        }
                        data.append(row)
                        stats["total_rows"] += 1
                        skipped_categories.append(cat)
                        logging.info(f"Line {line_num}: Added empty row for skipped category {cat} in stage {current_stage}")
                        extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Added empty row for skipped category {cat} in stage {current_stage}\n")
                        category_index += 1
                    else:
                        logging.warning(f"Line {line_num}: Blank line but no category to skip at index {category_index}")
                        extraction_log.append(f"{datetime.now()} - WARNING - Line {line_num}: Blank line but no category to skip at index {category_index}\n")
                last_line_type = 'other'
                continue

            # Parse institute (but don't store institute info yet)
            if institute_pattern.match(line):
                match = institute_pattern.match(line)
                current_institute = {
                    "Institute Code": match.group(1),
                    "Institute Name": match.group(2),
                    "District": match.group(3)
                }
                stats["institutes_processed"] += 1
                logging.info(f"Line {line_num}: Parsed institute - {current_institute}")
                extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Parsed institute - {current_institute}\n")
                # Reset lower-level context
                current_branch = {}
                current_status = ""
                current_seat_desc = ""
                current_stage = ""
                pending_categories = []
                last_categories = []
                category_index = 0
                buffered_rank = None
                in_branch_block = False
                skipped_categories = []
                i_non_detected = False
                collecting_categories = False
                last_line_type = 'branch'
                continue

            # Parse branch
            if branch_pattern.match(line):
                match = branch_pattern.match(line)
                current_branch = {
                    "Branch Code": str(match.group(1)),  # Ensure string to preserve leading zeros
                    "Branch Name": match.group(2)
                }
                stats["branches_processed"] += 1
                in_branch_block = True
                logging.info(f"Line {line_num}: Parsed branch - {current_branch}")
                extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Parsed branch - {current_branch}\n")
                # Reset stage and category context
                current_status = ""
                current_seat_desc = ""
                current_stage = ""
                pending_categories = []
                last_categories = []
                category_index = 0
                buffered_rank = None
                skipped_categories = []
                i_non_detected = False
                collecting_categories = False
                last_line_type = 'branch'
                continue

            # Parse status
            if line.startswith("Status:"):
                current_status = line.replace("Status:", "").strip()
                logging.info(f"Line {line_num}: Parsed status - {current_status}")
                extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Parsed status - {current_status}\n")
                last_line_type = 'other'
                continue

            # Parse seat description
            if line in ["State Level", "Home University Seats Allotted to Home University Candidates", 
                        "Home University Seats Allotted to Other Than Home University Candidates",
                        "Other Than Home University Seats Allotted to Other Than Home University Candidates"]:
                current_seat_desc = line
                logging.info(f"Line {line_num}: Parsed seat description - {current_seat_desc}")
                extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Parsed seat description - {current_seat_desc}\n")
                last_line_type = 'other'
                continue

            # Detect stage header
            if line == "Stage":
                pending_categories = []
                category_index = 0
                collecting_categories = True
                logging.info(f"Line {line_num}: Detected stage header, will collect categories")
                extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Detected stage header, will collect categories\n")
                last_line_type = 'stage'
                continue

            # Parse stage
            if stage_pattern.match(line):
                current_stage = line
                stats["stages_processed"] += 1
                collecting_categories = False
                logging.info(f"Line {line_num}: Parsed stage - {current_stage}")
                extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Parsed stage - {current_stage}\n")
                # Handle special stages that reuse categories from previous stage
                if current_stage in ["I-Non", "Defence", "VII"] and not pending_categories:
                    pending_categories = last_categories.copy()
                    logging.info(f"Line {line_num}: Reusing {len(pending_categories)} categories from previous stage for {current_stage}")
                    extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Reusing {len(pending_categories)} categories from previous stage for {current_stage}\n")
                # Special handling for MH stage - it should only use MI category
                elif current_stage == "MH":
                    pending_categories = ["MI"]
                    logging.info(f"Line {line_num}: Set MI as the only category for MH stage")
                    extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Set MI as the only category for MH stage\n")
                # Store categories for future reuse (excluding MH which has its own specific category MI)
                if pending_categories and current_stage not in ["I-Non", "Defence", "VII", "I-Non PWD", "MH"]:
                    last_categories = pending_categories.copy()
                category_index = 0
                last_line_type = 'stage'
                continue

            # Collect categories generically after 'Stage'
            if collecting_categories:
                if not stage_pattern.match(line):
                    pending_categories.append(line)
                    logging.info(f"Line {line_num}: Collected category - {line}")
                    extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Collected category - {line}\n")
                    last_line_type = 'category'
                    continue
                else:
                    collecting_categories = False



            # Parse rank and score (combined format, e.g., "28591 (90.4057549)")
            rank_match = rank_pattern.match(line)
            if rank_match:
                rank = rank_match.group(1)
                score = rank_match.group(2)
                if pending_categories and category_index < len(pending_categories):
                    cat = pending_categories[category_index]
                    logging.debug(f"Line {line_num}: Assigning rank to category index {category_index} ({cat}) in stage {current_stage}")
                    extraction_log.append(f"{datetime.now()} - DEBUG - Line {line_num}: Assigning rank to category index {category_index} ({cat}) in stage {current_stage}\n")
                    row = {
                        "Institute Code": "",  # Will be filled later
                        "Institute Name": "",  # Will be filled later
                        "District": "",  # Will be filled later
                        "Branch Code": str(current_branch.get("Branch Code", "")),  # Ensure string
                        "Branch Name": current_branch.get("Branch Name", ""),
                        "Status": current_status,
                        "Seat Description": current_seat_desc,
                        "Stage": current_stage,
                        "Category": cat,
                        "Rank": rank,
                        "Percentile": score
                    }
                    data.append(row)
                    stats["total_rows"] += 1
                    logging.info(f"Line {line_num}: Added row with rank - {rank} ({score}) for category {cat}")
                    extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Added row with rank - {rank} ({score}) for category {cat}\n")
                    category_index += 1
                    # Mark this branch as incomplete in case overflowed categories appear next
                    last_incomplete_branch = {
                        "Institute Code": "",  # Will be filled later
                        "Institute Name": "",  # Will be filled later
                        "District": "",  # Will be filled later
                        "Branch Code": str(current_branch.get("Branch Code", "")),  # Ensure string
                        "Branch Name": current_branch.get("Branch Name", ""),
                        "Status": current_status,
                        "Seat Description": current_seat_desc,
                        "Stage": current_stage
                    }
                else:
                    logging.error(f"Line {line_num}: Rank found without categories or index out of range - {line}")
                    extraction_log.append(f"{datetime.now()} - ERROR - Line {line_num}: Rank found without categories or index out of range - {line}\n")
                last_line_type = 'rank'
                continue

            # Handle buffered rank (rank on one line, score on next)
            if line.isdigit():
                buffered_rank = line
                logging.debug(f"Line {line_num}: Buffered rank - {buffered_rank}")
                extraction_log.append(f"{datetime.now()} - DEBUG - Line {line_num}: Buffered rank - {buffered_rank}\n")
                last_line_type = 'rank'
                continue
            if buffered_rank and line.startswith("(") and line.endswith(")"):
                score = line[1:-1]
                if pending_categories and category_index < len(pending_categories):
                    cat = pending_categories[category_index]
                    logging.debug(f"Line {line_num}: Assigning buffered rank to category index {category_index} ({cat}) in stage {current_stage}")
                    extraction_log.append(f"{datetime.now()} - DEBUG - Line {line_num}: Assigning buffered rank to category index {category_index} ({cat}) in stage {current_stage}\n")
                    row = {
                        "Institute Code": "",  # Will be filled later
                        "Institute Name": "",  # Will be filled later
                        "District": "",  # Will be filled later
                        "Branch Code": str(current_branch.get("Branch Code", "")),  # Ensure string
                        "Branch Name": current_branch.get("Branch Name", ""),
                        "Status": current_status,
                        "Seat Description": current_seat_desc,
                        "Stage": current_stage,
                        "Category": cat,
                        "Rank": buffered_rank,
                        "Percentile": score
                    }
                    data.append(row)
                    stats["total_rows"] += 1
                    logging.info(f"Line {line_num}: Added row with rank - {buffered_rank} ({score}) for category {cat}")
                    extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Added row with rank - {buffered_rank} ({score}) for category {cat}\n")
                    category_index += 1
                    # Mark this branch as incomplete in case overflowed categories appear next
                    last_incomplete_branch = {
                        "Institute Code": "",  # Will be filled later
                        "Institute Name": "",  # Will be filled later
                        "District": "",  # Will be filled later
                        "Branch Code": str(current_branch.get("Branch Code", "")),  # Ensure string
                        "Branch Name": current_branch.get("Branch Name", ""),
                        "Status": current_status,
                        "Seat Description": current_seat_desc,
                        "Stage": current_stage
                    }
                else:
                    logging.error(f"Line {line_num}: Rank found without categories or index out of range - {buffered_rank} ({score})")
                    extraction_log.append(f"{datetime.now()} - ERROR - Line {line_num}: Rank found without categories or index out of range - {buffered_rank} ({score})\n")
                buffered_rank = None
                last_line_type = 'rank'
                continue

            # Log unhandled lines
            logging.warning(f"Line {line_num}: Unhandled line - {line}")
            extraction_log.append(f"{datetime.now()} - WARNING - Line {line_num}: Unhandled line - {line}\n")
            last_line_type = 'other'

    # Create DataFrame
    df = pd.DataFrame(data)
    logging.info(f"Total rows in DataFrame before college mapping: {len(df)}")
    extraction_log.append(f"{datetime.now()} - INFO - Total rows in DataFrame before college mapping: {len(df)}\n")

    # Now map college codes and names from CSV
    try:
        # Read the institute mapping CSV
        institute_mapping = pd.read_csv("documents/institute_code_names_mapping_r2.csv")
        logging.info(f"Loaded {len(institute_mapping)} institute mappings from CSV")
        extraction_log.append(f"{datetime.now()} - INFO - Loaded {len(institute_mapping)} institute mappings from CSV\n")
        
        # Create a dictionary for quick lookup
        institute_dict = {}
        for _, row in institute_mapping.iterrows():
            institute_dict[str(row['Institute Code'])] = {
                'Institute Name': row['Institute Name'],
                'District': row['Institute Name'].split(',')[-1].strip() if ',' in row['Institute Name'] else "Unknown District"
            }
        
        # Map college codes and names for each row in the dataframe
        college_mapping_stats = {"mapped": 0, "not_found": 0}
        
        for index, row in df.iterrows():
            branch_code = str(row['Branch Code'])
            if len(branch_code) >= 5:
                # Extract first 5 digits and remove leading 0
                college_code_with_zero = branch_code[:5]
                college_code = college_code_with_zero.lstrip('0')
                
                if college_code in institute_dict:
                    df.at[index, 'Institute Code'] = college_code
                    df.at[index, 'Institute Name'] = institute_dict[college_code]['Institute Name']
                    df.at[index, 'District'] = institute_dict[college_code]['District']
                    college_mapping_stats["mapped"] += 1
                else:
                    df.at[index, 'Institute Code'] = "College Code Not Found"
                    df.at[index, 'Institute Name'] = "College Name Not Found"
                    df.at[index, 'District'] = "District Not Found"
                    college_mapping_stats["not_found"] += 1
                    logging.warning(f"College code {college_code} (from branch {branch_code}) not found in mapping CSV")
                    extraction_log.append(f"{datetime.now()} - WARNING - College code {college_code} (from branch {branch_code}) not found in mapping CSV\n")
            else:
                df.at[index, 'Institute Code'] = "Invalid Branch Code"
                df.at[index, 'Institute Name'] = "Invalid Branch Code"
                df.at[index, 'District'] = "Invalid Branch Code"
                college_mapping_stats["not_found"] += 1
                logging.warning(f"Invalid branch code format: {branch_code}")
                extraction_log.append(f"{datetime.now()} - WARNING - Invalid branch code format: {branch_code}\n")
        
        logging.info(f"College mapping complete: {college_mapping_stats['mapped']} mapped, {college_mapping_stats['not_found']} not found")
        extraction_log.append(f"{datetime.now()} - INFO - College mapping complete: {college_mapping_stats['mapped']} mapped, {college_mapping_stats['not_found']} not found\n")
        
    except FileNotFoundError:
        logging.error("Institute mapping CSV file not found")
        extraction_log.append(f"{datetime.now()} - ERROR - Institute mapping CSV file not found\n")
        # Fill with default values if CSV not found
        df['Institute Code'] = "CSV File Not Found"
        df['Institute Name'] = "CSV File Not Found"
        df['District'] = "CSV File Not Found"
    except Exception as e:
        logging.error(f"Error during college mapping: {str(e)}")
        extraction_log.append(f"{datetime.now()} - ERROR - Error during college mapping: {str(e)}\n")
        # Fill with error values if mapping fails
        df['Institute Code'] = "Mapping Error"
        df['Institute Name'] = "Mapping Error"
        df['District'] = "Mapping Error"

    # Log summary of missing values per category
    if not df.empty:
        for category in df['Category'].unique():
            missing = df[(df['Category'] == category) & (df['Rank'] == "")].shape[0]
            logging.info(f"Category {category}: {missing} missing values")
            extraction_log.append(f"{datetime.now()} - INFO - Category {category}: {missing} missing values\n")
    else:
        logging.warning("DataFrame is empty, no data was parsed")
        extraction_log.append(f"{datetime.now()} - WARNING - DataFrame is empty, no data was parsed\n")

    # Log summary statistics
    logging.info(f"Summary: {stats['institutes_processed']} institutes, {stats['branches_processed']} branches, {stats['stages_processed']} stages, {stats['total_rows']} total rows")
    extraction_log.append(f"{datetime.now()} - INFO - Summary: {stats['institutes_processed']} institutes, {stats['branches_processed']} branches, {stats['stages_processed']} stages, {stats['total_rows']} total rows\n")

    # Ensure branch codes are treated as strings to preserve leading zeros
    # Apply string formatting to restore leading zeros if they were lost
    df['Branch Code'] = df['Branch Code'].astype(str).str.zfill(10)
    
    # Save to Excel with filename based on input file using ExcelWriter to format as text
    output_file = f"{input_base_name}_cutoffs_output.xlsx"
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Cutoffs', index=False)
        
        # Get the workbook and worksheet objects
        from openpyxl.styles import NamedStyle
        workbook = writer.book
        worksheet = writer.sheets['Cutoffs']
        
        # Format the Branch Code column as text to preserve leading zeros
        text_style = NamedStyle(name="text_style", number_format="@")
        for row in range(1, len(df) + 2):  # Starting from row 1 (including header)
            cell = worksheet[f'D{row}']  # Column D is Branch Code
            cell.number_format = "@"  # Text format
    
    logging.info(f"Excel file generated: {output_file}")
    extraction_log.append(f"{datetime.now()} - INFO - Excel file generated: {output_file}\n")

    # Save extraction log with filename based on input file
    log_file_name = f"{input_base_name}_extraction_log.txt"
    with open(log_file_name, "w", encoding='utf-8') as log_file:
        log_file.writelines(extraction_log)
    logging.info(f"Extraction log generated: {log_file_name}")
    extraction_log.append(f"{datetime.now()} - INFO - Extraction log generated: {log_file_name}\n")

except FileNotFoundError:
    logging.error(f"Data file '{input_filename}' not found. Please ensure the file exists in the same directory as the script.")
    extraction_log.append(f"{datetime.now()} - ERROR - Data file '{input_filename}' not found.\n")
except ValueError as ve:
    logging.error(f"Input file error: {str(ve)}")
    extraction_log.append(f"{datetime.now()} - ERROR - Input file error: {str(ve)}\n")
except Exception as e:
    logging.error(f"An error occurred: {str(e)}")
    extraction_log.append(f"{datetime.now()} - ERROR - An error occurred: {str(e)}\n")

# Ensure extraction log is saved even if an exception occurs
log_file_name = f"{input_base_name}_extraction_log.txt"
with open(log_file_name, "w", encoding='utf-8') as log_file:
    log_file.writelines(extraction_log)