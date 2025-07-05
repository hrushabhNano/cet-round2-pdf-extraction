import pandas as pd
import re
import logging
from pathlib import Path

# Setting up logging
logging.basicConfig(filename='extraction_log_corrected_v5.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize lists to store parsed data
data = []
current_institute = {}
current_branch = {}
current_status = ''
current_seat_description = ''
current_categories = []
last_categories = []  # Store categories from previous stage
current_stage = ''
pending_categories = []
temp_rank = None  # Buffer for rank when percentile is on next line

# Regex patterns
institute_pattern = re.compile(r'(\d{5}) - (.+?)(?:,\s*(\w+))?$')
branch_pattern = re.compile(r'(\d{10}) - (.+)')
status_pattern = re.compile(r'Status:\s*(.+)')
seat_description_pattern = re.compile(r'(State Level|Home University Seats Allotted to .+|Other Than Home University Seats Allotted to .+)')
stage_pattern = re.compile(r'^\s*(I|II|III|IV|V|VI|VII|I-Non|Defence|PWD)\s*$')
category_pattern = re.compile(r'^(GOPENS|GSCS|GSTS|GVJS|GNT[1-3]S|GOBCS|GSEBCS|LOPENS|LSCS|LSTS|LVJS|LNT[1-3]S|LOBCS|LSEBCS|PWDOPENS|PWDOBCS|DEFOPENS|DEFOBCS|DEFROBCS|ORPHAN|EWS|GOPENH|GSCH|GSTH|GVJH|GNT[1-3]H|GOBCH|GSEBCH|LOPENH|LSCH|LSTH|LNT[1-3]H|LOBCH|LSEBCH|PWDOPENH|PWDSCH|PWDOBCH|PWDSEBCH|GOPENO|GSCO|GSTO|GVJO|GNT[1-3]O|GOBCO|GSEBCO|LOPENO|LSCO|LOBCO|LSEBCO|DEFRSCS|TFWS)$')
rank_only_pattern = re.compile(r'^\s*(\d+)\s*$')
percentile_only_pattern = re.compile(r'^\s*\((\d+\.\d+)\)\s*$')
rank_pattern = re.compile(r'^\s*(\d+)\s*\((\d+\.\d+)\)\s*$')
stage_header_pattern = re.compile(r'^\s*Stage\s*$')

def clean_value(value):
    """Clean string values by removing extra spaces and quotes."""
    if isinstance(value, str):
        return value.strip().replace('^"', '').replace('"$', '')
    return value

def save_to_excel(data, output_file='admission_cutoffs_corrected_v5.xlsx'):
    """Save parsed data to an Excel file."""
    df = pd.DataFrame(data)
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df.to_excel(output_file, index=False)
    logging.info(f"Excel file generated: {output_file}")

def add_category_rows(categories, institute, branch, status, seat_desc, stage):
    """Add rows for all categories, updating existing rows if they exist."""
    for category in categories:
        # Check if row already exists for this institute, branch, stage, and category
        existing_row_index = next((i for i, d in enumerate(data)
                                  if d['Institute Code'] == institute.get('Institute Code', '')
                                  and d['Branch Code'] == branch.get('Branch Code', '')
                                  and d['Stage'] == stage
                                  and d['Seat Category'] == category), None)
        if existing_row_index is None:
            data.append({
                'Sr No': len(data) + 1,
                'Institute Code': institute.get('Institute Code', ''),
                'Institute Name': institute.get('Institute Name', ''),
                'District': institute.get('District', ''),
                'Branch Code': branch.get('Branch Code', ''),
                'Branch Name': branch.get('Branch Name', ''),
                'Institute Status': status,
                'Seat Description': seat_desc,
                'Stage': stage,
                'Seat Category': category,
                'Rank': '',
                'Percentile': ''
            })
            logging.info(f"Added new row for category {category} in stage {stage} with no rank data")
        else:
            logging.debug(f"Row for category {category} in stage {stage} already exists at index {existing_row_index}")

# Parsing state machine
state = 'INITIAL'
input_file = 'round2_trimmed.txt'
try:
    with open(input_file, 'r', encoding='utf-8') as file:
        category_index = 0  # Track current category position
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            logging.debug(f"Line {line_num}: Processing line - {line}")

            if not line:
                if state == 'RANKS' and current_categories and category_index < len(current_categories):
                    logging.info(f"Line {line_num}: Empty line, skipping rank for category {current_categories[category_index]}")
                    category_index += 1
                else:
                    logging.debug(f"Line {line_num}: Empty line in {state} state, continuing.")
                continue

            # Parse institute
            institute_match = institute_pattern.match(line)
            if institute_match:
                # Process any pending categories for the previous branch/stage
                if current_categories and category_index < len(current_categories):
                    for i in range(category_index, len(current_categories)):
                        add_category_rows([current_categories[i]], current_institute, current_branch, current_status, current_seat_description, current_stage or 'I')
                state = 'INSTITUTE'
                current_institute = {
                    'Institute Code': clean_value(institute_match.group(1)),
                    'Institute Name': clean_value(institute_match.group(2)),
                    'District': clean_value(institute_match.group(3) or '')
                }
                current_branch = {}
                current_status = ''
                current_seat_description = ''
                current_categories = []
                last_categories = []
                pending_categories = []
                current_stage = ''
                temp_rank = None
                category_index = 0
                logging.info(f"Line {line_num}: Parsed institute - {current_institute}")
                continue

            # Parse branch
            branch_match = branch_pattern.match(line)
            if branch_match:
                # Process any pending categories for the previous branch/stage
                if current_categories and category_index < len(current_categories):
                    for i in range(category_index, len(current_categories)):
                        add_category_rows([current_categories[i]], current_institute, current_branch, current_status, current_seat_description, current_stage or 'I')
                state = 'BRANCH'
                current_branch = {
                    'Branch Code': clean_value(branch_match.group(1)),
                    'Branch Name': clean_value(branch_match.group(2))
                }
                current_categories = []
                last_categories = []
                pending_categories = []
                current_stage = ''
                temp_rank = None
                category_index = 0
                logging.info(f"Line {line_num}: Parsed branch - {current_branch}")
                continue

            # Parse status
            status_match = status_pattern.match(line)
            if status_match:
                state = 'STATUS'
                current_status = clean_value(status_match.group(1))
                logging.info(f"Line {line_num}: Parsed status - {current_status}")
                continue

            # Parse seat description
            seat_description_match = seat_description_pattern.match(line)
            if seat_description_match:
                state = 'SEAT_DESCRIPTION'
                current_seat_description = clean_value(seat_description_match.group(1))
                current_categories = []
                pending_categories = []
                current_stage = ''
                temp_rank = None
                category_index = 0
                logging.info(f"Line {line_num}: Parsed seat description - {current_seat_description}")
                continue

            # Parse stage header
            stage_header_match = stage_header_pattern.match(line)
            if stage_header_match:
                state = 'PENDING_CATEGORIES'
                pending_categories = []
                temp_rank = None
                category_index = 0
                logging.info(f"Line {line_num}: Detected stage header, awaiting categories")
                continue

            # Parse stage
            stage_match = stage_pattern.match(line)
            if stage_match:
                # Process any pending categories from previous stage
                if current_categories and category_index < len(current_categories):
                    for i in range(category_index, len(current_categories)):
                        add_category_rows([current_categories[i]], current_institute, current_branch, current_status, current_seat_description, current_stage)
                state = 'CATEGORIES'
                current_stage = clean_value(stage_match.group(1))
                current_categories = pending_categories.copy() if pending_categories else last_categories.copy()
                add_category_rows(current_categories, current_institute, current_branch, current_status, current_seat_description, current_stage)
                pending_categories = []
                category_index = 0
                logging.info(f"Line {line_num}: Parsed stage - {current_stage}, using {len(current_categories)} categories")
                continue

            # Parse category
            category_match = category_pattern.match(line)
            if category_match:
                category = clean_value(category_match.group(1))
                if state == 'PENDING_CATEGORIES':
                    pending_categories.append(category)
                    logging.info(f"Line {line_num}: Stored pending category - {category}")
                elif state in ['CATEGORIES', 'RANKS']:
                    state = 'CATEGORIES'
                    if category not in current_categories:
                        current_categories.append(category)
                        last_categories.append(category)  # Update last_categories
                        add_category_rows([category], current_institute, current_branch, current_status, current_seat_description, current_stage or 'I')
                    logging.info(f"Line {line_num}: Parsed category - {category}")
                else:
                    logging.warning(f"Line {line_num}: Category {category} found in unexpected state {state}")
                continue

            # Parse rank (single line with rank and percentile)
            rank_match = rank_pattern.match(line)
            if rank_match:
                if not current_stage and pending_categories:
                    # Assume stage I if ranks appear after categories without a stage
                    current_stage = 'I'
                    current_categories = pending_categories.copy()
                    add_category_rows(current_categories, current_institute, current_branch, current_status, current_seat_description, current_stage)
                    pending_categories = []
                    category_index = 0
                    logging.info(f"Line {line_num}: Assumed stage I for ranks, using {len(current_categories)} categories")
                
                state = 'RANKS'
                rank = clean_value(rank_match.group(1))
                percentile = clean_value(rank_match.group(2))
                temp_rank = None  # Clear any buffered rank

                if not current_categories or category_index >= len(current_categories):
                    logging.error(f"Line {line_num}: Rank found without categories or index out of range - {rank} ({percentile})")
                    continue

                category = current_categories[category_index]
                # Find and update existing row
                for i, d in enumerate(data):
                    if (d['Institute Code'] == current_institute.get('Institute Code', '') and
                        d['Branch Code'] == current_branch.get('Branch Code', '') and
                        d['Stage'] == current_stage and
                        d['Seat Category'] == category):
                        data[i].update({
                            'Rank': rank,
                            'Percentile': percentile
                        })
                        logging.info(f"Line {line_num}: Updated rank - {rank} ({percentile}) for category {category}")
                        break
                category_index += 1
                continue

            # Parse rank only
            rank_only_match = rank_only_pattern.match(line)
            if rank_only_match:
                state = 'RANKS'
                temp_rank = clean_value(rank_only_match.group(1))
                logging.debug(f"Line {line_num}: Buffered rank - {temp_rank}")
                continue

            # Parse percentile only
            percentile_only_match = percentile_only_pattern.match(line)
            if percentile_only_match:
                state = 'RANKS'
                if temp_rank is None:
                    logging.warning(f"Line {line_num}: Percentile found without preceding rank - {line}")
                    continue

                percentile = clean_value(percentile_only_match.group(1))
                if not current_categories or category_index >= len(current_categories):
                    logging.error(f"Line {line_num}: Rank found without categories or index out of range - {temp_rank} ({percentile})")
                    temp_rank = None
                    continue

                category = current_categories[category_index]
                # Find and update existing row
                for i, d in enumerate(data):
                    if (d['Institute Code'] == current_institute.get('Institute Code', '') and
                        d['Branch Code'] == current_branch.get('Branch Code', '') and
                        d['Stage'] == current_stage and
                        d['Seat Category'] == category):
                        data[i].update({
                            'Rank': temp_rank,
                            'Percentile': percentile
                        })
                        logging.info(f"Line {line_num}: Updated rank - {temp_rank} ({percentile}) for category {category}")
                        break
                temp_rank = None
                category_index += 1
                continue

            # Handle unexpected line patterns
            logging.warning(f"Line {line_num}: Unexpected line pattern - {line} (state: {state})")

    # After file processing, add remaining categories for the last stage/branch
    if pending_categories and not current_stage:
        current_stage = 'I'
        current_categories = pending_categories.copy()
        add_category_rows(current_categories, current_institute, current_branch, current_status, current_seat_description, current_stage)
        pending_categories = []
        logging.info(f"Added {len(current_categories)} pending categories for stage I at file end")
    elif current_categories and category_index < len(current_categories):
        for i in range(category_index, len(current_categories)):
            add_category_rows([current_categories[i]], current_institute, current_branch, current_status, current_seat_description, current_stage or 'I')
            logging.info(f"Added remaining category {current_categories[i]} for stage {current_stage or 'I'}")

except FileNotFoundError:
    logging.error(f"Input file '{input_file}' not found in the current directory.")
    print(f"Error: The file '{input_file}' was not found. Please ensure the file exists in the directory or update the script with the correct file name.")
    exit(1)

# Generate summary log
missing_values = {}
for category in set(d['Seat Category'] for d in data):
    missing_count = sum(1 for d in data if d['Seat Category'] == category and not d['Rank'])
    missing_values[category] = missing_count
logging.info("Summary of missing values per category:")
for category, count in missing_values.items():
    logging.info(f"Category {category}: {count} missing values")
logging.info(f"Total Institutes Processed: {len(set(d['Institute Code'] for d in data))}")
logging.info(f"Total Branches Processed: {len(set(d['Branch Code'] for d in data))}")
logging.info(f"Total Stages Processed: {len(set(d['Stage'] for d in data))}")
logging.info("Parsing and Excel generation completed.")

# Save parsed data to Excel
save_to_excel(data)