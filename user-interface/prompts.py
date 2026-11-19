# Module with functions that direct users to provide input
from datetime import date


class Cancelled(Exception):
    '''
    Custom exception raised by any prompt when the user cancels
    the current action.
    '''


def select_row(cursor, query: str, label: str, params: tuple = ()):
    '''
    Run a query returning (id, display_name) rows, show them as a
    numbered list, and return the chosen row. Raises Cancelled if
    the user enters 0 or there are no rows.

    Parameters:
        cursor (mysql connection object) - object used to interact
            with mysql connection
        query (string) - query run to generate list of options
        label (string) - name of the field being selected
        params (tuple) - values for any %s placeholders in query

    Returns:
        row (tuple) - (id, display_name)
    '''
    # execute query and store results
    cursor.execute(query, params)
    return select_option(cursor.fetchall(), label)


def select_option(rows: list, label: str):
    '''
    Show (id, display_name) rows as a numbered list and return the
    chosen row. Raises Cancelled if the user enters 0 or there are
    no rows.

    Parameters:
        rows (list) - (id, display_name) tuples to choose from
        label (string) - name of the field being selected

    Returns:
        row (tuple) - (id, display_name)
    '''
    # if there are no options cancel with note to user
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
    date that is not after today.

    Parameters:
        label (string) - text shown to the user describing the date
        allow_past (bool) - if True, today and earlier dates are
            accepted

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
        # re-prompt unless the date is in the future (matches the
        # DDL "future" check: assessment_dt > created_dt)
        if not allow_past and dt <= date.today():
            print('  Date must be after today.')
            continue
        return dt


def yes_no(question: str):
    '''
    Ask a yes/no question until the user enters y or n.

    Parameters:
        question (string) - question shown to the user

    Returns:
        answer (bool) - True for "y", False for "n"
    '''
    while True:
        answer = input(f'\n{question} (y/n): ').strip().lower()
        if answer in ('y', 'n'):
            return answer == 'y'
        # re-prompt if input conditions are not met
        print('  Please enter y or n.')


def prompt_int(label: str, minimum: int = 0, maximum: int = None):
    '''
    Prompt the user until a whole number between minimum and maximum
    (inclusive) is entered and return it.

    Parameters:
        label (string) - text shown to the user describing the number
        minimum (int) - smallest value accepted
        maximum (int) - largest value accepted; None means no limit

    Returns:
        raw (int) - the number entered by the user
    '''
    while True:
        raw = input(f'{label}: ').strip()
        # check, then enforce the bounds
        if (raw.isdigit() and int(raw) >= minimum
                and (maximum is None or int(raw) <= maximum)):
            return int(raw)
        # re-prompt if input conditions are not met
        if maximum is None:
            print(f'  Please enter a whole number {minimum} or greater.')
        else:
            print(f'  Please enter a whole number from {minimum} '
                  f'to {maximum}.')


def prompt_text(label: str, max_len: int, required: bool = True):
    '''
    Prompt the user until text no longer than max_len is entered and
    return it. Required fields re-prompt on blank input; optional
    fields return None when left blank so NULL is stored.

    Parameters:
        label (string) - text shown to the user describing the field
        max_len (int) - longest value accepted (matches column size)
        required (bool) - if False, blank input is accepted

    Returns:
        text (string or None) - the text entered by the user
    '''
    while True:
        hint = '' if required else ' (blank for none)'
        text = input(f'{label}{hint}: ').strip()
        # optional fields store NULL instead of an empty string
        if not text and not required:
            return None
        if not text:
            print('  This field is required.')
            continue
        # re-prompt instead of letting the db reject a long value
        if len(text) > max_len:
            print(f'  Please enter {max_len} characters or fewer.')
            continue
        return text


def prompt_email(label: str, max_len: int):
    '''
    Prompt the user until a basic name@domain email is entered and
    return it in lowercase.

    Parameters:
        label (string) - text shown to the user describing the email
        max_len (int) - longest value accepted (matches column size)

    Returns:
        email (string) - the email entered by the user
    '''
    while True:
        email = prompt_text(label, max_len).lower()
        # light check: one "@" with text before it and a "." after it
        local, at, domain = email.partition('@')
        if at and local and '.' in domain and '@' not in domain:
            return email
        print('  Please enter a valid email (name@domain.com).')


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