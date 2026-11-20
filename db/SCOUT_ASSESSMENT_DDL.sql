/*******************************************************************************
   scout_assessment Database - Version 1.4.0

   Script: SCOUT_ASSESSMENT_DDL.sql
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

/*******************************************************************************
   Create database
********************************************************************************/
CREATE DATABASE IF NOT EXISTS scout_assessment
    CHARACTER SET utf8mb4;

/*******************************************************************************
   Activate database
********************************************************************************/
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
    volunteer_id        INT             AUTO_INCREMENT PRIMARY KEY,
    council_num         INT             NOT NULL,
    first_name          VARCHAR(45)     NOT NULL,
    -- same length as first_name so the default always fits; the
    -- default applies only when the column is omitted, not when NULL
    -- is passed explicitly
    pref_name           VARCHAR(45)     NOT NULL DEFAULT (first_name),
    last_name           VARCHAR(45)     NOT NULL,
    email               VARCHAR(254)    NOT NULL UNIQUE,
    phone               VARCHAR(30)     NOT NULL,
    experience_baseline VARCHAR(15)     NOT NULL,
    added_dt            DATE            NOT NULL DEFAULT (CURRENT_DATE()),
    active_ind          BOOLEAN         NOT NULL DEFAULT TRUE, 

    FOREIGN KEY (council_num)
        REFERENCES council(council_num),

    CONSTRAINT check_active_ind
        CHECK (active_ind IN (0, 1)),

    CONSTRAINT check_experience
        CHECK (experience_baseline IN ('EXPERIENCED', 'NEW'))

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
    country         VARCHAR(60)  NOT NULL DEFAULT 'United States',
    ito_code        VARCHAR(15)  NOT NULL,

    FOREIGN KEY (council_num)
        REFERENCES council(council_num),

    CONSTRAINT check_usa
        CHECK (country <> 'United States' OR state IS NOT NULL)

) ENGINE=InnoDB;


-- Scouting program types
CREATE TABLE program (
	program_id		INT				AUTO_INCREMENT	PRIMARY KEY,
	program_name	VARCHAR(45)		NOT NULL,
	target_score	INT				NOT NULL,
	
	CONSTRAINT min_target
        CHECK (target_score > 0)
) ENGINE=InnoDB;


-- Assessment information
CREATE TABLE assessment (
    assessment_id       INT      AUTO_INCREMENT PRIMARY KEY,
    created_dt          DATE     NOT NULL DEFAULT (CURRENT_DATE()),
    camp_id             INT      NOT NULL,
    program_id          INT      NOT NULL,
    assessment_dt       DATE     NOT NULL,
    -- cancelled assessments are deleted, not kept as a status
    status              ENUM('PLANNED','FILLED','COMPLETED')
                                 NOT NULL DEFAULT 'PLANNED',
    assessment_year     SMALLINT AS (YEAR(assessment_dt)) STORED NOT NULL,
    required_assessors  INT      NOT NULL,
    score               INT,

    FOREIGN KEY (camp_id)
        REFERENCES camp(camp_id),

    FOREIGN KEY (program_id)
        REFERENCES program(program_id),

    -- a camp-program combination can only occur once per year
    -- also covers uniqueness on (camp_id, program_id, assessment_dt)
    CONSTRAINT one_per_camp_program_year
    UNIQUE (camp_id, program_id, assessment_year),

    CONSTRAINT check_required_assessors
        CHECK (required_assessors > 0),
    
    CONSTRAINT min_score
        CHECK (score >= 0),

    CONSTRAINT future
        CHECK (assessment_dt > created_dt),

    CONSTRAINT score_when_complete
        CHECK (status <> 'COMPLETED' OR score IS NOT NULL)

) ENGINE=InnoDB;


