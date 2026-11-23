# Module that controls all submenu actions available to users

import datetime
import display_support
import prompts
import mysql.connector


# volunteer display name used in every selection list
VOLUNTEER_NAME = "CONCAT(v.pref_name, ' ', v.last_name)"


def not_implemented(name: str, cursor=None):
    '''
    Placeholder action that tells the user the selected option
    is not available yet.

    Parameters:
        name (string) - name of the selected action
        cursor (mysql cursor object) - unused, kept so the signature
            matches other actions
    '''
    display_support.display_page(f'\n"{name}" is not implemented yet.')


# ---------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------

def update_field(cursor, table: str, key_column: str, key_value: int,
                 fields: dict, int_minimum: int = 1):
    '''
    Let the user pick one field of a record, enter a new value,
    confirm old -> new, and save it. Raises Cancelled if the user
    cancels at any prompt.

    Parameters:
        cursor (mysql cursor object) - object used to run queries
        table (string) - table holding the record
        key_column (string) - primary key column of the table
        key_value (int) - primary key of the record to update
        fields (dict) - column name -> (label, max_len); max_len of
            None means the field is a whole number
        int_minimum (int) - smallest value accepted for a whole
            number field

    Returns:
        label (string) - label of the field that was updated
    '''
    # select_option expects (id, display_name) pairs
    options = [(column, label) for column, (label, max_len)
               in fields.items()]
    column = prompts.select_option(options, 'field to update')[0]
    label, max_len = fields[column]

    # table and column names come from this module (never from user
    # input) so building them into the query string is safe; values
    # still use %s placeholders
    cursor.execute(
        f'SELECT {column} FROM {table} WHERE {key_column} = %s',
        (key_value,)
    )
    old_value = cursor.fetchone()[0]
    print(f'\nCurrent {label.lower()}: {old_value}')

    # prompt with the matching input type
    if max_len is None:
        new_value = prompts.prompt_int(f'New {label.lower()}',
                                       minimum=int_minimum)
    elif 'email' in column:
        new_value = prompts.prompt_email(f'New {label.lower()}', max_len)
    else:
        new_value = prompts.prompt_text(f'New {label.lower()}', max_len)

    # cancel unless user confirms
    prompts.confirm(f'Update {label.lower()}',
                    {label: f'{old_value} -> {new_value}'})
    cursor.execute(
        f'UPDATE {table} SET {column} = %s WHERE {key_column} = %s',
        (new_value, key_value)
    )
    return label


def select_council(cursor):
    '''
    Show all councils and return the one the user picks.

    Parameters:
        cursor (mysql cursor object) - object used to run queries

    Returns:
        row (tuple) - (council_num, council_name)
    '''
    return prompts.select_row(
        cursor,
        'SELECT council_num, council_name FROM council '
        'ORDER BY council_name',
        'council'
    )


def select_open_assessment(cursor):
    '''
    Show assessments that are not completed and return the one the
    user picks. Completed assessments are locked from changes.

    Parameters:
        cursor (mysql cursor object) - object used to run queries

    Returns:
        row (tuple) - (assessment_id, description)
    '''
    # select_row expects exactly (id, display_name) so concat details
    # for display
    return prompts.select_row(
        cursor,
        "SELECT a.assessment_id, "
        "CONCAT(a.assessment_dt, ' - ', c.camp_name, ' - ', "
        "p.program_name, ' (', a.status, ')') "
        'FROM assessment a '
        'JOIN camp c ON c.camp_id = a.camp_id '
        'JOIN program p ON p.program_id = a.program_id '
        "WHERE a.status <> 'COMPLETED' "
        'ORDER BY a.assessment_dt',
        'assessment'
    )


def volunteers_to_notify(cursor, assessment_id: int):
    '''
    Look up the volunteers assigned to an assessment so they can be
    notified when it is cancelled or rescheduled.

    Parameters:
        cursor (mysql cursor object) - object used to run queries
        assessment_id (int) - id of the affected assessment

    Returns:
        emails (string) - assigned volunteer emails joined by "; ",
            or "none" if no one is assigned
    '''
    cursor.execute(
        'SELECT v.email '
        'FROM assessment_assignment aa '
        'JOIN volunteer v ON v.volunteer_id = aa.volunteer_id '
        'WHERE aa.assessment_id = %s',
        (assessment_id,)
    )
    return '; '.join(row[0] for row in cursor.fetchall()) or 'none'


