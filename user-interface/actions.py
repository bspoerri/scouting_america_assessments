# Module that controls all submenu actions available to users
#
# Every action has the signature  action(name, cursor) -> str | None
#   - Run queries with the cursor; do NOT commit/rollback
#     (run_action does that).
#   - Raise prompts.Cancelled to abort (prompts.* helpers do this
#     for you).
#   - Return an optional success message, shown after the commit
#     succeeds.
import display_support
import prompts
import mysql.connector


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


def add_camp(name: str, cursor):
    display_support.display_page(name, to_upper=True)
    # TODO: prompt for camp fields and INSERT INTO camp


def edit_camp(name: str, cursor):
    # TODO
    not_implemented(name)


def delete_camp(name: str, cursor):
    # TODO
    not_implemented(name)


def add_program(name: str, cursor):
    # TODO
    not_implemented(name)


def edit_program(name: str, cursor):
    # TODO
    not_implemented(name)


def delete_program(name: str, cursor):
    # TODO
    not_implemented(name)


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
    assessment_date = prompts.prompt_date('Assessment date')
    # matches check_required_assessors (>= 0)
    required_assessors = prompts.prompt_int(
        'Number of required assessors', minimum=0
    )

    # show summary using display names, cancel unless user confirms
    prompts.confirm('New assessment', {
        'Camp': camp[1],
        'Program': program[1],
        'Date': assessment_date,
        'Required assessors': required_assessors
    })

    # insert using ids, %s placeholders let the connector escape
    # values safely
    cursor.execute(
        'INSERT INTO assessment '
        '(camp_id, program_id, assessment_date, required_assessors) '
        'VALUES (%s, %s, %s, %s)',
        (camp[0], program[0], assessment_date, required_assessors)
    )
    # returns lastrowid which is built in attribute containing
    # auto-generated (incrementing) id
    return f'Assessment scheduled (id {cursor.lastrowid}).'


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
        'FROM assessment_assignment a '
        'JOIN volunteer v ON a.volunteer_id = v.volunteer_id '
        'WHERE a.assessment_id = %s',
        (assessment_id,)
    )
    return '; '.join(row[0] for row in cursor.fetchall()) or 'none'


def modify_assessment(name: str, cursor):
    '''
    Prompt for an assessment that has not been completed, let the
    user pick which fields to change (camp, program, date, required
    assessors), show old -> new values, and update the assessment
    once the user confirms. Raises Cancelled if the user cancels at
    the assessment or field menu, or declines to save.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message with the updated id
    '''
    display_support.display_page(name, to_upper=True)

    # only open assessments can be modified
    assessment = prompts.select_row(
        cursor,
        "SELECT a.assessment_id, "
        "CONCAT(a.assessment_date, ' - ', c.camp_name, ' - ', "
        "p.program_name) "
        'FROM assessment a '
        'JOIN camp c ON c.camp_id = a.camp_id '
        'JOIN program p ON p.program_id = a.program_id '
        'WHERE a.completed_ind = FALSE '
        'ORDER BY a.assessment_date DESC',
        'assessment'
    )
    assessment_id = assessment[0]

    # load current values (ids are saved, names are displayed)
    cursor.execute(
        'SELECT a.camp_id, c.camp_name, a.program_id, p.program_name, '
        'a.assessment_date, a.required_assessors '
        'FROM assessment a '
        'JOIN camp c ON c.camp_id = a.camp_id '
        'JOIN program p ON p.program_id = a.program_id '
        'WHERE a.assessment_id = %s',
        (assessment_id,)
    )
    camp_id, camp_name, program_id, program_name, a_date, required = \
        cursor.fetchone()

    # menu labels for each editable column
    labels = {
        'camp_id': 'Camp',
        'program_id': 'Program',
        'assessment_date': 'Date',
        'required_assessors': 'Required assessors'
    }
    # values saved to the db, and the text shown to the user
    current = {'camp_id': camp_id, 'program_id': program_id,
               'assessment_date': a_date, 'required_assessors': required}
    current_shown = {'camp_id': camp_name, 'program_id': program_name,
                     'assessment_date': a_date,
                     'required_assessors': required}
    # copies the user edits; current stays as the original values
    new = dict(current)
    new_shown = dict(current_shown)

    editing = True
    while editing:
        display_support.display_page(f'{name.upper()}\n\n{assessment[1]}')
        # * marks fields changed but not yet saved
        options = [
            (col, f'{label}: {new_shown[col]}'
                  + (' *' if new[col] != current[col] else ''))
            for col, label in labels.items()
        ]
        options.append(('save', 'Review and save changes'))
        # 0 here cancels the whole action
        column = prompts.select_option(options, 'field to update')[0]
        if column == 'save':
            editing = False

        # 0 inside a camp/program list returns to the field menu
        try:
            if column == 'camp_id':
                new[column], new_shown[column] = prompts.select_row(
                    cursor,
                    'SELECT camp_id, camp_name FROM camp '
                    'ORDER BY camp_name',
                    'camp'
                )
            elif column == 'program_id':
                new[column], new_shown[column] = prompts.select_row(
                    cursor,
                    'SELECT program_id, program_name FROM program '
                    'ORDER BY program_name',
                    'program'
                )
            elif column == 'assessment_date':
                new[column] = new_shown[column] = prompts.prompt_date(
                    'New assessment date'
                )
            else:
                new[column] = new_shown[column] = prompts.prompt_int(
                    'New number of required assessors', minimum=0
                )
        except prompts.Cancelled:
            pass

    # quick check to see if changes made
    changed = [col for col in labels if new[col] != current[col]]
    if not changed:
        return 'No changes made.'

    # compare old -> new for changed fields
    summary = {
        labels[col]: f'{current_shown[col]} -> {new_shown[col]}'
        for col in changed
    }
    # a new camp, program, or date reschedules the assessment
    if set(changed) - {'required_assessors'}:
        # generate list of volunteers to notify for material change
        summary['Assessors to notify'] = volunteers_to_notify(
            cursor, assessment_id
        )

    # cancel unless user confirms
    prompts.confirm(f'Update assessment {assessment_id}', summary)

    # unchanged columns are rewritten with their current value
    cursor.execute(
        'UPDATE assessment '
        'SET camp_id = %s, program_id = %s, assessment_date = %s, '
        'required_assessors = %s '
        'WHERE assessment_id = %s',
        (new['camp_id'], new['program_id'], new['assessment_date'],
         new['required_assessors'], assessment_id)
    )
    return f'Assessment {assessment_id} updated.'


