import pandas as pd
import re
import uuid
import logging
from pathlib import Path

# Setting up logging
logging.basicConfig(filename='extraction_log_corrected.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize lists to store parsed data
data = []
current_institute = {}
current_branch = {}
current_status = ''
current_seat_description = ''
current_categories = []
current_stage = ''

# Regex patterns
institute_pattern = re.compile(r'(\d+) - (.+),\s*(\w+)')
branch_pattern = re.compile(r'(\d+) - (.+)')
status_pattern = re.compile(r'Status:\s*(.+)')
seat_description_pattern = re.compile(r'(State Level|Home University Seats Allotted to .+|Other Than Home University Seats Allotted to .+)')
stage_pattern = re.compile(r'^\s*(I|II|III|IV|V|VI|VII|I-Non|Defence|PWD)\s*$')
category_pattern = re.compile(r'^(GOPENS|GSCS|GSTS|GVJS|GNT[1-3]S|GOBCS|GSEBCS|LOPENS|LSCS|LSTS|LVJS|LNT[1-3]S|LOBCS|LSEBCS|PWDOPENS|PWDOBCS|DEFOPENS|DEFOBCS|DEFROBCS|ORPHAN|EWS|GOPENH|GSCH|GSTH|GVJH|GNT[1-3]H|GOBCH|GSEBCH|LOPENH|LSCH|LSTH|LNT[1-3]H|LOBCH|LSEBCH|PWDOPENH|PWDSCH|PWDOBCH|PWDSEBCH|GOPENO|GSCO|GSTO|GVJO|GNT[1-3]O|GOBCO|GSEBCO|LOPENO|LSCO|LOBCO|LSEBCO|DEFRSCS|TFWS)$')
rank_pattern = re.compile(r'^\s*(\d+)\s*\((\d+\.\d+)\)\s*$')

def clean_value(value):
    """Clean string values by removing extra spaces and quotes."""
    if isinstance(value, str):
        return value.strip().replace('^"', '').replace('"$', '')
    return value

def save_to_excel(data, output_file='admission_cutoffs_corrected.xlsx'):
    """Save parsed data to an Excel file."""
    df = pd.DataFrame(data)
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df.to_excel(output_file, index=False)
    logging.info(f"Excel file generated: {output_file}")

# Parsing state machine
state = 'INITIAL'
input_file = 'round2_trimmed (1).txt'  # Updated file name
try:
    with open(input_file, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            logging.debug(f"Line {line_num}: Processing line - {line}")

            if not line:
                if state in ['RANKS', 'CATEGORIES']:
                    logging.debug(f"Line {line_num}: Empty line in {state} state, continuing.")
                else:
                    logging.warning(f"Line {line_num}: Empty line outside active branch block, ignored.")
                continue

            # Parse institute
            institute_match = institute_pattern.match(line)
            if institute_match:
                state = 'INSTITUTE'
                current_institute = {
                    'Institute Code': clean_value(institute_match.group(1)),
                    'Institute Name': clean_value(institute_match.group(2)),
                    'District': clean_value(institute_match.group(3))
                }
                logging.info(f"Line {line_num}: Parsed institute - {current_institute}")
                continue

            # Parse branch
            branch_match = branch_pattern.match(line)
            if branch_match:
                state = 'BRANCH'
                current_branch = {
                    'Branch Code': clean_value(branch_match.group(1)),
                    'Branch Name': clean_value(branch_match.group(2))
                }
                current_categories = []
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
                logging.info(f"Line {line_num}: Parsed seat description - {current_seat_description}")
                continue

            # Parse stage
            stage_match = stage_pattern.match(line)
            if stage_match:
                state = 'CATEGORIES'
                current_stage = clean_value(stage_match.group(1))
                current_categories = []
                logging.info(f"Line {line_num}: Parsed stage - {current_stage}")
                continue

            # Parse category
            category_match = category_pattern.match(line)
            if category_match and state in ['CATEGORIES', 'RANKS']:
                state = 'CATEGORIES'
                current_categories.append(clean_value(category_match.group(1)))
                logging.info(f"Line {line_num}: Parsed category - {category_match.group(1)}")
                continue

            # Parse rank and percentile
            rank_match = rank_pattern.match(line)
            if rank_match and state in ['CATEGORIES', 'RANKS']:
                state = 'RANKS'
                rank = clean_value(rank_match.group(1))
                percentile = clean_value(rank_match.group(2))
                
                # Check if there are categories to associate with the rank
                if not current_categories:
                    logging.error(f"Line {line_num}: Rank found without categories - {rank} ({percentile})")
                    continue

                # Associate rank with the next available category
                if len(current_categories) > len([d for d in data if d['Branch Code'] == current_branch.get('Branch Code', '') and d['Stage'] == current_stage]):
                    category = current_categories[len([d for d in data if d['Branch Code'] == current_branch.get('Branch Code', '') and d['Stage'] == current_stage])]
                    data.append({
                        'Sr No': len(data) + 1,
                        'Institute Code': current_institute.get('Institute Code', ''),
                        'Institute Name': current_institute.get('Institute Name', ''),
                        'District': current_institute.get('District', ''),
                        'Branch Code': current_branch.get('Branch Code', ''),
                        'Branch Name': current_branch.get('Branch Name', ''),
                        'Institute Status': current_status,
                        'Seat Description': current_seat_description,
                        'Stage': current_stage,
                        'Seat Category': category,
                        'Rank': rank,
                        'Percentile': percentile
                    })
                    logging.info(f"Line {line_num}: Parsed rank - {rank} ({percentile}) for category {category}")
                else:
                    logging.warning(f"Line {line_num}: No remaining categories for rank - {rank} ({percentile})")
                continue

            # Handle unexpected line patterns
            logging.warning(f"Line {line_num}: Unexpected line pattern - {line}")

except FileNotFoundError:
    logging.error(f"Input file '{input_file}' not found in the current directory.")
    print(f"Error: The file '{input_file}' was not found. Please ensure the file exists in the directory '/Users/nanostuffstechnoogies/Projects/cet-round2-conversion/' or update the script with the correct file name.")
    exit(1)

# Save parsed data to Excel
save_to_excel(data)
logging.info("Parsing and Excel generation completed.")
logging.info(f"Total Institutes Processed: {len(set(d['Institute Code'] for d in data))}")
logging.info(f"Total Branches Processed: {len(set(d['Branch Code'] for d in data))}")
logging.info(f"Total Stages Processed: {len(set(d['Stage'] for d in data))}")