def get_staffing(cursor, assessment_id: int):
    '''
    Count the current team of an assessment. Seats are LEAD +
    ASSESSOR roles; alternates do not hold a seat.

    Parameters:
        cursor (mysql cursor object) - object used to run queries
        assessment_id (int) - id of the assessment

    Returns:
        staffing (tuple) - (required seats, filled seats,
            first time volunteers in seats, number of leads)
    '''
    # a volunteer missing from experienced_volunteers is first time
    cursor.execute(
        'SELECT a.required_assessors, '
        "COUNT(CASE WHEN aa.role_code IN ('LEAD', 'ASSESSOR') "
        'THEN 1 END), '
        "COUNT(CASE WHEN aa.role_code IN ('LEAD', 'ASSESSOR') "
        'AND ev.volunteer_id IS NULL THEN 1 END), '
        "COUNT(CASE WHEN aa.role_code = 'LEAD' THEN 1 END) "
        'FROM assessment a '
        'LEFT JOIN assessment_assignment aa '
        'ON aa.assessment_id = a.assessment_id '
        'LEFT JOIN experienced_volunteers ev '
        'ON ev.volunteer_id = aa.volunteer_id '
        'WHERE a.assessment_id = %s '
        'GROUP BY a.required_assessors',
        (assessment_id,)
    )
    return cursor.fetchone()


def fill_open_seat(cursor, assessment_id: int):
    '''
    Promote the first eligible alternate (earliest added) to
    ASSESSOR after a seat opens up. A first time alternate is only
    eligible while first time volunteers hold fewer than half of
    the required seats.

    Parameters:
        cursor (mysql cursor object) - object used to run queries
        assessment_id (int) - id of the assessment with an open seat

    Returns:
        name (string) - name of the promoted alternate, or None if
            no alternate was eligible
    '''
    required, filled, new_count, lead_count = get_staffing(
        cursor, assessment_id
    )
    # nothing to fill if the team is still fully staffed
    if filled >= required:
        return None

    # alternates in the order they were added, with experience flag
    cursor.execute(
        f'SELECT aa.assignment_id, {VOLUNTEER_NAME}, '
        'ev.volunteer_id IS NOT NULL '
        'FROM assessment_assignment aa '
        'JOIN volunteer v ON v.volunteer_id = aa.volunteer_id '
        'LEFT JOIN experienced_volunteers ev '
        'ON ev.volunteer_id = v.volunteer_id '
        'JOIN assessment selected ON selected.assessment_id = aa.assessment_id '
        "WHERE aa.assessment_id = %s AND aa.role_code = 'ALTERNATE' "
        'AND v.active_ind = TRUE '
        'AND NOT EXISTS ( '
        '  SELECT 1 FROM assessment_assignment other_aa '
        '  JOIN assessment other_a '
        '    ON other_a.assessment_id = other_aa.assessment_id '
        '  WHERE other_aa.volunteer_id = v.volunteer_id '
        '    AND other_a.assessment_dt = selected.assessment_dt '
        '    AND other_a.assessment_id <> selected.assessment_id '
        ') '
        'ORDER BY aa.assignment_id',
        (assessment_id,)
    )
    for assignment_id, alt_name, experienced in cursor.fetchall():
        if experienced or new_count < required / 2:
            cursor.execute(
                "UPDATE assessment_assignment SET role_code = 'ASSESSOR' "
                'WHERE assignment_id = %s',
                (assignment_id,)
            )
            return alt_name
    return None


def drop_assignment(cursor, assessment_id: int, assignment_id: int,
                    role_code: str):
    '''
    Remove one volunteer from an assessment and keep the team
    staffed. A dropped LEAD must be replaced by an experienced
    assessor already on the team (chosen by the user); any seat left
    open is then offered to the first eligible alternate. Raises
    Cancelled if a lead is dropped and no replacement is chosen.

    Parameters:
        cursor (mysql cursor object) - object used to run queries
        assessment_id (int) - id of the assessment
        assignment_id (int) - id of the assignment being dropped
        role_code (string) - role of the assignment being dropped

    Returns:
        notes (list) - text lines describing the team changes
    '''
    notes = []

    # choose the replacement lead before anything is deleted
    new_lead = None
    if role_code == 'LEAD':
        new_lead = prompts.select_row(
            cursor,
            f'SELECT aa.assignment_id, {VOLUNTEER_NAME} '
            'FROM assessment_assignment aa '
            'JOIN volunteer v ON v.volunteer_id = aa.volunteer_id '
            'JOIN experienced_volunteers ev '
            'ON ev.volunteer_id = v.volunteer_id '
            "WHERE aa.assessment_id = %s AND aa.role_code = 'ASSESSOR' "
            'ORDER BY v.last_name',
            'replacement lead',
            (assessment_id,)
        )

    # delete first: only one LEAD is allowed per assessment
    # (uq_one_lead), so the old lead must be gone before promoting
    cursor.execute(
        'DELETE FROM assessment_assignment WHERE assignment_id = %s',
        (assignment_id,)
    )
    if new_lead:
        cursor.execute(
            "UPDATE assessment_assignment SET role_code = 'LEAD' "
            'WHERE assignment_id = %s',
            (new_lead[0],)
        )
        notes.append(f'{new_lead[1]} is the new lead.')

    # dropping a LEAD or ASSESSOR opens a seat; alternates hold none
    if role_code in ('LEAD', 'ASSESSOR'):
        promoted = fill_open_seat(cursor, assessment_id)
        if promoted:
            notes.append(f'Alternate {promoted} promoted to assessor.')
        else:
            notes.append('No eligible alternate; seat left open.')
    return notes


