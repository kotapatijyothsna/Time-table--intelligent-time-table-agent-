-- =====================================================================
-- SMART CAMPUS - AIML DEPARTMENT TIMETABLE & SCHEDULING DATABASE SCHEMA
-- Target Engine: MySQL 8.4 LTS
-- Character Set: utf8mb4 / Collation: utf8mb4_unicode_ci
-- =====================================================================

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS import_batches;
DROP TABLE IF EXISTS resource_blocks;
DROP TABLE IF EXISTS schedule_exceptions;
DROP TABLE IF EXISTS timetable_entries;
DROP TABLE IF EXISTS timetable_versions;
DROP TABLE IF EXISTS resources;
DROP TABLE IF EXISTS subjects;
DROP TABLE IF EXISTS faculty;
DROP TABLE IF EXISTS academic_sections;
DROP TABLE IF EXISTS academic_terms;
DROP TABLE IF EXISTS departments;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. Department Master
CREATE TABLE departments (
    id CHAR(36) PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Academic Terms
CREATE TABLE academic_terms (
    id CHAR(36) PRIMARY KEY,
    department_id CHAR(36) NOT NULL,
    academic_year VARCHAR(50) NOT NULL,
    semester SMALLINT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_terms_dept FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT,
    CONSTRAINT chk_term_dates CHECK (end_date >= start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Academic Sections (24 AIML Sections)
CREATE TABLE academic_sections (
    id CHAR(36) PRIMARY KEY,
    department_id CHAR(36) NOT NULL,
    year_level SMALLINT NOT NULL,
    section_code VARCHAR(10) NOT NULL,
    full_name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sections_dept FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT,
    CONSTRAINT uq_dept_section UNIQUE (department_id, year_level, section_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Faculty Master
CREATE TABLE faculty (
    id CHAR(36) PRIMARY KEY,
    department_id CHAR(36) NOT NULL,
    faculty_code VARCHAR(50) NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    designation VARCHAR(50) NULL,
    email VARCHAR(120) NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_faculty_dept FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT,
    INDEX idx_faculty_name (full_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Subject Master
CREATE TABLE subjects (
    id CHAR(36) PRIMARY KEY,
    department_id CHAR(36) NOT NULL,
    code VARCHAR(30) NULL,
    name VARCHAR(200) NOT NULL,
    course_type VARCHAR(30) NOT NULL DEFAULT 'CORE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_subjects_dept FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT,
    INDEX idx_subject_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Resource Master (Classrooms & Labs)
CREATE TABLE resources (
    id CHAR(36) PRIMARY KEY,
    department_id CHAR(36) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    resource_type ENUM('CLASSROOM', 'LABORATORY', 'SEMINAR_HALL', 'LIBRARY_SLOT') NOT NULL,
    capacity INT NULL,
    is_shared BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_resources_dept FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT,
    CONSTRAINT chk_resource_capacity CHECK (capacity IS NULL OR capacity > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Timetable Versions
CREATE TABLE timetable_versions (
    id CHAR(36) PRIMARY KEY,
    term_id CHAR(36) NOT NULL,
    version_number SMALLINT NOT NULL,
    status ENUM('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'ARCHIVED') NOT NULL DEFAULT 'DRAFT',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    change_summary TEXT NULL,
    created_by CHAR(36) NOT NULL,
    approved_by CHAR(36) NULL,
    approved_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_version_term FOREIGN KEY (term_id) REFERENCES academic_terms(id) ON DELETE RESTRICT,
    CONSTRAINT uq_term_version UNIQUE (term_id, version_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Timetable Entries
CREATE TABLE timetable_entries (
    id CHAR(36) PRIMARY KEY,
    timetable_version_id CHAR(36) NOT NULL,
    section_id CHAR(36) NOT NULL,
    subject_id CHAR(36) NOT NULL,
    faculty_id CHAR(36) NULL,
    resource_id CHAR(36) NULL,
    day_of_week SMALLINT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    session_type ENUM('THEORY', 'TUTORIAL', 'PRACTICAL', 'COUNSELLING', 'LIBRARY', 'SELF_LEARNING') NOT NULL,
    source_sheet VARCHAR(50) NOT NULL,
    source_row INT NOT NULL,
    source_cell VARCHAR(20) NOT NULL,
    original_text TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_entry_version FOREIGN KEY (timetable_version_id) REFERENCES timetable_versions(id) ON DELETE CASCADE,
    CONSTRAINT fk_entry_section FOREIGN KEY (section_id) REFERENCES academic_sections(id) ON DELETE RESTRICT,
    CONSTRAINT fk_entry_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE RESTRICT,
    CONSTRAINT fk_entry_faculty FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE SET NULL,
    CONSTRAINT fk_entry_resource FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE SET NULL,
    CONSTRAINT chk_time_range CHECK (end_time > start_time),
    CONSTRAINT chk_day_range CHECK (day_of_week BETWEEN 0 AND 6),
    INDEX idx_lookup_slot (timetable_version_id, day_of_week, start_time, end_time),
    INDEX idx_faculty_slot (faculty_id, day_of_week, start_time, end_time),
    INDEX idx_resource_slot (resource_id, day_of_week, start_time, end_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Schedule Exceptions
CREATE TABLE schedule_exceptions (
    id CHAR(36) PRIMARY KEY,
    timetable_entry_id CHAR(36) NOT NULL,
    exception_date DATE NOT NULL,
    exception_type ENUM('CANCEL', 'RESCHEDULE', 'SUBSTITUTE', 'RESOURCE_CHANGE') NOT NULL,
    replacement_faculty_id CHAR(36) NULL,
    replacement_resource_id CHAR(36) NULL,
    new_start_time TIME NULL,
    new_end_time TIME NULL,
    reason VARCHAR(255) NOT NULL,
    created_by CHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_exc_entry FOREIGN KEY (timetable_entry_id) REFERENCES timetable_entries(id) ON DELETE CASCADE,
    CONSTRAINT fk_exc_faculty FOREIGN KEY (replacement_faculty_id) REFERENCES faculty(id) ON DELETE SET NULL,
    CONSTRAINT fk_exc_resource FOREIGN KEY (replacement_resource_id) REFERENCES resources(id) ON DELETE SET NULL,
    INDEX idx_exception_date (exception_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. Resource Maintenance Blocks
CREATE TABLE resource_blocks (
    id CHAR(36) PRIMARY KEY,
    resource_id CHAR(36) NOT NULL,
    start_datetime DATETIME NOT NULL,
    end_datetime DATETIME NOT NULL,
    reason VARCHAR(255) NOT NULL,
    block_type ENUM('MAINTENANCE', 'EXAMINATION', 'EVENT', 'OFFLINE') NOT NULL,
    created_by CHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_block_resource FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    CONSTRAINT chk_block_range CHECK (end_datetime > start_datetime),
    INDEX idx_block_interval (resource_id, start_datetime, end_datetime)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. Import Batches
CREATE TABLE import_batches (
    id CHAR(36) PRIMARY KEY,
    source_filename VARCHAR(255) NOT NULL,
    uploaded_by CHAR(36) NOT NULL,
    status ENUM('PENDING', 'PARSED', 'VALIDATING', 'CONFLICTS_FOUND', 'APPROVED', 'FAILED') NOT NULL,
    total_records INT DEFAULT 0,
    valid_records INT DEFAULT 0,
    critical_errors INT DEFAULT 0,
    warnings INT DEFAULT 0,
    error_summary JSON NULL,
    imported_version_id CHAR(36) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_import_version FOREIGN KEY (imported_version_id) REFERENCES timetable_versions(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 12. Audit Logs
CREATE TABLE audit_logs (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NULL,
    action VARCHAR(50) NOT NULL,
    entity_name VARCHAR(100) NOT NULL,
    entity_id CHAR(36) NOT NULL,
    changes JSON NULL,
    ip_address VARCHAR(45) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_entity (entity_name, entity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
