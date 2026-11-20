/*******************************************************************************
  SCOUT ASSESSMENT - UAT (USER ACCEPTANCE TESTING) SEED DATA
  File: SCOUT_ASSESSMENT_SEED_UAT.sql
  Compatible with: SCOUT_ASSESSMENT_DDL.sql, Version 1.4.0

  PURPOSE
    Load a small, FICTIONAL dataset that exercises every business rule
    and every menu option in the application. NOT real Scouting America
    data; all emails use the reserved example.com domain.
    Never run this script against the production database.

  BEFORE RUNNING
    1. Run SCOUT_ASSESSMENT_DDL.sql (v1.3.0) to create the schema.
    2. Run this file as a SQL script, in full (DBeaver: Alt+X, or
       mysql -u <user> -p < SCOUT_ASSESSMENT_SEED_UAT.sql).

  RE-RUNNING
    Safe to re-run at any time. Step 0 removes the demo rows (negative
    IDs) AND anything testers created that hangs off them: assessments
    at demo camps or for demo programs, assignments of demo volunteers,
    and camps/volunteers added under demo councils. Nothing else is
    touched, and no table or database is dropped.

  DATES
    Dates are relative to the day the script runs, so the data never
    goes stale:  Y = YEAR(CURRENT_DATE()).
      history   -> years Y-3 .. Y-1 (always in the past)
      overdue   -> CURRENT_DATE() - 14 / - 7 days
      upcoming  -> year Y+1 (always in the future)

  DATA OVERVIEW
    Councils   -101 Demo Northern, -102 Demo Coastal, -103 Demo Lakes
    Camps      -101 Pine Ridge (ME), -102 Seaside (NH),
               -103 Lakeview (Canada, no state), -104 Unassessed (NH)
    Programs   -101 Scouts BSA 85, -102 Cub Scouts 80,
               -103 High Adventure 90, -104 Family Camp 75 (unused)

    Volunteers                     baseline     ends up as
      -101 Alex Rivera             EXPERIENCED  experienced
      -102 Morgan Lee              EXPERIENCED  experienced
      -103 Taylor Chen             NEW          experienced (assessor, Y-2)
      -104 Jordan Brooks           EXPERIENCED  experienced
      -105 Casey Morgan            EXPERIENCED  experienced
      -106 Riley Patel             NEW          first time
      -107 Sam Ortiz               NEW          first time
      -108 Jamie Kim               NEW          first time
      -109 Drew Alvarez            NEW          first time (was only an
                                                ALTERNATE on a completed
                                                assessment)
      -110 Pat Nguyen              EXPERIENCED  INACTIVE, has history
      -111 Avery Johnson           EXPERIENCED  INACTIVE, no history
      -112 Bartholomew-Maximilian  NEW          first time; 40-char first
           Featherstonehaugh Ashby              name, pref_name = first
      -113 Quinn Foster            EXPERIENCED  active, unassigned

    Assessments (seats = LEAD + ASSESSOR; alternates are extra)
      id    camp / program               date        req  status     team
      -101  Pine Ridge / Scouts BSA      Y-3-07-09   3    COMPLETED  Alex*, Morgan, Jordan
      -102  Pine Ridge / Scouts BSA      Y-2-07-08   3    COMPLETED  Alex*, Taylor, Jordan, Drew(alt)
      -103  Pine Ridge / Scouts BSA      Y-1-07-07   4    COMPLETED  Alex*, Morgan, Taylor, Pat
      -104  Seaside    / Cub Scouts      Y-1-08-11   2    COMPLETED  Casey*, Morgan
      -105  Lakeview   / High Adventure  today-14    2    FILLED     Jordan*, Riley          (overdue)
      -106  Seaside    / High Adventure  today-7     2    PLANNED    no team                 (overdue)
      -107  Pine Ridge / Scouts BSA      Y+1-07-06   4    FILLED     Morgan*, Taylor, Riley, Sam, Jordan(alt)
      -108  Seaside    / Scouts BSA      Y+1-07-13   3    PLANNED    Jordan*, Jamie, Drew(alt)
      -109  Seaside    / Cub Scouts      Y+1-08-10   2    PLANNED    no team
      -110  Lakeview   / Scouts BSA      Y+1-07-20   2    FILLED     Alex*, Bartholomew, Casey(alt)
      (* = LEAD)

  UAT TEST CASES (expected result in brackets)
    T01 Quick views > overdue assessments            [-105 and -106 listed]
    T02 Quick views > scheduled assessments          [-105 to -110, by date]
    T03 Quick views > volunteer activity report      [Alex: 3 completed as lead]
    T04 Quick views > completed assessment history   [4 rows, lead emails shown]
    T05 Modify -106 > mark complete                  [refused: no lead]
    T06 Modify -105 > mark complete, score 90        [COMPLETED; Riley becomes
                                                      experienced]
    T07 Modify -107 > mark complete                  [refused: date in future]
    T08 Modify -107 > required assessors to 3        [refused: below 4 filled]
    T09 Modify -108 > required assessors to 2        [-108 becomes FILLED]
    T10 Enter assignments on -109                    [first pick must be LEAD;
                                                      only experienced shown,
                                                      Pat/Avery not shown]
    T11 Enter assignments on -107                    [fully staffed -> ALTERNATE]
    T12 Drop Bartholomew from -110                   [Casey promoted to ASSESSOR]
    T13 Drop Morgan (LEAD) from -107                 [must pick Taylor as new
                                                      lead; Jordan promoted]
    T14 Drop Jordan (LEAD) from -108                 [no experienced assessor:
                                                      cancelled (known gap)]
    T15 Enter assignments on -108 as LEAD            [Drew is listed as first
                                                      time: ALTERNATE history
                                                      gives no experience]
    T16 Deactivate Riley                             [warns about -105, -107;
                                                      drops from both]
    T17 Activate Pat, then assign Pat to -109        [Pat listed and assignable]
    T18 Add volunteer with 40+ char first name and
        blank preferred name                         [saves; pref = first name]
    T19 Add volunteer with email morgan.lee@...      [refused: duplicate email]
    T20 Delete camp / delete program                 [only Unassessed camp and
                                                      Family Camp are offered]
    T21 Schedule Pine Ridge / Scouts BSA in Y+1      [refused: one per year]
    T22 Schedule with a past date                    [re-prompted]
    T23 Cancel -109                                  [deleted, no one to notify]
    T24 Lead rotation: Alex led -101..-103 in a row  [NOT enforced in v1.3.0;
                                                      Alex can still be lead]
    T25 Modify -105 > mark complete, score 95        [re-prompted: above
                                                      High Adventure target 90]
    T26 Update program Scouts BSA target to 80       [re-prompted: -103 already
                                                      scored 83]
*******************************************************************************/