# ---------------------------------------------------------------------
# Camp manager
# ---------------------------------------------------------------------

def add_camp(name: str, cursor):
    '''
    Prompt for camp details, confirm with the user, and insert a new
    camp. State is required for camps in the United States
    (check_usa). Raises Cancelled if the user cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message with the new camp id
    '''
    display_support.display_page(name, to_upper=True)

    # max lengths match the camp column sizes
    camp_name = prompts.prompt_text('Camp name', 100)
    council = select_council(cursor)
    director_name = prompts.prompt_text('Director name', 60)
    director_email = prompts.prompt_email('Director email', 254)
    street = prompts.prompt_text('Street', 120)
    city = prompts.prompt_text('City', 60)
    # state is only required inside the United States
    if prompts.yes_no('Is the camp in the United States?'):
        country = 'United States'
        state = prompts.prompt_text('State', 50)
    else:
        country = prompts.prompt_text('Country', 60)
        state = prompts.prompt_text('State/province', 50, required=False)
    ito_code = prompts.prompt_text('ITO code', 15)

    # show summary using display names, cancel unless user confirms
    prompts.confirm('New camp', {
        'Camp': camp_name,
        'Council': council[1],
        'Director': f'{director_name} ({director_email})',
        'Address': f'{street}, {city}, {state or "-"}, {country}',
        'ITO code': ito_code
    })

    # insert using ids, %s placeholders let the connector escape
    # values safely
    cursor.execute(
        'INSERT INTO camp (camp_name, council_num, director_name, '
        'director_email, street, city, state, country, ito_code) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (camp_name, council[0], director_name, director_email, street,
         city, state, country, ito_code)
    )
    # lastrowid holds the auto-generated (incrementing) id
    return f'Camp added (id {cursor.lastrowid}).'


def update_camp_info(name: str, cursor):
    '''
    Prompt for a camp and one field to change, then save the new
    value once the user confirms. Raises Cancelled if the user
    cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message naming the updated field
    '''
    display_support.display_page(name, to_upper=True)

    camp = prompts.select_row(
        cursor,
        'SELECT camp_id, camp_name FROM camp ORDER BY camp_name',
        'camp'
    )
    # editable columns -> (label, max length)
    label = update_field(cursor, 'camp', 'camp_id', camp[0], {
        'camp_name': ('Camp name', 100),
        'director_name': ('Director name', 60),
        'director_email': ('Director email', 254),
        'street': ('Street', 120),
        'city': ('City', 60),
        'state': ('State', 50),
        'country': ('Country', 60),
        'ito_code': ('ITO code', 15)
    })
    return f'{camp[1]}: {label.lower()} updated.'


def delete_camp(name: str, cursor):
    '''
    Prompt for a camp that has never been assessed, confirm with the
    user, and delete it. Camps with assessments are not shown.
    Raises Cancelled if the user cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message with the deleted camp
    '''
    display_support.display_page(name, to_upper=True)

    # only show/allow removal of unassessed camps
    camp = prompts.select_row(
        cursor,
        'SELECT c.camp_id, c.camp_name FROM camp c '
        'WHERE NOT EXISTS (SELECT 1 FROM assessment a '
        'WHERE a.camp_id = c.camp_id) '
        'ORDER BY c.camp_name',
        'unassessed camp'
    )

    # cancel unless user confirms
    prompts.confirm('Delete camp', {'Camp': camp[1]})
    cursor.execute('DELETE FROM camp WHERE camp_id = %s', (camp[0],))
    return f'{camp[1]} deleted.'


# ---------------------------------------------------------------------
# Program manager
# ---------------------------------------------------------------------