-- Assessment team assignments
CREATE TABLE assessment_assignment (
    assignment_id  INT  AUTO_INCREMENT PRIMARY KEY,
    volunteer_id   INT  NOT NULL,
    assessment_id  INT  NOT NULL,
    role_code      ENUM('LEAD','ASSESSOR','ALTERNATE') NOT NULL,

    -- volunteer can only appear once per assessment
    CONSTRAINT unique_assignment
        UNIQUE (assessment_id, volunteer_id),
        
    CONSTRAINT fk_assign_volunteer
        FOREIGN KEY (volunteer_id) REFERENCES volunteer(volunteer_id),
        
    CONSTRAINT fk_assign_assessment
        FOREIGN KEY (assessment_id) REFERENCES assessment(assessment_id)
        ON DELETE CASCADE,

    -- at most one lead per assessment
    UNIQUE KEY uq_one_lead
        (assessment_id, (CASE WHEN role_code = 'LEAD' THEN 1 END))
      
) ENGINE=InnoDB;


/*******************************************************************************
   Create Views
********************************************************************************/

-- experienced volunteers: experienced baseline, or served as LEAD or
-- ASSESSOR on a completed assessment (ALTERNATEs do not gain experience)
CREATE VIEW experienced_volunteers AS
	SELECT volunteer_id FROM volunteer
	WHERE experience_baseline = 'EXPERIENCED'
	UNION
	SELECT volunteer_id FROM assessment_assignment aa, assessment a
    WHERE aa.assessment_id = a.assessment_id
    AND a.status = 'COMPLETED'
    AND aa.role_code IN ('LEAD', 'ASSESSOR');


-- first time volunteers
CREATE VIEW first_time_volunteers AS 
	SELECT v.volunteer_id FROM volunteer v
	WHERE v.experience_baseline = 'NEW'
	AND NOT EXISTS (
		SELECT 1 FROM experienced_volunteers ev
		WHERE ev.volunteer_id = v.volunteer_id
	);


-- summary view of all assessments not yet completed (with status),
-- including overdue ones
CREATE VIEW scheduled_assessments AS
	SELECT a.assessment_dt,
	       c.camp_name,
	       p.program_name,
	       a.status,
	       COALESCE(curr.num_assigned, 0) AS num_assigned,
	       a.required_assessors
	FROM assessment a
	JOIN camp c
		ON c.camp_id = a.camp_id
	JOIN program p
		ON p.program_id = a.program_id
	LEFT JOIN (SELECT aa.assessment_id, COUNT(*) AS num_assigned
	           FROM assessment_assignment aa
	           WHERE aa.role_code IN ('LEAD', 'ASSESSOR')
	           GROUP BY aa.assessment_id) AS curr
		ON curr.assessment_id = a.assessment_id
	WHERE a.status <> 'COMPLETED';



-- view of engagement stats for each volunteer
CREATE VIEW volunteer_activity AS
	SELECT v.volunteer_id,
		   v.pref_name,
		   v.last_name,
           v.active_ind,
		   COUNT(CASE WHEN a.status <> 'COMPLETED' THEN 1 END)
			   AS pending,
		   COUNT(CASE WHEN a.status <> 'COMPLETED'
					   AND aa.role_code = 'LEAD' THEN 1 END)
			   AS pending_as_lead,
		   COUNT(CASE WHEN a.status = 'COMPLETED' THEN 1 END)
			   AS completed,
		   COUNT(CASE WHEN a.status = 'COMPLETED'
					   AND aa.role_code = 'LEAD' THEN 1 END)
			   AS completed_as_lead
	FROM volunteer v
	LEFT JOIN assessment_assignment aa
		ON aa.volunteer_id = v.volunteer_id
	LEFT JOIN assessment a
		ON a.assessment_id = aa.assessment_id
	GROUP BY v.volunteer_id, v.pref_name, v.last_name, v.active_ind
	ORDER BY completed DESC, completed_as_lead DESC, v.last_name, v.pref_name;


-- historical completed assessments with lead contact
CREATE VIEW completed_assessment_history AS
	SELECT a.assessment_year,
		   c.camp_name,
		   p.program_name,
		   p.target_score,
		   a.score AS actual_score,
		   v.email AS lead_contact
	FROM assessment a
	JOIN camp c
		ON c.camp_id = a.camp_id
	JOIN program p
		ON p.program_id = a.program_id
	LEFT JOIN assessment_assignment aa
		ON aa.assessment_id = a.assessment_id
		AND aa.role_code = 'LEAD'
	LEFT JOIN volunteer v
		ON v.volunteer_id = aa.volunteer_id
	WHERE a.status = 'COMPLETED'
	ORDER BY a.assessment_year DESC, c.camp_name, p.program_name;