USE scout_assessment;

SET @y = YEAR(CURRENT_DATE());

START TRANSACTION;

/*******************************************************************************
  0. Remove demo rows and anything testers attached to them
     (child-to-parent order). Deleting an assessment cascades to its
     assignments.
*******************************************************************************/
DELETE FROM assessment
WHERE assessment_id BETWEEN -110 AND -101
   OR program_id BETWEEN -104 AND -101
   OR camp_id IN (SELECT c.camp_id FROM camp c
                  WHERE c.council_num BETWEEN -103 AND -101);

DELETE FROM assessment_assignment
WHERE volunteer_id IN (SELECT v.volunteer_id FROM volunteer v
                       WHERE v.council_num BETWEEN -103 AND -101);

DELETE FROM camp      WHERE council_num BETWEEN -103 AND -101;
DELETE FROM volunteer WHERE council_num BETWEEN -103 AND -101;
DELETE FROM program   WHERE program_id  BETWEEN -104 AND -101;
DELETE FROM council   WHERE council_num BETWEEN -103 AND -101;

/*******************************************************************************
  1. COUNCIL
*******************************************************************************/
INSERT INTO council (council_num, council_name) VALUES
    (-101, 'Demo Northern Council'),
    (-102, 'Demo Coastal Council'),
    (-103, 'Demo Lakes Council');