def add_program(name: str, cursor):
    '''
    Prompt for a program name and target score, confirm with the
    user, and insert a new program. Raises Cancelled if the user
    cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message with the new program id
    '''
    display_support.display_page(name, to_upper=True)

    program_name = prompts.prompt_text('Program name', 45)
    # matches min_target (target_score > 0)
    target_score = prompts.prompt_int('Target score', minimum=1)

    # cancel unless user confirms
    prompts.confirm('New program', {
        'Program': program_name,
        'Target score': target_score
    })

    cursor.execute(
        'INSERT INTO program (program_name, target_score) '
        'VALUES (%s, %s)',
        (program_name, target_score)
    )
    return f'Program added (id {cursor.lastrowid}).'


def update_program_info(name: str, cursor):
    '''
    Prompt for a program and one field to change, then save the new
    value once the user confirms. Raises Cancelled if the user
    cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message naming the updated field
    '''
    display_support.display_page(name, to_upper=True)

    program = prompts.select_row(
        cursor,
        'SELECT program_id, program_name FROM program '
        'ORDER BY program_name',
        'program'
    )
    # target cannot drop below a score already recorded for this
    # program (target_not_below_scores) or below 1 (min_target)
    cursor.execute(
        'SELECT COALESCE(MAX(score), 0) FROM assessment '
        'WHERE program_id = %s',
        (program[0],)
    )
    highest_score = cursor.fetchone()[0]

    # max length of None marks target_score as a whole number field
    label = update_field(cursor, 'program', 'program_id', program[0], {
        'program_name': ('Program name', 45),
        'target_score': ('Target score', None)
    }, int_minimum=max(1, highest_score))
    return f'{program[1]}: {label.lower()} updated.'


def delete_program(name: str, cursor):
    '''
    Prompt for a program with no assessments, confirm with the user,
    and delete it. Raises Cancelled if the user cancels at any
    prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message with the deleted program
    '''
    display_support.display_page(name, to_upper=True)

    # only show programs with no assessments
    program = prompts.select_row(
        cursor,
        'SELECT p.program_id, p.program_name FROM program p '
        'WHERE NOT EXISTS (SELECT 1 FROM assessment a '
        'WHERE a.program_id = p.program_id) '
        'ORDER BY p.program_name',
        'unassessed program'
    )

    # cancel unless user confirms
    prompts.confirm('Delete program', {'Program': program[1]})
    cursor.execute('DELETE FROM program WHERE program_id = %s',
                   (program[0],))
    return f'{program[1]} deleted.'


# ---------------------------------------------------------------------
# Assessment scheduler
# ---------------------------------------------------------------------

def schedule_assessment(name: str, cursor):
    '''
    Prompt for a camp, program, date, and number of required
    assessors, confirm with the user, and insert a new assessment.
    Raises Cancelled if the user cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message with the new assessment id
    '''
    display_support.display_page(name, to_upper=True)

    # collect assessment fields, select_row returns (id, display_name)
    camp = prompts.select_row(
        cursor,
        'SELECT camp_id, camp_name FROM camp ORDER BY camp_name',
        'camp'
    )
    program = prompts.select_row(
        cursor,
        'SELECT program_id, program_name FROM program '
        'ORDER BY program_name',
        'program'
    )
    assessment_dt = prompts.prompt_date('Assessment date')
    # matches check_required_assessors (> 0)
    required = prompts.prompt_int('Number of required assessors',
                                  minimum=1)

    # show summary using display names, cancel unless user confirms
    prompts.confirm('New assessment', {
        'Camp': camp[1],
        'Program': program[1],
        'Date': assessment_dt,
        'Required assessors': required
    })

    # status defaults to PLANNED; one camp-program per year is
    # enforced by the database (one_per_camp_program_year)
    cursor.execute(
        'INSERT INTO assessment '
        '(camp_id, program_id, assessment_dt, required_assessors) '
        'VALUES (%s, %s, %s, %s)',
        (camp[0], program[0], assessment_dt, required)
    )
    return f'Assessment scheduled (id {cursor.lastrowid}).'


