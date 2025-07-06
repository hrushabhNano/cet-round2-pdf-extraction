
# 📖 AI Agent Instructions for PDF Text Extraction and Excel Conversion

## 📌 Background
You will receive a text file converted from a PDF/Word document containing engineering college admission cutoffs for different institutes, branches, seat categories, and stages. The format is inconsistent and has mixed text + tables. The goal is to parse this text according to a well-defined pattern and produce a structured Excel sheet.

---

## 📌 Expected Excel Columns
| Sr No | Institute Code | Institute Name | District | Branch Code | Branch Name | Institute Status | Seat Description | Stage | Seat Category | Rank | Percentile |
|:------|:----------------|:----------------|:------------|:--------------|:----------------|:--------------------|:----------------|:--------|:----------------|:------|:--------------|

---

## 📌 Extraction Logic

### 1️⃣ Process the file **line-by-line from top to bottom**.

---

### 2️⃣ Identify the **Institute Information**
- **Pattern**: `<5-digit code> - <Institute Name>, <District>`
  - `Institute Code`: 5 digits.
  - `Institute Name`: String between hyphen and comma (or till end of line if no comma).
  - `District`: If present, comes after the comma and space.

**Example:**
```
01002 - Government College of Engineering, Amravati
```

---

### 3️⃣ Identify the **Branch Information**
- **Pattern**: `<10-digit code> - <Branch Name>`
  - `Branch Code`: 10 digits.
  - `Branch Name`: Remainder after hyphen.

**Example:**
```
0100219110 - Civil Engineering
```

---

### 4️⃣ Capture **Institute Status**
- **Line Format**: e.g., `Government Autonomous`
  - Add this to the `Institute Status` column.

---

### 5️⃣ Capture **Seat Description**
- **Line Format**: e.g., `Home University Seats Allotted to Home University Candidates`
  - Add this to the `Seat Description` column.

---

### 6️⃣ Capture **Stage Indicator**
- Detect line containing the word `Stage` or Roman numeral (e.g. `I`, `II`, `VI`, `VII`, `I-Non PWD`) indicating the start of a new stage.
- Capture and assign this stage name to `Stage` column for all upcoming category entries.

---

### 7️⃣ Capture **Seat Categories**
- Lines immediately following the `Stage` indicator line till the first empty line are considered **Seat Categories**.

**Example:**
```
GOPENS
GSCS
GOBCS
GSEBCS
...
```

---

### 8️⃣ Capture **Rank & Percentile Pairs**
- **Pattern**: `<rank> (<percentile>)`
- Sequentially assign these values to each category captured for the current stage.
- **Blank lines** in between indicate missing data for that position.

**Example:**
```
28591 (90.4057549)
(blank line)
45021 (84.5242070)
```
- First value → GOPENS
- Blank line → GSCS (skip for this stage)
- Next value → GOBCS

**Important:**
- If a new stage indicator appears, remaining categories with skipped positions from the last stage continue from here.
- **Outside a branch**, blank lines can appear. Implement a state-check mechanism to ignore empty lines when not inside an active branch block.

---

## 📌 Edge Cases & Validation Rules

- **Missing Districts**: If comma is not found in institute line, district is null.
- **Empty Rank Lines**: Track skipped positions carefully.
- **Multiple Stages for One Branch**: Category order remains consistent.
- **Unexpected Line Patterns**: Log unknown line patterns for manual review.
- **End of File**: Cleanly flush and finalize open data blocks.

---

## 📌 Test Cases (Recommend AI run these)

**Case 1:** Full block with all stages, no missing values  
**Case 2:** Block missing district  
**Case 3:** Block with missing rank lines inside a stage  
**Case 4:** Block with multiple stages for one branch  
**Case 5:** Unexpected line after branch line  
**Case 6:** End of file without final empty line  

---

## 📌 Logging Recommendations

Implement structured logging throughout:
- **INFO**: When parsing an institute, branch, or stage  
- **WARNING**: When unexpected line patterns or empty lines outside a branch block appear  
- **ERROR**: If any parsing assumption fails (e.g., rank without a current category list)  
- **DEBUG**: For detailed mapping of category → rank/percentile per stage  

Write logs to a file for post-run diagnostics.

---

## 📌 Additional Instruction  
At the end of parsing, produce a summary log:
- Total institutes processed
- Total branches processed
- Total stages processed
- Number of skipped/missing values per category  

---

## 📌 Follow-up Python Script

You are also required to write a Python script that:
- Accepts the parsed text file
- Applies the above extraction logic
- Generates a well-formatted Excel (.xlsx) file with the expected columns

Use:
- `openpyxl` or `pandas` for Excel generation
- `logging` module for logging
- Regular expressions (`re`) for pattern matching

---

## 📌 Deliverables

- Final Excel file  
- Log file with structured log entries  
- Python script (.py)

---

**End of Instructions**
