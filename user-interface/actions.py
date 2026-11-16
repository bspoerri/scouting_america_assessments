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
        'camp',
    )
    program = prompts.select_row(
        cursor,
        'SELECT program_id, program_name FROM program '
        'ORDER BY program_name',
        'program',
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
        'Required assessors': required_assessors,
    })

    # insert using ids, %s placeholders let the connector escape
    # values safely
    cursor.execute(
        'INSERT INTO assessment '
        '(camp_id, program_id, assessment_date, required_assessors) '
        'VALUES (%s, %s, %s, %s)',
        (camp[0], program[0], assessment_date, required_assessors),
    )
    # returns lastrowid which is built in attribute containing
    # auto-generated id
    return f'Assessment scheduled (id {cursor.lastrowid}).'


def modify_assessment(name: str, cursor):
    # TODO
    not_implemented(name)


def cancel_assessment(name: str, cursor):
    # TODO
    not_implemented(name)


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
    'delete volunteer': delete_volunteer,
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