def modify_assessment(name: str, cursor):
    '''
    Prompt for an assessment that is not completed and make one
    change: move the date (must be after today), change the number
    of required assessors (not below the seats already filled), or
    mark it complete with a score (only once its date has arrived and
    a lead is assigned). Raises Cancelled if the user
    cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - result message for the change made
    '''
    display_support.display_page(name, to_upper=True)

    # only non-completed assessments appear as options
    assessment = select_open_assessment(cursor)
    assessment_id = assessment[0]

    change = prompts.select_option([
        ('date', 'Change date'),
        ('required', 'Change number of required assessors'),
        ('complete', 'Mark complete (enter score)')
    ], 'change')[0]

    if change == 'date':
        # prompt_date only accepts dates after today
        new_dt = prompts.prompt_date('New assessment date')
        # a new date is a material change, so list who to notify
        prompts.confirm(f'Update assessment {assessment_id}', {
            'Assessment': assessment[1],
            'New date': new_dt,
            'Assessors to notify': volunteers_to_notify(cursor,
                                                        assessment_id)
        })
        cursor.execute(
            'UPDATE assessment SET assessment_dt = %s '
            'WHERE assessment_id = %s',
            (new_dt, assessment_id)
        )
        return f'Assessment {assessment_id} moved to {new_dt}.'

    if change == 'required':
        required, filled, new_count, lead_count = get_staffing(
            cursor, assessment_id
        )
        print(f'\nSeats filled: {filled} of {required}')
        # cannot drop below seats already filled
        # (required_not_below_filled) or below 1
        # (check_required_assessors)
        new_required = prompts.prompt_int(
            'New number of required assessors', minimum=max(1, filled)
        )
        prompts.confirm(f'Update assessment {assessment_id}', {
            'Assessment': assessment[1],
            'Required assessors': f'{required} -> {new_required}'
        })
        # status (PLANNED/FILLED) is re-derived by the database trigger
        cursor.execute(
            'UPDATE assessment SET required_assessors = %s '
            'WHERE assessment_id = %s',
            (new_required, assessment_id)
        )
        return f'Assessment {assessment_id} now requires {new_required}.'

    # mark complete: cannot complete an assessment before its date
    cursor.execute(
        'SELECT assessment_dt FROM assessment WHERE assessment_id = %s',
        (assessment_id,)
    )
    assessment_dt = cursor.fetchone()[0]
    if assessment_dt > datetime.date.today():
        return (f'Assessment {assessment_id} is on {assessment_dt} and '
                'cannot be marked complete yet.')

    # a lead is required to complete (complete_requires_lead trigger);
    # check here so the user is not asked for a score first
    lead_count = get_staffing(cursor, assessment_id)[3]
    if lead_count == 0:
        return (f'Assessment {assessment_id} has no lead and cannot be '
                'marked complete. Assign a lead first.')

    # score is required when completing (score_when_complete) and
    # cannot exceed the program target (score_within_target_update)
    cursor.execute(
        'SELECT p.target_score FROM assessment a '
        'JOIN program p ON p.program_id = a.program_id '
        'WHERE a.assessment_id = %s',
        (assessment_id,)
    )
    target_score = cursor.fetchone()[0]
    score = prompts.prompt_int(f'Score (target {target_score})',
                               minimum=0, maximum=target_score)
    prompts.confirm(f'Complete assessment {assessment_id}', {
        'Assessment': assessment[1],
        'Score': score
    })
    cursor.execute(
        "UPDATE assessment SET status = 'COMPLETED', score = %s "
        'WHERE assessment_id = %s',
        (score, assessment_id)
    )
    return f'Assessment {assessment_id} marked complete.'


def cancel_assessment(name: str, cursor):
    '''
    Prompt for an assessment that is not completed, confirm with the
    user, and delete it. Team assignments are removed by ON DELETE
    CASCADE. Raises Cancelled if the user cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message with the cancelled id
    '''
    display_support.display_page(name, to_upper=True)

    # canceling is deleting; completed assessments are not listed so
    # they can never be deleted
    assessment = select_open_assessment(cursor)

    # show summary with assigned volunteers, cancel unless user confirms
    prompts.confirm('Cancel assessment', {
        'Assessment': assessment[1],
        'Assessors to notify': volunteers_to_notify(cursor,
                                                    assessment[0])
    })

    cursor.execute('DELETE FROM assessment WHERE assessment_id = %s',
                   (assessment[0],))
    return f'Assessment {assessment[0]} cancelled.'


# ---------------------------------------------------------------------
# Manage assignments
# ---------------------------------------------------------------------

