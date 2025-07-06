import pandas as pd
import re
import uuid
import logging
from datetime import datetime

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

# Regex patterns
institute_pattern = re.compile(r"(\d{5}) - (.+), (.+)")
branch_pattern = re.compile(r"(\d{10}) - (.+)")
rank_pattern = re.compile(r"(\d+)\s*\(([\d.]+)\)")
stage_pattern = re.compile(r"^(I|II|III|IV|V|VI|VII|I-Non|Defence|PWD)$")

# Statistics
stats = {
    "institutes_processed": 0,
    "branches_processed": 0,
    "stages_processed": 0,
    "total_rows": 0
}

try:
    # Read the actual data file
    with open("documents/round2_trimmed.txt", "r", encoding='utf-8') as file:
        lines = file.readlines()
        logging.info(f"Read {len(lines)} lines from round2_trimmed.txt")
        extraction_log.append(f"{datetime.now()} - INFO - Read {len(lines)} lines from round2_trimmed.txt\n")

        collecting_categories = False
        i_non_detected = False
        for line_num, line in enumerate(lines, 1):
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
                continue

            if line == "I-Non":
                i_non_detected = True
                logging.debug(f"Line {line_num}: Detected I-Non, waiting for next stage qualifier")
                extraction_log.append(f"{datetime.now()} - DEBUG - Line {line_num}: Detected I-Non, waiting for next stage qualifier\n")
                continue

            # Skip empty lines outside branch blocks
            if not line:
                if collecting_categories:
                    # End of category block
                    collecting_categories = False
                if in_branch_block:
                    if pending_categories and category_index < len(pending_categories):
                        cat = pending_categories[category_index]
                        logging.debug(f"Line {line_num}: Blank line for category index {category_index} ({cat}) in stage {current_stage}")
                        extraction_log.append(f"{datetime.now()} - DEBUG - Line {line_num}: Blank line for category index {category_index} ({cat}) in stage {current_stage}\n")
                        # Create a row with empty rank/percentile for the skipped category
                        row = {
                            "Institute Code": current_institute.get("Institute Code", ""),
                            "Institute Name": current_institute.get("Institute Name", ""),
                            "District": current_institute.get("District", ""),
                            "Branch Code": current_branch.get("Branch Code", ""),
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
                else:
                    logging.debug(f"Line {line_num}: Empty line outside branch block, skipping")
                    extraction_log.append(f"{datetime.now()} - DEBUG - Line {line_num}: Empty line outside branch block, skipping\n")
                continue

            # Parse institute
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
                continue

            # Parse branch
            if branch_pattern.match(line):
                match = branch_pattern.match(line)
                current_branch = {
                    "Branch Code": match.group(1),
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
                continue

            # Parse status
            if line.startswith("Status:"):
                current_status = line.replace("Status:", "").strip()
                logging.info(f"Line {line_num}: Parsed status - {current_status}")
                extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Parsed status - {current_status}\n")
                continue

            # Parse seat description
            if line in ["State Level", "Home University Seats Allotted to Home University Candidates", 
                        "Home University Seats Allotted to Other Than Home University Candidates",
                        "Other Than Home University Seats Allotted to Other Than Home University Candidates"]:
                current_seat_desc = line
                logging.info(f"Line {line_num}: Parsed seat description - {current_seat_desc}")
                extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Parsed seat description - {current_seat_desc}\n")
                continue

            # Detect stage header
            if line == "Stage":
                pending_categories = []
                category_index = 0
                collecting_categories = True
                logging.info(f"Line {line_num}: Detected stage header, will collect categories")
                extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Detected stage header, will collect categories\n")
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
                
                # Store categories for future reuse
                if pending_categories and current_stage not in ["I-Non", "Defence", "VII", "I-Non PWD"]:
                    last_categories = pending_categories.copy()
                
                # Reset category index for new stage
                category_index = 0
                continue

            # Collect categories generically after 'Stage'
            if collecting_categories:
                if not stage_pattern.match(line):
                    pending_categories.append(line)
                    logging.info(f"Line {line_num}: Collected category - {line}")
                    extraction_log.append(f"{datetime.now()} - INFO - Line {line_num}: Collected category - {line}\n")
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
                        "Institute Code": current_institute.get("Institute Code", ""),
                        "Institute Name": current_institute.get("Institute Name", ""),
                        "District": current_institute.get("District", ""),
                        "Branch Code": current_branch.get("Branch Code", ""),
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
                else:
                    logging.error(f"Line {line_num}: Rank found without categories or index out of range - {line}")
                    extraction_log.append(f"{datetime.now()} - ERROR - Line {line_num}: Rank found without categories or index out of range - {line}\n")
                continue

            # Handle buffered rank (rank on one line, score on next)
            if line.isdigit():
                buffered_rank = line
                logging.debug(f"Line {line_num}: Buffered rank - {buffered_rank}")
                extraction_log.append(f"{datetime.now()} - DEBUG - Line {line_num}: Buffered rank - {buffered_rank}\n")
                continue
            if buffered_rank and line.startswith("(") and line.endswith(")"):
                score = line[1:-1]
                if pending_categories and category_index < len(pending_categories):
                    cat = pending_categories[category_index]
                    logging.debug(f"Line {line_num}: Assigning buffered rank to category index {category_index} ({cat}) in stage {current_stage}")
                    extraction_log.append(f"{datetime.now()} - DEBUG - Line {line_num}: Assigning buffered rank to category index {category_index} ({cat}) in stage {current_stage}\n")
                    row = {
                        "Institute Code": current_institute.get("Institute Code", ""),
                        "Institute Name": current_institute.get("Institute Name", ""),
                        "District": current_institute.get("District", ""),
                        "Branch Code": current_branch.get("Branch Code", ""),
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
                else:
                    logging.error(f"Line {line_num}: Rank found without categories or index out of range - {buffered_rank} ({score})")
                    extraction_log.append(f"{datetime.now()} - ERROR - Line {line_num}: Rank found without categories or index out of range - {buffered_rank} ({score})\n")
                buffered_rank = None
                continue

            # Log unhandled lines
            logging.warning(f"Line {line_num}: Unhandled line - {line}")
            extraction_log.append(f"{datetime.now()} - WARNING - Line {line_num}: Unhandled line - {line}\n")

    # Create DataFrame
    df = pd.DataFrame(data)
    logging.info(f"Total rows in DataFrame: {len(df)}")
    extraction_log.append(f"{datetime.now()} - INFO - Total rows in DataFrame: {len(df)}\n")

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

    # Save to Excel
    output_file = "admission_cutoffs_output.xlsx"
    df.to_excel(output_file, index=False)
    logging.info(f"Excel file generated: {output_file}")
    extraction_log.append(f"{datetime.now()} - INFO - Excel file generated: {output_file}\n")

    # Save extraction log
    with open("extraction_log.txt", "w", encoding='utf-8') as log_file:
        log_file.writelines(extraction_log)
    logging.info("Extraction log generated: extraction_log.txt")
    extraction_log.append(f"{datetime.now()} - INFO - Extraction log generated: extraction_log.txt\n")

except FileNotFoundError:
    logging.error("Data file 'round2_trimmed.txt' not found. Please ensure the file exists in the same directory as the script.")
    extraction_log.append(f"{datetime.now()} - ERROR - Data file 'round2_trimmed.txt' not found.\n")
except ValueError as ve:
    logging.error(f"Input file error: {str(ve)}")
    extraction_log.append(f"{datetime.now()} - ERROR - Input file error: {str(ve)}\n")
except Exception as e:
    logging.error(f"An error occurred: {str(e)}")
    extraction_log.append(f"{datetime.now()} - ERROR - An error occurred: {str(e)}\n")

# Ensure extraction log is saved even if an exception occurs
with open("extraction_log.txt", "w", encoding='utf-8') as log_file:
    log_file.writelines(extraction_log)