def cancel_assessment(name: str, cursor):
    '''
    Prompt for an assessment that has not been completed, confirm
    with the user, and delete it along with its team assignments.
    Raises Cancelled if the user cancels at any prompt.

    Parameters:
        name (string) - name of the action, used as the page heading
        cursor (mysql cursor object) - object used to run queries
            inside the current transaction

    Returns:
        message (string) - success message with the cancelled id
    '''
    display_support.display_page(name, to_upper=True)

    # select_row expects exactly (id, display_name) so concat details
    #   for display
    # TODO: implement as views
    assessment = prompts.select_row(
        cursor,
        "SELECT a.assessment_id, "
        "CONCAT(a.assessment_date, ' - ', c.camp_name, ' - ', "
        "p.program_name) "
        'FROM assessment a '
        'JOIN camp c ON c.camp_id = a.camp_id '
        'JOIN program p ON p.program_id = a.program_id '
        'WHERE a.completed_ind = FALSE '
        'ORDER BY a.assessment_date DESC',
        'assessment'
    )

    # show summary with assigned volunteers, cancel unless user confirms
    prompts.confirm('Cancel assessment', {
        'Assessment': assessment[1],
        'Assessors to notify': volunteers_to_notify(cursor, assessment[0])
    })

    # assignments reference the assessment (no ON DELETE CASCADE),
    # so delete them first, both run in the same transaction
    cursor.execute(
        'DELETE FROM assessment_assignment WHERE assessment_id = %s',
        (assessment[0],)
    )
    cursor.execute(
        'DELETE FROM assessment WHERE assessment_id = %s',
        (assessment[0],)
    )
    return f'Assessment {assessment[0]} cancelled.'


def add_assessors(name: str, cursor):
    # TODO
    not_implemented(name)


def remove_assessors(name: str, cursor):
    # TODO
    not_implemented(name)


def add_volunteer(name: str, cursor):
    # TODO
    not_implemented(name)


def edit_volunteer(name: str, cursor):
    # TODO
    not_implemented(name)


def delete_volunteer(name: str, cursor):
    # TODO
    not_implemented(name)


actions = {
    'add camp': add_camp,
    'edit camp': edit_camp,
    'delete camp': delete_camp,
    'add program': add_program,
    'edit program': edit_program,
    'delete program': delete_program,
    'schedule new': schedule_assessment,
    'modify existing': modify_assessment,
    'cancel existing': cancel_assessment,
    'add assessors': add_assessors,
    'remove assessors': remove_assessors,
    'add volunteer': add_volunteer,
    'edit volunteer': edit_volunteer,
    'delete volunteer': delete_volunteer
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
    # hold the result on screen before returning to the menu
    display_support.pause()