def enter_assignments(name: str, cursor):
    '''
    Prompt for an assessment that is not completed, then add
    volunteers one at a time until the user stops. The role is set
    by the team's state:
        - no lead yet          -> LEAD (experienced only)
        - open seats remaining -> ASSESSOR (first time volunteers are
          hidden once they hold half of the required seats)
        - fully staffed        -> ALTERNATE
    The team does not have to be complete to save. A warning is
    shown if first time volunteers outnumber experienced ones.
    Cancelling the volunteer list after at least one pick ends the
    loop and goes to the save summary with the picks so far. Raises
    Cancelled if the user cancels before picking anyone or declines
    the final save (nothing from this session is saved).

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message with the number added
    '''
    display_support.display_page(name, to_upper=True)

    assessment = select_open_assessment(cursor)
    assessment_id = assessment[0]
    added = []

    adding = True
    while adding:
        # re-count each time since every insert changes the team
        required, filled, new_count, lead_count = get_staffing(
            cursor, assessment_id
        )

        # pick the role for the next volunteer
        if lead_count == 0:
            role_code = 'LEAD'
            experienced_only = True
        elif filled < required:
            role_code = 'ASSESSOR'
            # hide first time volunteers once they hold half the seats
            experienced_only = new_count >= required / 2
        else:
            # fully staffed: only alternates can be added
            role_code = 'ALTERNATE'
            experienced_only = False

        print(f'\nSeats filled: {filled} of {required}'
              f'  |  Adding: {role_code}')
        if role_code == 'ASSESSOR' and experienced_only:
            print('  Half of the seats are first time volunteers; '
                  'only experienced volunteers are shown.')

        # active volunteers not already on this assessment, flagged
        # as first time when missing from experienced_volunteers
        query = (
            'SELECT v.volunteer_id, '
            f"CONCAT({VOLUNTEER_NAME}, "
            "IF(ev.volunteer_id IS NULL, ' (first time)', '')) "
            'FROM volunteer v '
            'LEFT JOIN experienced_volunteers ev '
            'ON ev.volunteer_id = v.volunteer_id '
            'WHERE v.active_ind = TRUE '
            'AND v.volunteer_id NOT IN (SELECT volunteer_id '
            'FROM assessment_assignment WHERE assessment_id = %s) '
            'AND NOT EXISTS ( '
            '  SELECT 1 FROM assessment_assignment other_aa '
            '  JOIN assessment other_a '
            '    ON other_a.assessment_id = other_aa.assessment_id '
            '  WHERE other_aa.volunteer_id = v.volunteer_id '
            '    AND other_a.assessment_dt = ( '
            '      SELECT assessment_dt FROM assessment '
            '      WHERE assessment_id = %s '
            '    ) '
            ') '
        )
        if experienced_only:
            query += 'AND ev.volunteer_id IS NOT NULL '
        query += 'ORDER BY v.last_name, v.pref_name'

        try:
            volunteer = prompts.select_row(cursor, query, role_code.lower(),
                                           (assessment_id, assessment_id))
        except prompts.Cancelled:
            # nothing picked yet: cancel the whole action
            if not added:
                raise
            # otherwise stop adding and keep the volunteers already
            # picked; they are still saved only after the confirm below
            break
        cursor.execute(
            'INSERT INTO assessment_assignment '
            '(assessment_id, volunteer_id, role_code) '
            'VALUES (%s, %s, %s)',
            (assessment_id, volunteer[0], role_code)
        )
        added.append(f'{volunteer[1]} ({role_code})')

        adding = prompts.yes_no('Add another volunteer?')

    # final team counts for the summary
    required, filled, new_count, lead_count = get_staffing(
        cursor, assessment_id
    )
    summary = {
        'Assessment': assessment[1],
        'Added': '; '.join(added),
        'Seats filled': f'{filled} of {required}'
    }
    # warn (but allow) when first time volunteers outnumber
    # experienced ones
    if new_count > filled - new_count:
        summary['WARNING'] = ('more first time than experienced '
                              'volunteers assigned')

    # cancel unless user confirms
    prompts.confirm('Save assignments', summary)
    return f'{len(added)} assignment(s) saved.'


def drop_assignments(name: str, cursor):
    '''
    Prompt for an assessment that is not completed and a volunteer
    on its team, confirm, and drop them. A dropped lead must be
    replaced by an experienced assessor already on the team; any
    open seat is filled by the first eligible alternate. Raises
    Cancelled if the user cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - who was dropped and any team changes
    '''
    display_support.display_page(name, to_upper=True)

    assessment = select_open_assessment(cursor)
    assessment_id = assessment[0]

    # team listed lead first, then assessors, then alternates
    member = prompts.select_row(
        cursor,
        f"SELECT aa.assignment_id, CONCAT({VOLUNTEER_NAME}, "
        "' (', aa.role_code, ')') "
        'FROM assessment_assignment aa '
        'JOIN volunteer v ON v.volunteer_id = aa.volunteer_id '
        'WHERE aa.assessment_id = %s '
        "ORDER BY FIELD(aa.role_code, 'LEAD', 'ASSESSOR', 'ALTERNATE'), "
        'v.last_name',
        'volunteer to drop',
        (assessment_id,)
    )
    # select_row only returns (id, display_name), so look up the role
    cursor.execute(
        'SELECT role_code FROM assessment_assignment '
        'WHERE assignment_id = %s',
        (member[0],)
    )
    role_code = cursor.fetchone()[0]

    # cancel unless user confirms
    prompts.confirm('Drop assignment', {
        'Assessment': assessment[1],
        'Drop': member[1]
    })

    notes = drop_assignment(cursor, assessment_id, member[0], role_code)
    return '\n'.join([f'{member[1]} dropped.'] + notes)


