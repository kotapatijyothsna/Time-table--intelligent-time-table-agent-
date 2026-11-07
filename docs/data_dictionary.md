# Smart Campus: AIML Department Data Dictionary
**Academic Year:** 2026–27 (I Semester)  
**Database Engine:** MySQL 8.4 LTS

---

## 1. Entities & Field Definitions

### `departments`
Stores departmental metadata within VFSTR.
- `id` (`CHAR(36)`, PK): UUID unique identifier.
- `code` (`VARCHAR(10)`, UK): Abbreviated department code (e.g., `'AIML'`).
- `name` (`VARCHAR(150)`): Full department title (`'Artificial Intelligence and Machine Learning'`).

### `academic_terms`
Stores academic semesters.
- `id` (`CHAR(36)`, PK): UUID.
- `department_id` (`CHAR(36)`, FK): Reference to `departments.id`.
- `academic_year` (`VARCHAR(50)`): Academic year range (e.g., `'2026-27'`).
- `semester` (`SMALLINT`): Numerical semester (`1` or `2`).
- `start_date` (`DATE`): Term start date (e.g., `'2026-08-17'`).
- `end_date` (`DATE`): Term end date.
- `is_current` (`BOOLEAN`): Active semester flag.

### `academic_sections`
Stores student section cohorts.
- `id` (`CHAR(36)`, PK): UUID.
- `department_id` (`CHAR(36)`, FK): Reference to `departments.id`.
- `year_level` (`SMALLINT`): `2` (II Year), `3` (III Year), or `4` (IV Year).
- `section_code` (`VARCHAR(10)`): Section character (`'A'`, `'B'`, ... `'L'`).
- `full_name` (`VARCHAR(50)`): Display name (e.g., `'II AIML-A'`).

### `faculty`
Stores teaching and advising staff.
- `id` (`CHAR(36)`, PK): UUID.
- `department_id` (`CHAR(36)`, FK): Reference to `departments.id`.
- `faculty_code` (`VARCHAR(50)`, UK): Optional institutional employee ID.
- `full_name` (`VARCHAR(150)`): Cleaned faculty name (e.g., `'Dr. S. Srikantha Reddy'`).
- `designation` (`VARCHAR(50)`): Title (`'Professor'`, `'Assistant Professor'`).
- `email` (`VARCHAR(120)`, UK): Institutional email address.
- `is_active` (`BOOLEAN`): Active duty status flag.

### `subjects`
Stores course syllabus offerings.
- `id` (`CHAR(36)`, PK): UUID.
- `department_id` (`CHAR(36)`, FK): Reference to `departments.id`.
- `code` (`VARCHAR(30)`): Short course acronym (e.g., `'DS'`, `'DBMS'`, `'SFCDS'`).
- `name` (`VARCHAR(200)`): Full course name (e.g., `'Data Structures'`).
- `course_type` (`VARCHAR(30)`): `'CORE'`, `'ELECTIVE'`, `'MINOR'`, `'HONORS'`.

### `resources`
Stores physical classrooms, laboratories, and halls.
- `id` (`CHAR(36)`, PK): UUID.
- `department_id` (`CHAR(36)`, FK): Reference to `departments.id`.
- `code` (`VARCHAR(50)`, UK): Physical room identifier (e.g., `'619'`, `'604'`, `'AFTF-13'`).
- `name` (`VARCHAR(100)`): Display title (e.g., `'Computer Lab 604'`).
- `resource_type` (`ENUM`): `'CLASSROOM'`, `'LABORATORY'`, `'SEMINAR_HALL'`, `'LIBRARY_SLOT'`.
- `capacity` (`INT`): Physical seating count.
- `is_shared` (`BOOLEAN`): `TRUE` if utilized across multiple campus programmes.

### `timetable_entries`
Stores scheduled sessions.
- `id` (`CHAR(36)`, PK): UUID.
- `timetable_version_id` (`CHAR(36)`, FK): Reference to parent schedule version.
- `section_id` (`CHAR(36)`, FK): Target cohort.
- `subject_id` (`CHAR(36)`, FK): Course taught.
- `faculty_id` (`CHAR(36)`, FK, Nullable): Assigned instructor.
- `resource_id` (`CHAR(36)`, FK, Nullable): Physical room or lab.
- `day_of_week` (`SMALLINT`): `0` (Monday) through `5` (Saturday).
- `start_time` (`TIME`): Session start (e.g., `'08:15:00'`).
- `end_time` (`TIME`): Session end (e.g., `'09:05:00'`).
- `session_type` (`ENUM`): `'THEORY'`, `'TUTORIAL'`, `'PRACTICAL'`, `'COUNSELLING'`, `'LIBRARY'`, `'SELF_LEARNING'`.
- `source_sheet` (`VARCHAR(50)`): Original workbook worksheet.
- `source_cell` (`VARCHAR(20)`): Excel cell reference.
- `original_text` (`TEXT`): Exact verbatim spreadsheet cell text.
