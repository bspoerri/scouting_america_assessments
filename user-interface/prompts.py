# Module with functions that direct users to provide input
from datetime import date


class Cancelled(Exception):
    '''
    Custom exception raised by any prompt when the user cancels
    the current action.
    '''


def select_row(cursor, query: str, label: str):
    '''
    Run a query returning (id, display_name) rows, show them as a
    numbered list, and return the chosen row. Raises Cancelled if
    the user enters 0 or there are no rows.

    Parameters:
        cursor (mysql connection object) - object used to interact
            with mysql connection
        query (string) - query run to generate list of options
        label (string) - name of the field being selected

    Returns:
        row (tuple) - (id, display_name)
    '''
    # execute query and store results
    cursor.execute(query)
    rows = cursor.fetchall()
    # if query returns no options cancel with note to user
    if not rows:
        print(f'\nNo {label}s found.')
        raise Cancelled
    # otherwise, prompt user to make a selection
    print(f'\nSelect a {label}:')
    # assume query returns the selectable field values and their db id
    for idx, (id, display_name) in enumerate(rows, start=1):
        print(f' {idx}) {display_name}')
    while True:
        choice = input('\nEnter number (0 to cancel): ').strip()
        if choice.isdigit() and (0 <= int(choice) <= len(rows)):
            if int(choice) == 0:
                raise Cancelled
            # adjust index for retrieval
            return rows[int(choice) - 1]
        # re-prompt if input conditions are not met
        print(f'  Please enter a number from 0 to {len(rows)}.')


def prompt_date(label: str, allow_past: bool = False):
    '''
    Prompt the user until a valid YYYY-MM-DD date is entered and
    return it. Re-prompts on bad formatting or, unless allowed, a
    date in the past.

    Parameters:
        label (string) - text shown to the user describing the date
        allow_past (bool) - if True, dates before today are accepted

    Returns:
        dt (datetime.date) - the date entered by the user
    '''
    while True:
        dt_txt = input(f'\n{label} (YYYY-MM-DD): ').strip()
        try:
            # convert string to date
            dt = date.fromisoformat(dt_txt)
        # re-prompt if string is not a valid ISO date
        except ValueError:
            print('  Invalid date format.')
            continue
        # re-prompt if past dates are not allowed
        if not allow_past and dt < date.today():
            print('  Date cannot be in the past.')
            continue
        return dt


def prompt_int(label: str, minimum: int = 0):
    '''
    Prompt the user until a whole number greater than or equal to
    minimum is entered and return it.

    Parameters:
        label (string) - text shown to the user describing the number
        minimum (int) - smallest value accepted

    Returns:
        raw (int) - the number entered by the user
    '''
    while True:
        raw = input(f'{label}: ').strip()
        # check, then enforce the minimum
        if raw.isdigit() and int(raw) >= minimum:
            return int(raw)
        # re-prompt if input conditions are not met
        print(f'  Please enter a whole number {minimum} or greater.')


def confirm(title: str, fields: dict):
    '''
    Show a summary of the entered fields and ask the user to save.
    Raises Cancelled on anything but "y".

    Parameters:
        title (string) - heading printed above the summary
        fields (dict) - field labels mapped to the values entered
    '''
    print(f'\n{title}:')
    # pad labels to the longest one so values line up in a column
    width = max(len(k) for k in fields) + 1
    for key, value in fields.items():
        print(f'  {key + ":":<{width}} {value}')
    # cancel unless the user explicitly confirms
    if input('\nSave? (y/n): ').strip().lower() != 'y':
        raise Cancelled
