# Smart Campus: Timetable Ingestion & Import Specification

## 1. Overview
The import system transforms raw Excel workbooks into validated relational structures in MySQL 8.4 LTS without risking active production schedules.

## 2. Pipeline Execution Steps

```
[Upload Excel] 
   --> [Create ImportBatch: PENDING]
   --> [Celery Worker: Asynchronous Cell Extraction]
   --> [Entity Filtering: Strictly II, III, IV AIML]
   --> [Normalization & Alias Mapping]
   --> [Conflict Detection Engine: Overlaps & Shared Assets]
   --> [Create TimetableVersion: PENDING_APPROVAL]
   --> [HOD Inspection via UI]
   --> [Atomic Transaction: Deactivate Old Version + Activate New Version]
   --> [Purge Redis Availability Cache]
```

## 3. Strict Extraction Rules
1. **Target Sheets:** Only process sections matching `^(II|III|IV)\s+AIML-([A-L])`, AIML records in `MINORHONORS`, and AIML entries in `LIBRARY SLOTS`.
2. **Sheet Exclusion:** Non-AIML worksheets (`CS`, `DS`, `CSBS`, `IoT`, `BS(DS)`, `MSc(DS)`, `M.Tech(DS)`) must be filtered out immediately at the workbook sheet parsing loop.
3. **Session Type Detection:**
   - Cells containing `(P)` or room codes matching `LAB*` are categorized as `PRACTICAL`.
   - Cells containing `(T)` are categorized as `TUTORIAL`.
   - Cells containing `COUNSELLING` are categorized as `COUNSELLING`.
   - Cells containing `SL` or `SELF LEARNING` are categorized as `SELF_LEARNING`.
   - All other valid course cells default to `THEORY`.
4. **Shared Resource Safety Rule:**
   - Any classroom or laboratory used by non-AIML programs is marked `is_shared = TRUE`.
   - The engine will strictly report `UNSCHEDULED` or `NOT_VERIFIED` for shared resources outside verified AIML periods.
