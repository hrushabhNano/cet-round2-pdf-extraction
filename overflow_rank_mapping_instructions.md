
# 📄 Instructions for Overflow Rank Detection and Mapping Logic

## 📌 Issue Summary:
- One rank `87619 (67.6869909)` was detected.
- It was incorrectly mapped to the wrong **branch** and **category**.
- Two other ranks are still missing.
- The **stage sequence** is not following the expected order.

---

## ✅ Correct Mapping Logic:

### 1️⃣ Branch Mapping Logic
- The first branch **Civil Engineering (Code: 0110519110)** has:
  - **> 26 categories**
  - **No EWS category**
- So, any overflow ranks in this scenario should get mapped under **Civil Engineering**, **not** the previous page's last branch (in this case **Information Technology**).

---

### 2️⃣ Overflow Detection Logic
- In the overflow block, if there are **3 categories** (example: `TFWS`, `ORPHAN`, `EWS`), then:
  - Each **stage** should have **3 lines/values** — one for each category.
  - After **3 lines**, move to the **next stage** in the sequence.

---

### 3️⃣ Stage Sequence Logic
- For **parent branch Civil Engineering (0110519110)**, the expected stage sequence is:
  - **I**
  - **I-Non Defense**
  - **I-Non PWD**
  - **VII**
- The agent should map values according to this sequence.

---

### 4️⃣ Mapping Flow Example

Given overflow ranks:

```
87619 (67.6869909)     → EWS (Stage-I)
(empty line)           → ORPHAN (Stage-I)
169113 (13.2387508)    → TFWS (Stage-I)
(empty line)
(empty line)
(empty line)
110206 (56.9588351)    → EWS (Stage-VII)
```

- **After 3 entries** (one for each category), move to the **next stage**.
- If there's an empty line — treat it as **no value for that category in that stage**.
- After 3 lines per stage → advance to the next stage in the sequence.

---

## 🚨 Current Issues:
- **Rank `87619 (67.6869909)` was mapped to Information Technology** — should have been Civil Engineering.
- **Only one rank detected, others missing.**
- **Stage sequence misaligned** — not following the `I → I-Non Defense → I-Non PWD → VII` sequence.

---

## 📌 Expected AI Agent Actions:
- Detect all ranks from the overflow block.
- Map them to the **correct parent branch**.
- Follow **category and stage mapping rules**:
  - 3 entries per stage (one per category)
  - Empty line = no value for that category in that stage.
- Correctly sequence stages based on the **parent branch’s sequence definition**.
