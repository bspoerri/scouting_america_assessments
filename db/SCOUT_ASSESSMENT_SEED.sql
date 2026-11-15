/*******************************************************************************
  SCOUT ASSESSMENT - DEMONSTRATION SEED DATA
  File: SCOUT_ASSESSMENT_SEED_v1_0.sql
  Compatible with: SCOUT_ASSESSMENT_MYSQL.sql, Version 1.0.0 (as shared)

  PURPOSE
    Populate each of the six project tables with a small, FICTIONAL dataset.
    The records are for testing only; they are NOT actual Scouting America data.
    Email addresses use reserved example.com domains.

  BEFORE RUNNING
    1. Connect DBeaver to MySQL (not PostgreSQL).
    2. Run the database initialization script to create the six tables.
    3. Run this file as a SQL script, in full.

  RE-RUNNING
    This script removes ONLY its own sample rows (negative IDs -101 to -106),
    then inserts them again. It does not DROP any database or table.
    Do not assign these negative IDs to real records.

  NOTE ABOUT BUSINESS RULES
    This seed data meets the proposed one-lead and <=50%-first-time rules.
    The latter rule is NOT enforced by the Version 1.0.0 table definitions.
*******************************************************************************/

USE scout_assessment;

START TRANSACTION;

/*******************************************************************************
  0. Clear only demo records, in child-to-parent order (makes reruns possible)
*******************************************************************************/
DELETE FROM assessment_assignment WHERE assessment_id IN (-101, -102);
DELETE FROM assessment WHERE assessment_id IN (-101, -102);
DELETE FROM camp WHERE camp_id IN (-101, -102);
DELETE FROM volunteer WHERE volunteer_id IN (-101, -102, -103, -104, -105, -106);
DELETE FROM program WHERE program_id IN (-101, -102);
DELETE FROM council WHERE council_num IN (-101, -102);

/*******************************************************************************
  1. COUNCIL: parent records for camps and volunteers
*******************************************************************************/
INSERT INTO council (council_num, council_name) VALUES
    (-101, 'Demo Northern Council'),
    (-102, 'Demo Coastal Council');

/*******************************************************************************
  2. VOLUNTEER: tenure must be 'first-time' or 'experienced' in Version 1.0.0
     All names and contacts in this section are fictional.
*******************************************************************************/
INSERT INTO volunteer (
    volunteer_id, council_num, first_name, pref_name, last_name,
    email, phone, tenure
) VALUES
    (-101, -101, 'Alex',   'Alex',  'Rivera',  'alex.rivera@example.com',   '(000) 555-0101', 'experienced'),
    (-102, -101, 'Morgan', 'Morgan','Lee',     'morgan.lee@example.com',    '(000) 555-0102', 'experienced'),
    (-103, -102, 'Taylor', 'Taylor','Chen',    'taylor.chen@example.com',   '(000) 555-0103', 'first-time'),
    (-104, -102, 'Jordan', 'Jordan','Brooks',  'jordan.brooks@example.com', '(000) 555-0104', 'experienced'),
    (-105, -101, 'Casey',  'Casey', 'Morgan',  'casey.morgan@example.com',  '(000) 555-0105', 'experienced'),
    (-106, -102, 'Riley',  'Riley', 'Patel',   'riley.patel@example.com',   '(000) 555-0106', 'first-time');

/*******************************************************************************
  3. CAMP: demo addresses, directors, and ITO codes are NOT real camp details
*******************************************************************************/
INSERT INTO camp (
    camp_id, camp_name, council_num, director_name, director_email,
    street, city, state, country, ito_code
) VALUES
    (-101, 'Demo Camp Pine Ridge', -101, 'Demo Director One',
     'director.one@example.com', '10 Example Trail', 'Example Falls',
     'Maine', 'United States', 'DEMO-ITO-01'),
    (-102, 'Demo Camp Seaside', -102, 'Demo Director Two',
     'director.two@example.com', '20 Sample Lane', 'Sample Harbor',
     'New Hampshire', 'United States', 'DEMO-ITO-02');

/*******************************************************************************
  4. PROGRAM: max_score is required by Version 1.0.0, so 100 is a DEMO value.
     It is not an assertion about actual NCAP scoring.
*******************************************************************************/
INSERT INTO program (program_id, program_name, max_score) VALUES
    (-101, 'Scouts BSA', 100),
    (-102, 'Cub Scouts', 100);

/*******************************************************************************
  5. ASSESSMENT: one camp and exactly one program per assessment
     required_assessors here means non-lead team members (3 and 2 respectively)
*******************************************************************************/
INSERT INTO assessment (
    assessment_id, camp_id, program_id, assessment_date,
    required_assessors, completed_ind
) VALUES
    (-101, -101, -101, '2027-07-06', 3, FALSE),
    (-102, -102, -102, '2027-07-13', 2, FALSE);