# ---------------------------------------------------------------------
# Volunteer manager
# ---------------------------------------------------------------------

def add_volunteer(name: str, cursor):
    '''
    Prompt for volunteer details, confirm with the user, and insert
    a new volunteer. Preferred name falls back to first name when
    left blank. Raises Cancelled if the user cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message with the new volunteer id
    '''
    display_support.display_page(name, to_upper=True)

    # max lengths match the volunteer column sizes
    first_name = prompts.prompt_text('First name', 45)
    pref_name = prompts.prompt_text('Preferred name', 45, required=False)
    # pref_name is NOT NULL, so use first name when left blank
    if pref_name is None:
        pref_name = first_name
    last_name = prompts.prompt_text('Last name', 45)
    email = prompts.prompt_email('Email', 254)
    phone = prompts.prompt_text('Phone (xxx-xxx-xxxx)', 30)
    council = select_council(cursor)
    # experience before joining this system (check_experience)
    experience = prompts.select_option([
        ('EXPERIENCED', 'Experienced (has assessed before)'),
        ('NEW', 'New (first time assessor)')
    ], 'experience level')

    # cancel unless user confirms
    prompts.confirm('New volunteer', {
        'Name': f'{first_name} {last_name}',
        'Preferred name': pref_name,
        'Email': email,
        'Phone': phone,
        'Council': council[1],
        'Experience': experience[1]
    })

    # active_ind and added_dt use their column defaults
    cursor.execute(
        'INSERT INTO volunteer (council_num, first_name, pref_name, '
        'last_name, email, phone, experience_baseline) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s)',
        (council[0], first_name, pref_name, last_name, email, phone,
         experience[0])
    )
    return f'Volunteer added (id {cursor.lastrowid}).'


def update_volunteer_info(name: str, cursor):
    '''
    Prompt for a volunteer and one contact/name field to change,
    then save the new value once the user confirms. Raises Cancelled
    if the user cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message naming the updated field
    '''
    display_support.display_page(name, to_upper=True)

    # inactive volunteers are listed too, but flagged
    volunteer = prompts.select_row(
        cursor,
        f"SELECT v.volunteer_id, CONCAT({VOLUNTEER_NAME}, "
        "IF(v.active_ind, '', ' (inactive)')) "
        'FROM volunteer v ORDER BY v.last_name, v.pref_name',
        'volunteer'
    )
    label = update_field(cursor, 'volunteer', 'volunteer_id',
                         volunteer[0], {
                             'first_name': ('First name', 45),
                             'pref_name': ('Preferred name', 45),
                             'last_name': ('Last name', 45),
                             'email': ('Email', 254),
                             'phone': ('Phone', 30)
                         })
    return f'{volunteer[1]}: {label.lower()} updated.'


def deactivate_volunteer(name: str, cursor):
    '''
    Prompt for an active volunteer, warn which pending (not
    completed) assessments they will be dropped from, and once the
    user confirms, drop them from each and mark them inactive.
    Dropping a lead requires choosing a replacement lead. Raises
    Cancelled if the user cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - result message with any team changes
    '''
    display_support.display_page(name, to_upper=True)

    volunteer = prompts.select_row(
        cursor,
        f'SELECT v.volunteer_id, {VOLUNTEER_NAME} FROM volunteer v '
        'WHERE v.active_ind = TRUE ORDER BY v.last_name, v.pref_name',
        'volunteer'
    )

    # pending assignments that will be dropped
    cursor.execute(
        'SELECT aa.assessment_id, aa.assignment_id, aa.role_code, '
        "CONCAT(a.assessment_dt, ' - ', c.camp_name, ' - ', "
        "p.program_name, ' (', aa.role_code, ')') "
        'FROM assessment_assignment aa '
        'JOIN assessment a ON a.assessment_id = aa.assessment_id '
        'JOIN camp c ON c.camp_id = a.camp_id '
        'JOIN program p ON p.program_id = a.program_id '
        "WHERE aa.volunteer_id = %s AND a.status <> 'COMPLETED' "
        'ORDER BY a.assessment_dt',
        (volunteer[0],)
    )
    pending = cursor.fetchall()

    # warn the user with the impacted assessments before confirming
    summary = {'Volunteer': volunteer[1]}
    if pending:
        print(f'\nWARNING: {volunteer[1]} will be dropped from '
              f'{len(pending)} pending assessment(s):')
        for assessment_id, assignment_id, role_code, description in pending:
            print(f'  - {description}')
        summary['Pending assessments dropped'] = len(pending)
    prompts.confirm('Deactivate volunteer', summary)

    # drop from each pending assessment, keeping teams staffed
    notes = []
    for assessment_id, assignment_id, role_code, description in pending:
        print(f'\n{description}')
        for note in drop_assignment(cursor, assessment_id,
                                    assignment_id, role_code):
            notes.append(f'  {description}: {note}')

    cursor.execute(
        'UPDATE volunteer SET active_ind = FALSE WHERE volunteer_id = %s',
        (volunteer[0],)
    )
    return '\n'.join([f'{volunteer[1]} deactivated.'] + notes)