/*******************************************************************************
  2. VOLUNTEER
     pref_name is always given explicitly. Passing NULL would fail:
     the DEFAULT (first_name) only applies when the column is omitted.
     All start active; -110 and -111 are deactivated in step 7.
*******************************************************************************/
INSERT INTO volunteer (
    volunteer_id, council_num, first_name, pref_name, last_name,
    email, phone, experience_baseline
) VALUES
    (-101, -101, 'Alexander', 'Alex',   'Rivera',  'alex.rivera@example.com',   '(000) 555-0101', 'EXPERIENCED'),
    (-102, -101, 'Morgan',    'Morgan', 'Lee',     'morgan.lee@example.com',    '(000) 555-0102', 'EXPERIENCED'),
    (-103, -102, 'Taylor',    'Taylor', 'Chen',    'taylor.chen@example.com',   '(000) 555-0103', 'NEW'),
    (-104, -102, 'Jordan',    'Jordan', 'Brooks',  'jordan.brooks@example.com', '(000) 555-0104', 'EXPERIENCED'),
    (-105, -101, 'Casey',     'Casey',  'Morgan',  'casey.morgan@example.com',  '(000) 555-0105', 'EXPERIENCED'),
    (-106, -102, 'Riley',     'Riley',  'Patel',   'riley.patel@example.com',   '(000) 555-0106', 'NEW'),
    (-107, -101, 'Samuel',    'Sam',    'Ortiz',   'sam.ortiz@example.com',     '(000) 555-0107', 'NEW'),
    (-108, -102, 'Jamie',     'Jamie',  'Kim',     'jamie.kim@example.com',     '(000) 555-0108', 'NEW'),
    (-109, -103, 'Drew',      'Drew',   'Alvarez', 'drew.alvarez@example.com',  '(000) 555-0109', 'NEW'),
    (-110, -103, 'Patricia',  'Pat',    'Nguyen',  'pat.nguyen@example.com',    '(000) 555-0110', 'EXPERIENCED'),
    (-111, -101, 'Avery',     'Avery',  'Johnson', 'avery.johnson@example.com', '(000) 555-0111', 'EXPERIENCED'),
    (-112, -103, 'Bartholomew-Maximilian Featherstonehaugh',
                 'Bartholomew-Maximilian Featherstonehaugh',
                                        'Ashby',   'b.ashby@example.com',       '(000) 555-0112', 'NEW'),
    (-113, -102, 'Quinn',     'Quinn',  'Foster',  'quinn.foster@example.com',  '(000) 555-0113', 'EXPERIENCED');

/*******************************************************************************
  3. CAMP: demo directors, addresses, and ITO codes are not real
     -103 is outside the United States, so state may be NULL (check_usa)
     -104 has no assessments, so it can be deleted in the app
*******************************************************************************/
INSERT INTO camp (
    camp_id, camp_name, council_num, director_name, director_email,
    street, city, state, country, ito_code
) VALUES
    (-101, 'Demo Camp Pine Ridge', -101, 'Demo Director One',
     'director.one@example.com',   '10 Example Trail', 'Example Falls',
     'Maine',         'United States', 'DEMO-ITO-01'),
    (-102, 'Demo Camp Seaside',    -102, 'Demo Director Two',
     'director.two@example.com',   '20 Sample Lane',   'Sample Harbor',
     'New Hampshire', 'United States', 'DEMO-ITO-02'),
    (-103, 'Demo Camp Lakeview',   -103, 'Demo Director Three',
     'director.three@example.com', '30 Test Road',     'Testville',
     NULL,            'Canada',        'DEMO-ITO-03'),
    (-104, 'Demo Camp Unassessed', -102, 'Demo Director Four',
     'director.four@example.com',  '40 Spare Way',     'Spare Town',
     'New Hampshire', 'United States', 'DEMO-ITO-04');

/*******************************************************************************
  4. PROGRAM: demo target scores, not actual NCAP scoring
     -104 has no assessments, so it can be deleted in the app
*******************************************************************************/
INSERT INTO program (program_id, program_name, target_score) VALUES
    (-101, 'Scouts BSA',     85),
    (-102, 'Cub Scouts',     80),
    (-103, 'High Adventure', 90),
    (-104, 'Family Camp',    75);

