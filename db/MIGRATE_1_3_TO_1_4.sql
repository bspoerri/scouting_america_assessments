USE scout_assessment;

/*******************************************************************************
  Version 1.4.0: lead rotation and same-day assignment conflicts

  Rules:
   - Camp + program identifies a recurring annual assessment.
   - One volunteer may lead at most three CONSECUTIVE years for that pair.
   - All assignment roles (including ALTERNATE) reserve the entire day.
   - Validation covers assigning/promoting a volunteer and rescheduling or
     changing the camp/program of an existing assessment.

  Upgrade script for an EXISTING v1.3 database. Do not run after the
  complete v1.4 DDL. Back up existing data first.
*******************************************************************************/

-- Index is optional for correctness. Create it once if needed:
-- CREATE INDEX idx_assessment_assessment_dt ON assessment (assessment_dt);

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