-- overdue evaluation: date has passed but not yet marked COMPLETED
CREATE VIEW overdue_assessments AS
	SELECT a.assessment_id,
		   a.assessment_dt,
		   DATEDIFF(CURRENT_DATE(), a.assessment_dt) AS days_overdue,
		   c.camp_name,
		   p.program_name,
		   (SELECT COUNT(*) FROM assessment_assignment f
			WHERE f.assessment_id = a.assessment_id
			  AND f.role_code IN ('LEAD', 'ASSESSOR')) AS filled_assessors,
		   CONCAT(v.pref_name, ' ', v.last_name) AS lead_name,
		   v.email AS lead_email
	FROM assessment a
	JOIN camp c
		ON c.camp_id = a.camp_id
	JOIN program p
		ON p.program_id = a.program_id
	LEFT JOIN assessment_assignment aa
		ON aa.assessment_id = a.assessment_id
		AND aa.role_code = 'LEAD'
	LEFT JOIN volunteer v
		ON v.volunteer_id = aa.volunteer_id
	WHERE a.status <> 'COMPLETED'
	  AND a.assessment_dt < CURRENT_DATE()
	ORDER BY a.assessment_dt, a.assessment_id;


-- DELIMITER must come before the block comment below: the mysql
-- command-line client only recognizes DELIMITER at the start of a
-- statement, and a /* */ comment counts as the start of one
DELIMITER $$

/*******************************************************************************
   Create Triggers for Advanced Constraints
********************************************************************************/

-- Only active volunteers can be assigned to an assessment.
CREATE TRIGGER volunteer_must_be_active_insert
BEFORE INSERT ON assessment_assignment
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM volunteer v
        WHERE v.volunteer_id = NEW.volunteer_id
          AND v.active_ind = FALSE
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Inactive volunteers cannot be assigned to an assessment';
    END IF;
END$$


-- same rule when an existing assignment is changed (volunteer swapped
-- in, role changed, or moved to another assessment)
CREATE TRIGGER volunteer_must_be_active_update
BEFORE UPDATE ON assessment_assignment
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM volunteer v
        WHERE v.volunteer_id = NEW.volunteer_id
          AND v.active_ind = FALSE
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Inactive volunteers cannot be assigned to an assessment';
    END IF;
END$$

DELIMITER ;


-- A volunteer may only be assigned the LEAD role if they are experienced.
DELIMITER $$