/*******************************************************************************
  5. ASSESSMENT: all inserted as PLANNED (status default); the status
     triggers move them to FILLED as teams are assigned, and step 7
     completes the historical ones. Past and overdue rows set
     created_dt explicitly because CHECK future requires
     assessment_dt > created_dt.
*******************************************************************************/
INSERT INTO assessment (
    assessment_id, created_dt, camp_id, program_id, assessment_dt,
    required_assessors
) VALUES
    (-101, CONCAT(@y - 3, '-01-16'), -101, -101, CONCAT(@y - 3, '-07-09'), 3),
    (-102, CONCAT(@y - 2, '-01-14'), -101, -101, CONCAT(@y - 2, '-07-08'), 3),
    (-103, CONCAT(@y - 1, '-01-13'), -101, -101, CONCAT(@y - 1, '-07-07'), 4),
    (-104, CONCAT(@y - 1, '-03-02'), -102, -102, CONCAT(@y - 1, '-08-11'), 2),
    (-105, CURRENT_DATE() - INTERVAL 90 DAY, -103, -103,
           CURRENT_DATE() - INTERVAL 14 DAY, 2),
    (-106, CURRENT_DATE() - INTERVAL 60 DAY, -102, -103,
           CURRENT_DATE() - INTERVAL 7 DAY, 2);

-- upcoming: created_dt uses its CURRENT_DATE() default
INSERT INTO assessment (
    assessment_id, camp_id, program_id, assessment_dt, required_assessors
) VALUES
    (-107, -101, -101, CONCAT(@y + 1, '-07-06'), 4),
    (-108, -102, -101, CONCAT(@y + 1, '-07-13'), 3),
    (-109, -102, -102, CONCAT(@y + 1, '-08-10'), 2),
    (-110, -103, -101, CONCAT(@y + 1, '-07-20'), 2);

/*******************************************************************************
  6. ASSESSMENT_ASSIGNMENT: within each team, LEAD first, then
     ASSESSORs, then ALTERNATEs (the order the app adds them).
     Every LEAD has an EXPERIENCED baseline, so the lead trigger passes
     regardless of history.
*******************************************************************************/
INSERT INTO assessment_assignment (assessment_id, volunteer_id, role_code)
VALUES
    -- -101 history Y-3: 3 of 3 experienced
    (-101, -101, 'LEAD'),       -- Alex
    (-101, -102, 'ASSESSOR'),   -- Morgan
    (-101, -104, 'ASSESSOR'),   -- Jordan

    -- -102 history Y-2: Taylor's first assessment; Drew only an alternate
    (-102, -101, 'LEAD'),       -- Alex
    (-102, -103, 'ASSESSOR'),   -- Taylor (first time)
    (-102, -104, 'ASSESSOR'),   -- Jordan
    (-102, -109, 'ALTERNATE'),  -- Drew (gains NO experience)

    -- -103 history Y-1: Pat serves before being deactivated
    (-103, -101, 'LEAD'),       -- Alex (third lead in a row)
    (-103, -102, 'ASSESSOR'),   -- Morgan
    (-103, -103, 'ASSESSOR'),   -- Taylor
    (-103, -110, 'ASSESSOR'),   -- Pat

    -- -104 history Y-1
    (-104, -105, 'LEAD'),       -- Casey
    (-104, -102, 'ASSESSOR'),   -- Morgan

    -- -105 overdue, FILLED, ready to complete: 1 of 2 first time
    (-105, -104, 'LEAD'),       -- Jordan
    (-105, -106, 'ASSESSOR'),   -- Riley (first time)

    -- -106 overdue, no team: cannot be completed (no lead)

    -- -107 upcoming, FILLED: 2 of 4 first time (boundary of half rule)
    (-107, -102, 'LEAD'),       -- Morgan
    (-107, -103, 'ASSESSOR'),   -- Taylor (experienced via -102)
    (-107, -106, 'ASSESSOR'),   -- Riley (first time)
    (-107, -107, 'ASSESSOR'),   -- Sam (first time)
    (-107, -104, 'ALTERNATE'),  -- Jordan

    -- -108 upcoming, PLANNED 2 of 3; lead has no experienced assessor
    (-108, -104, 'LEAD'),       -- Jordan
    (-108, -108, 'ASSESSOR'),   -- Jamie (first time)
    (-108, -109, 'ALTERNATE'),  -- Drew (first time)

    -- -109 upcoming, no team

    -- -110 upcoming, FILLED with an experienced alternate to promote
    (-110, -101, 'LEAD'),       -- Alex
    (-110, -112, 'ASSESSOR'),   -- Bartholomew (first time)
    (-110, -105, 'ALTERNATE');  -- Casey

