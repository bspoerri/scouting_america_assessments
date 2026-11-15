/*******************************************************************************
   scout_assessment Database - Version 1.1.0

   Script: SCOUT_ASSESSMENT_MYSQL.sql
   Description: Creates the relational database structure for scheduling
                and managing Scouting America camp assessments.

   DB Server: MySQL 8.0.16+
   Authors: Brad Spoerri, Sam Whitaker, Chaitanya Patil
   License: TBD
********************************************************************************/


/*******************************************************************************
   Create and activate database

   WARNING: Uncomment DROP DATABASE only when intentionally resetting
   a development database. It permanently deletes existing data.
********************************************************************************/

-- DROP DATABASE IF EXISTS scout_assessment;

CREATE DATABASE IF NOT EXISTS scout_assessment
    CHARACTER SET utf8mb4;

USE scout_assessment;


/*******************************************************************************
   Create Tables
********************************************************************************/

-- Council information

CREATE TABLE council (
    council_num     INT          PRIMARY KEY,
    council_name    VARCHAR(60)  NOT NULL
) ENGINE=InnoDB;


-- Volunteer information

CREATE TABLE volunteer (
    volunteer_id     INT          AUTO_INCREMENT PRIMARY KEY,
    council_num      INT          NOT NULL,
    first_name       VARCHAR(45)  NOT NULL,
    pref_name        VARCHAR(30),
    last_name        VARCHAR(45)  NOT NULL,
    email            VARCHAR(254) NOT NULL UNIQUE,
    phone            VARCHAR(30)  NOT NULL,
    experience_level VARCHAR(15)  NOT NULL,

    FOREIGN KEY (council_num)
        REFERENCES council(council_num),

    CONSTRAINT check_experience_level
        CHECK (experience_level IN ('first-time', 'experienced'))
) ENGINE=InnoDB;


-- Camp information

CREATE TABLE camp (
    camp_id         INT          AUTO_INCREMENT PRIMARY KEY,
    camp_name       VARCHAR(100) NOT NULL,
    council_num     INT          NOT NULL,
    director_name   VARCHAR(60)  NOT NULL,
    director_email  VARCHAR(254) NOT NULL,
    street          VARCHAR(120) NOT NULL,
    city            VARCHAR(60)  NOT NULL,
    state           VARCHAR(50),
    country         VARCHAR(60)  NOT NULL,
    ito_code        VARCHAR(15)  NOT NULL,

    FOREIGN KEY (council_num)
        REFERENCES council(council_num)
) ENGINE=InnoDB;


-- Scouting program types

CREATE TABLE program (
    program_id      INT          AUTO_INCREMENT PRIMARY KEY,
    program_name    VARCHAR(45)  NOT NULL UNIQUE
) ENGINE=InnoDB;


-- Assessment information

CREATE TABLE assessment (
    assessment_id      INT      AUTO_INCREMENT PRIMARY KEY,
    camp_id            INT      NOT NULL,
    program_id         INT      NOT NULL,
    assessment_date    DATE     NOT NULL,
    required_assessors INT      NOT NULL,
    completed_ind      BOOLEAN  NOT NULL DEFAULT FALSE,

    FOREIGN KEY (camp_id)
        REFERENCES camp(camp_id),

    FOREIGN KEY (program_id)
        REFERENCES program(program_id),

    CONSTRAINT check_required_assessors
        CHECK (required_assessors >= 0),

    CONSTRAINT check_completed_ind
        CHECK (completed_ind IN (0, 1))
) ENGINE=InnoDB;


-- Assessment team assignments

CREATE TABLE assessment_assignment (
    assignment_idx  INT      AUTO_INCREMENT PRIMARY KEY,
    assessment_id   INT      NOT NULL,
    volunteer_id    INT      NOT NULL,
    lead_ind        BOOLEAN  NOT NULL DEFAULT FALSE,
    alternate_ind   BOOLEAN  NOT NULL DEFAULT FALSE,
    first_time_ind  BOOLEAN  NOT NULL,

    FOREIGN KEY (assessment_id)
        REFERENCES assessment(assessment_id),

    FOREIGN KEY (volunteer_id)
        REFERENCES volunteer(volunteer_id),

    -- Prevent duplicate assignments
    CONSTRAINT unique_instance
        UNIQUE (assessment_id, volunteer_id),

    -- A lead assessor cannot simultaneously be an alternate
    CONSTRAINT check_lead_status
        CHECK (NOT (lead_ind AND alternate_ind)),

    -- Restrict indicator fields to TRUE/FALSE
    CONSTRAINT check_assignment_flags
        CHECK (
            lead_ind IN (0, 1)
            AND alternate_ind IN (0, 1)
            AND first_time_ind IN (0, 1)
        )
) ENGINE=InnoDB;