CREATE TRIGGER lead_must_be_experienced_insert
BEFORE INSERT ON assessment_assignment
FOR EACH ROW
BEGIN
    IF NEW.role_code = 'LEAD' AND NOT EXISTS (
        SELECT 1 FROM experienced_volunteers ev
        WHERE ev.volunteer_id = NEW.volunteer_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Only an experienced volunteer can be assigned as LEAD';
    END IF;
END$$


-- same rule when an existing assignment is promoted to LEAD
-- or its volunteer is swapped in
CREATE TRIGGER lead_must_be_experienced_update
BEFORE UPDATE ON assessment_assignment
FOR EACH ROW
BEGIN
    IF NEW.role_code = 'LEAD' AND NOT EXISTS (
        SELECT 1 FROM experienced_volunteers ev
        WHERE ev.volunteer_id = NEW.volunteer_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Only an experienced volunteer can be assigned as LEAD';
    END IF;
END$$

DELIMITER ;


-- There cannot be more than the required number of assessors
-- insert and update triggers
DELIMITER $$

CREATE TRIGGER max_assessors_insert
BEFORE INSERT ON assessment_assignment
FOR EACH ROW
BEGIN
    DECLARE v_required INT;
    DECLARE v_filled   INT;

    IF NEW.role_code IN ('LEAD', 'ASSESSOR') THEN
        -- lock the parent row so two concurrent inserts can't both pass
        SELECT required_assessors INTO v_required
        FROM assessment
        WHERE assessment_id = NEW.assessment_id
        FOR UPDATE;

        SELECT COUNT(*) INTO v_filled
        FROM assessment_assignment
        WHERE assessment_id = NEW.assessment_id
          AND role_code IN ('LEAD', 'ASSESSOR');

        IF v_filled >= v_required THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Assessment is fully staffed; add as ALTERNATE instead';
        END IF;
    END IF;
END$$


-- same cap when an assignment is promoted (e.g. ALTERNATE -> ASSESSOR)
-- or moved to a different assessment
CREATE TRIGGER max_assessors_update
BEFORE UPDATE ON assessment_assignment
FOR EACH ROW
BEGIN
    DECLARE v_required INT;
    DECLARE v_filled   INT;

    IF NEW.role_code IN ('LEAD', 'ASSESSOR') THEN
        -- lock the parent row so concurrent changes can't both pass
        SELECT required_assessors INTO v_required
        FROM assessment
        WHERE assessment_id = NEW.assessment_id
        FOR UPDATE;

        -- exclude the row being updated so LEAD <-> ASSESSOR swaps
        -- and other edits to an already-counted seat still pass
        SELECT COUNT(*) INTO v_filled
        FROM assessment_assignment
        WHERE assessment_id = NEW.assessment_id
          AND role_code IN ('LEAD', 'ASSESSOR')
          AND assignment_id <> OLD.assignment_id;

        IF v_filled >= v_required THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Assessment is fully staffed; cannot promote to LEAD or ASSESSOR';
        END IF;
    END IF;
END$$


-- re-derive assessment status when the number of required assessors
-- changes
CREATE TRIGGER required_not_below_filled
BEFORE UPDATE ON assessment
FOR EACH ROW
BEGIN
    DECLARE v_filled INT;

    SELECT COUNT(*) INTO v_filled
    FROM assessment_assignment
    WHERE assessment_id = NEW.assessment_id
      AND role_code IN ('LEAD', 'ASSESSOR');

    IF NEW.required_assessors < v_filled THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Cannot set required_assessors below the number already assigned';
    END IF;

    -- required count changed: re-derive status (never touch COMPLETED)
    IF NEW.required_assessors <> OLD.required_assessors
       AND NEW.status <> 'COMPLETED' THEN
        SET NEW.status = IF(v_filled = NEW.required_assessors,
                            'FILLED', 'PLANNED');
    END IF;
END$$


-- An assessment cannot be marked COMPLETED unless it has a LEAD.
CREATE TRIGGER complete_requires_lead
BEFORE UPDATE ON assessment
FOR EACH ROW
BEGIN
    IF NEW.status = 'COMPLETED' AND OLD.status <> 'COMPLETED'
       AND NOT EXISTS (
           SELECT 1 FROM assessment_assignment aa
           WHERE aa.assessment_id = NEW.assessment_id
             AND aa.role_code = 'LEAD'
       ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'An assessment cannot be completed without a LEAD';
    END IF;
END$$


-- a new assessment has no team yet, so it cannot start as COMPLETED
-- (closes the insert path around complete_requires_lead)
CREATE TRIGGER no_insert_as_completed
BEFORE INSERT ON assessment
FOR EACH ROW
BEGIN
    IF NEW.status = 'COMPLETED' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'An assessment cannot be created as COMPLETED; assign a LEAD and complete it afterward';
    END IF;
END$$


-- An assessment score cannot exceed the target score of the program
-- being assessed. target_score lives in program, so a CHECK cannot
-- reference it; enforce on insert, on update (score or program
-- changed), and when a program's target is lowered.
CREATE TRIGGER score_within_target_insert
BEFORE INSERT ON assessment
FOR EACH ROW
BEGIN
    IF NEW.score IS NOT NULL AND NEW.score > (
        SELECT p.target_score FROM program p
        WHERE p.program_id = NEW.program_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Assessment score cannot exceed the program target score';
    END IF;
END$$


CREATE TRIGGER score_within_target_update
BEFORE UPDATE ON assessment
FOR EACH ROW
BEGIN
    IF NEW.score IS NOT NULL AND NEW.score > (
        SELECT p.target_score FROM program p
        WHERE p.program_id = NEW.program_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Assessment score cannot exceed the program target score';
    END IF;
END$$


-- a program's target cannot be lowered below a score already recorded
-- against it
CREATE TRIGGER target_not_below_scores
BEFORE UPDATE ON program
FOR EACH ROW
BEGIN
    IF NEW.target_score < OLD.target_score AND EXISTS (
        SELECT 1 FROM assessment a
        WHERE a.program_id = NEW.program_id
          AND a.score > NEW.target_score
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Cannot set target_score below an existing assessment score for this program';
    END IF;
END$$

DELIMITER ;


-- Keep assessment.status in sync with assignments:
-- FILLED  when assigned LEAD/ASSESSOR count = required_assessors
-- PLANNED otherwise
-- COMPLETED assessments are never changed.
DELIMITER $$

CREATE PROCEDURE refresh_assessment_status(IN p_assessment_id INT)
BEGIN
    UPDATE assessment a
    SET a.status = CASE
            WHEN (SELECT COUNT(*) FROM assessment_assignment aa
                  WHERE aa.assessment_id = a.assessment_id
                    AND aa.role_code IN ('LEAD', 'ASSESSOR'))
                 = a.required_assessors
            THEN 'FILLED'
            ELSE 'PLANNED'
        END
    WHERE a.assessment_id = p_assessment_id
      AND a.status <> 'COMPLETED';
END$$

CREATE TRIGGER status_after_assignment_insert
AFTER INSERT ON assessment_assignment
FOR EACH ROW
BEGIN
    CALL refresh_assessment_status(NEW.assessment_id);
END$$

CREATE TRIGGER status_after_assignment_update
AFTER UPDATE ON assessment_assignment
FOR EACH ROW
BEGIN
    CALL refresh_assessment_status(NEW.assessment_id);
    -- assignment moved to a different assessment: refresh the old one too
    IF OLD.assessment_id <> NEW.assessment_id THEN
        CALL refresh_assessment_status(OLD.assessment_id);
    END IF;
END$$

CREATE TRIGGER status_after_assignment_delete
AFTER DELETE ON assessment_assignment
FOR EACH ROW
BEGIN
    CALL refresh_assessment_status(OLD.assessment_id);
END$$

DELIMITER ;


/*******************************************************************************
  Version 1.4.0: lead rotation and same-day assignment conflicts

  Rules:
   - Camp + program identifies a recurring annual assessment.
   - One volunteer may lead at most three CONSECUTIVE years for that pair.
   - All assignment roles (including ALTERNATE) reserve the entire day.
   - Validation covers assigning/promoting a volunteer and rescheduling or
     changing the camp/program of an existing assessment.

  Assumes a freshly created database (run this full DDL before the seed).
  For an existing v1.3 database, use the separate migration file instead.
*******************************************************************************/

CREATE INDEX idx_assessment_assessment_dt ON assessment (assessment_dt);

DELIMITER $$

-- Exclude the assessment currently being changed, then inspect all four
-- possible 4-year windows that include the proposed year. If the other
-- three years in any window already have this same lead, reject the change.
CREATE PROCEDURE assert_lead_rotation(
    IN p_volunteer_id INT,
    IN p_camp_id INT,
    IN p_program_id INT,
    IN p_year INT,
    IN p_excluded_assessment_id INT
)
BEGIN
    IF EXISTS (
        SELECT 1
        FROM (SELECT 0 AS shift_years UNION ALL SELECT 1
              UNION ALL SELECT 2 UNION ALL SELECT 3) AS windows
        WHERE (
            SELECT COUNT(DISTINCT a.assessment_year)
            FROM assessment a
            JOIN assessment_assignment aa
              ON aa.assessment_id = a.assessment_id
            WHERE aa.volunteer_id = p_volunteer_id
              AND aa.role_code = 'LEAD'
              AND a.camp_id = p_camp_id
              AND a.program_id = p_program_id
              AND a.assessment_id <> p_excluded_assessment_id
              AND a.assessment_year BETWEEN p_year - windows.shift_years
                                        AND p_year - windows.shift_years + 3
        ) = 3
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Lead rotation: maximum three consecutive years per camp and program';
    END IF;
END$$

CREATE TRIGGER lead_rotation_assignment_insert
BEFORE INSERT ON assessment_assignment
FOR EACH ROW
BEGIN
    DECLARE v_camp_id INT;
    DECLARE v_program_id INT;
    DECLARE v_year INT;
    IF NEW.role_code = 'LEAD' THEN
        SELECT a.camp_id, a.program_id, a.assessment_year
          INTO v_camp_id, v_program_id, v_year
        FROM assessment a WHERE a.assessment_id = NEW.assessment_id;
        CALL assert_lead_rotation(NEW.volunteer_id, v_camp_id,
                                  v_program_id, v_year, NEW.assessment_id);
    END IF;
END$$

CREATE TRIGGER lead_rotation_assignment_update
BEFORE UPDATE ON assessment_assignment
FOR EACH ROW
BEGIN
    DECLARE v_camp_id INT;
    DECLARE v_program_id INT;
    DECLARE v_year INT;
    IF NEW.role_code = 'LEAD' THEN
        SELECT a.camp_id, a.program_id, a.assessment_year
          INTO v_camp_id, v_program_id, v_year
        FROM assessment a WHERE a.assessment_id = NEW.assessment_id;
        CALL assert_lead_rotation(NEW.volunteer_id, v_camp_id,
                                  v_program_id, v_year, NEW.assessment_id);
    END IF;
END$$

CREATE TRIGGER lead_rotation_assessment_update
BEFORE UPDATE ON assessment
FOR EACH ROW
BEGIN
    DECLARE v_lead_id INT DEFAULT NULL;
    IF NEW.assessment_dt <> OLD.assessment_dt
       OR NEW.camp_id <> OLD.camp_id
       OR NEW.program_id <> OLD.program_id THEN
        SELECT MAX(aa.volunteer_id) INTO v_lead_id
        FROM assessment_assignment aa
        WHERE aa.assessment_id = OLD.assessment_id
          AND aa.role_code = 'LEAD';
        IF v_lead_id IS NOT NULL THEN
            CALL assert_lead_rotation(v_lead_id, NEW.camp_id,
                                      NEW.program_id, YEAR(NEW.assessment_dt),
                                      OLD.assessment_id);
        END IF;
    END IF;
END$$

CREATE TRIGGER no_date_conflict_assignment_insert
BEFORE INSERT ON assessment_assignment
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM assessment a_new
        JOIN assessment a_other ON a_other.assessment_dt = a_new.assessment_dt
        JOIN assessment_assignment aa ON aa.assessment_id = a_other.assessment_id
        WHERE a_new.assessment_id = NEW.assessment_id
          AND a_other.assessment_id <> NEW.assessment_id
          AND aa.volunteer_id = NEW.volunteer_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Volunteer already assigned on that assessment date';
    END IF;
END$$

CREATE TRIGGER no_date_conflict_assignment_update
BEFORE UPDATE ON assessment_assignment
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM assessment a_new
        JOIN assessment a_other ON a_other.assessment_dt = a_new.assessment_dt
        JOIN assessment_assignment aa ON aa.assessment_id = a_other.assessment_id
        WHERE a_new.assessment_id = NEW.assessment_id
          AND a_other.assessment_id <> NEW.assessment_id
          AND aa.volunteer_id = NEW.volunteer_id
          AND aa.assignment_id <> OLD.assignment_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Volunteer already assigned on that assessment date';
    END IF;
END$$

CREATE TRIGGER no_date_conflict_assessment_update
BEFORE UPDATE ON assessment
FOR EACH ROW
BEGIN
    IF NEW.assessment_dt <> OLD.assessment_dt AND EXISTS (
        SELECT 1
        FROM assessment_assignment mine
        JOIN assessment_assignment theirs
          ON theirs.volunteer_id = mine.volunteer_id
        JOIN assessment other_a ON other_a.assessment_id = theirs.assessment_id
        WHERE mine.assessment_id = OLD.assessment_id
          AND theirs.assessment_id <> OLD.assessment_id
          AND other_a.assessment_dt = NEW.assessment_dt
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Rescheduling conflicts with an assigned volunteer';
    END IF;
END$$

DELIMITER ;