/*******************************************************************************
  6. ASSESSMENT_ASSIGNMENT:
       lead_ind = 1       => team lead
       alternate_ind = 1  => alternate (not in active-team percentage)
       first_time_ind = 1 => first-time status at THIS assessment

     Assessment -101: 1 lead + 3 confirmed members (1 first-time) + 1 alternate
     Assessment -102: 1 lead + 2 confirmed members (1 first-time) + 1 alternate
     Both pass the proposed <=50% first-time rule for active team members.
*******************************************************************************/
INSERT INTO assessment_assignment (
    assessment_id, volunteer_id, lead_ind, alternate_ind, first_time_ind
) VALUES
    (-101, -101, TRUE,  FALSE, FALSE), -- Lead
    (-101, -102, FALSE, FALSE, FALSE), -- Confirmed experienced assessor
    (-101, -103, FALSE, FALSE, TRUE),  -- Confirmed first-time assessor
    (-101, -104, FALSE, FALSE, FALSE), -- Confirmed experienced assessor
    (-101, -105, FALSE, TRUE,  FALSE), -- Alternate

    (-102, -105, TRUE,  FALSE, FALSE), -- Lead
    (-102, -104, FALSE, FALSE, FALSE), -- Confirmed experienced assessor
    (-102, -106, FALSE, FALSE, TRUE),  -- Confirmed first-time assessor
    (-102, -102, FALSE, TRUE,  FALSE);-- Alternate

COMMIT;

/*******************************************************************************
  7. VERIFICATION: should return counts of 2, 6, 2, 2, 2, 9
*******************************************************************************/
SELECT 'council' AS table_name, COUNT(*) AS demo_rows
FROM council WHERE council_num IN (-101, -102)
UNION ALL
SELECT 'volunteer', COUNT(*) FROM volunteer
WHERE volunteer_id IN (-101, -102, -103, -104, -105, -106)
UNION ALL
SELECT 'camp', COUNT(*) FROM camp WHERE camp_id IN (-101, -102)
UNION ALL
SELECT 'program', COUNT(*) FROM program WHERE program_id IN (-101, -102)
UNION ALL
SELECT 'assessment', COUNT(*) FROM assessment WHERE assessment_id IN (-101, -102)
UNION ALL
SELECT 'assessment_assignment', COUNT(*) FROM assessment_assignment
WHERE assessment_id IN (-101, -102);

/*******************************************************************************
  8. VERIFICATION: team composition, excluding alternates
     Expected: -101 has 4 active, 1 lead, 1 first-time = 25.0%
               -102 has 3 active, 1 lead, 1 first-time = 33.3%
*******************************************************************************/
SELECT
    a.assessment_id,
    c.camp_name,
    p.program_name,
    a.assessment_date,
    a.required_assessors,
    SUM(CASE WHEN aa.alternate_ind = FALSE THEN 1 ELSE 0 END) AS active_team_size,
    SUM(CASE WHEN aa.alternate_ind = FALSE AND aa.lead_ind = TRUE
             THEN 1 ELSE 0 END) AS active_leads,
    SUM(CASE WHEN aa.alternate_ind = FALSE AND aa.first_time_ind = TRUE
             THEN 1 ELSE 0 END) AS first_time_active,
    SUM(CASE WHEN aa.alternate_ind = TRUE THEN 1 ELSE 0 END) AS alternates,
    ROUND(100.0 * SUM(CASE WHEN aa.alternate_ind = FALSE AND aa.first_time_ind = TRUE
                           THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN aa.alternate_ind = FALSE THEN 1 ELSE 0 END), 0),
          1) AS first_time_pct
FROM assessment a
JOIN camp c ON c.camp_id = a.camp_id
JOIN program p ON p.program_id = a.program_id
LEFT JOIN assessment_assignment aa ON aa.assessment_id = a.assessment_id
WHERE a.assessment_id IN (-101, -102)
GROUP BY a.assessment_id, c.camp_name, p.program_name,
         a.assessment_date, a.required_assessors
ORDER BY a.assessment_date;

/*******************************************************************************
  9. VERIFICATION: list assignments by role
*******************************************************************************/
SELECT
    a.assessment_date,
    c.camp_name,
    CONCAT(v.first_name, ' ', v.last_name) AS volunteer_name,
    CASE
        WHEN aa.alternate_ind = TRUE THEN 'Alternate'
        WHEN aa.lead_ind = TRUE THEN 'Lead'
        ELSE 'Member'
    END AS assignment_role,
    CASE WHEN aa.first_time_ind = TRUE THEN 'First-Time'
         ELSE 'Experienced' END AS experience_at_assessment
FROM assessment_assignment aa
JOIN assessment a ON a.assessment_id = aa.assessment_id
JOIN camp c ON c.camp_id = a.camp_id
JOIN volunteer v ON v.volunteer_id = aa.volunteer_id
WHERE a.assessment_id IN (-101, -102)
ORDER BY a.assessment_date,
         aa.alternate_ind, aa.lead_ind DESC, v.last_name;