def activate_volunteer(name: str, cursor):
    '''
    Prompt for an inactive volunteer, confirm with the user, and mark
    them active so they can be assigned again. Assignments dropped at
    deactivation are not restored. Raises Cancelled if the user
    cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message naming the volunteer
    '''
    display_support.display_page(name, to_upper=True)

    # only inactive volunteers can be activated
    volunteer = prompts.select_row(
        cursor,
        f"SELECT v.volunteer_id, CONCAT({VOLUNTEER_NAME}, ' (', "
        "v.email, ')') FROM volunteer v "
        'WHERE v.active_ind = FALSE ORDER BY v.last_name, v.pref_name',
        'inactive volunteer'
    )

    # cancel unless user confirms
    prompts.confirm('Activate volunteer', {'Volunteer': volunteer[1]})
    cursor.execute(
        'UPDATE volunteer SET active_ind = TRUE WHERE volunteer_id = %s',
        (volunteer[0],)
    )
    return f'{volunteer[1]} activated.'


# ---------------------------------------------------------------------
# Quick views
# ---------------------------------------------------------------------

# quick view menu option -> query against its database view
view_queries = {
    'overdue assessments': 'SELECT * FROM overdue_assessments',
    'scheduled assessments': ('SELECT * FROM scheduled_assessments '
                              'ORDER BY assessment_dt'),
    'volunteer activity report': 'SELECT * FROM volunteer_activity',
    'completed assessment history':
        'SELECT * FROM completed_assessment_history',
}


def show_view(name: str, cursor):
    '''
    Display the results of the database view behind a quick view
    menu option as a table. Read-only.

    Parameters:
        name (string) - quick view option name, key in view_queries
        cursor (mysql cursor object) - used to run the view query
    '''
    display_support.display_page(name, to_upper=True)
    cursor.execute(view_queries[name])
    rows = cursor.fetchall()
    headers = [col[0] for col in cursor.description]
    display_support.print_table(headers, rows)


# ---------------------------------------------------------------------
# Action command and control
# ---------------------------------------------------------------------

actions = {
    # quick views (all read-only, same display action)
    **{view: show_view for view in view_queries},
    # volunteer manager
    'add volunteer': add_volunteer,
    'update info': update_volunteer_info,
    'deactivate volunteer': deactivate_volunteer,
    'activate volunteer': activate_volunteer,
    # camp manager
    'add camp': add_camp,
    'update camp info': update_camp_info,
    'delete camp': delete_camp,
    # program manager
    'add program': add_program,
    'update program info': update_program_info,
    'delete program': delete_program,
    # assessment scheduler
    'schedule new': schedule_assessment,
    'modify assessment': modify_assessment,
    'cancel': cancel_assessment,
    # manage assignments
    'enter assignments': enter_assignments,
    'drop assignments': drop_assignments,
}


def run_action(name: str, cnx):
    '''
    Run an action inside one transaction: commit if it finishes,
    roll back if it is cancelled or the database rejects it.

    Parameters:
        name (string) - name of the action to run, key in actions dict
        cnx (mysql connection object) - open database connection
    '''
    print()
    # fall back to placeholder if no action is mapped to this name
    action = actions.get(name, not_implemented)
    # cursor is closed automatically when the with block ends
    with cnx.cursor() as cursor:
        try:
            message = action(name, cursor)
            # only commit once the action finishes without errors
            cnx.commit()
            if message:
                print(f'\n{message}')
        # user cancelled, undo anything the action ran
        except prompts.Cancelled:
            cnx.rollback()
            print('\nCancelled.')
        # database rejected a query (e.g. constraint/trigger), undo
        # and report
        except mysql.connector.Error as err:
            cnx.rollback()
            print(f'\nDatabase error: {err.msg}')
        except Exception:
            # Do not leave pending changes after unexpected Python errors.
            cnx.rollback()
            raise
    # hold the result on screen before returning to the menu
    display_support.pause()