/*******************************************************************************
  7. LIFECYCLE: complete history in date order (score is required with
     COMPLETED and may not exceed the program target_score, and
     complete_requires_lead needs a LEAD), then
     deactivate the two inactive volunteers.
*******************************************************************************/
UPDATE assessment SET status = 'COMPLETED', score = 78 WHERE assessment_id = -101;
UPDATE assessment SET status = 'COMPLETED', score = 81 WHERE assessment_id = -102;
UPDATE assessment SET status = 'COMPLETED', score = 83 WHERE assessment_id = -103;
UPDATE assessment SET status = 'COMPLETED', score = 76 WHERE assessment_id = -104;

UPDATE volunteer SET active_ind = FALSE WHERE volunteer_id IN (-110, -111);

COMMIT;

/*******************************************************************************
  8. VERIFICATION: row counts
     Expected: council 3, volunteer 13, camp 4, program 4,
               assessment 10, assessment_assignment 26
*******************************************************************************/
SELECT 'council' AS table_name, COUNT(*) AS demo_rows
FROM council WHERE council_num BETWEEN -103 AND -101
UNION ALL
SELECT 'volunteer', COUNT(*) FROM volunteer
WHERE volunteer_id BETWEEN -113 AND -101
UNION ALL
SELECT 'camp', COUNT(*) FROM camp WHERE camp_id BETWEEN -104 AND -101
UNION ALL
SELECT 'program', COUNT(*) FROM program WHERE program_id BETWEEN -104 AND -101
UNION ALL
SELECT 'assessment', COUNT(*) FROM assessment
WHERE assessment_id BETWEEN -110 AND -101
UNION ALL
SELECT 'assessment_assignment', COUNT(*) FROM assessment_assignment
WHERE assessment_id BETWEEN -110 AND -101;

/*******************************************************************************
  9. VERIFICATION: first-time volunteers
     Expected: Drew Alvarez, Bartholomew-Maximilian ... Ashby, Jamie Kim,
               Sam Ortiz, Riley Patel  (Taylor is NEW but experienced)
*******************************************************************************/
SELECT v.volunteer_id,
       CONCAT(v.pref_name, ' ', v.last_name) AS volunteer_name,
       v.active_ind
FROM first_time_volunteers ftv
JOIN volunteer v ON v.volunteer_id = ftv.volunteer_id
WHERE v.volunteer_id BETWEEN -113 AND -101
ORDER BY v.last_name;

/*******************************************************************************
  10. VERIFICATION: status and staffing of every demo assessment
      Expected (id  status     req filled first_time alternates lead):
        -101 COMPLETED  3  3  0  0  Alex
        -102 COMPLETED  3  3  0  1  Alex     (Taylor now experienced)
        -103 COMPLETED  4  4  0  0  Alex
        -104 COMPLETED  2  2  0  0  Casey
        -105 FILLED     2  2  1  0  Jordan
        -106 PLANNED    2  0  0  0  (none)
        -107 FILLED     4  4  2  1  Morgan
        -108 PLANNED    3  2  1  1  Jordan
        -109 PLANNED    2  0  0  0  (none)
        -110 FILLED     2  2  1  1  Alex
*******************************************************************************/
SELECT
    a.assessment_id,
    a.status,
    a.required_assessors AS req,
    COUNT(CASE WHEN aa.role_code IN ('LEAD', 'ASSESSOR') THEN 1 END)
        AS filled,
    COUNT(CASE WHEN aa.role_code IN ('LEAD', 'ASSESSOR')
                AND ev.volunteer_id IS NULL THEN 1 END)
        AS first_time,
    COUNT(CASE WHEN aa.role_code = 'ALTERNATE' THEN 1 END)
        AS alternates,
    MAX(CASE WHEN aa.role_code = 'LEAD' THEN v.pref_name END) AS lead_name
FROM assessment a
LEFT JOIN assessment_assignment aa ON aa.assessment_id = a.assessment_id
LEFT JOIN volunteer v ON v.volunteer_id = aa.volunteer_id
LEFT JOIN experienced_volunteers ev ON ev.volunteer_id = aa.volunteer_id
WHERE a.assessment_id BETWEEN -110 AND -101
GROUP BY a.assessment_id, a.status, a.required_assessors
ORDER BY a.assessment_id DESC;
