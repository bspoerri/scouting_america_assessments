import os
import subprocess
import time


def clear_screen():
    """Clear the terminal window."""
    command = 'cls' if os.name == 'nt' else 'clear'
    subprocess.run(command, shell=True, check=False)


def print_chars(message: str, speed: float = 0.01):
    """Print text with a typewriter effect."""
    print("\n")

    for char in message:
        print(char, end='', flush=True)
        time.sleep(speed)

    print("\n")


def display_greeting(greeting_text: str):
    """Display the application's welcome message."""
    clear_screen()

    text = greeting_text

    welcome = (
        "_" * (len(text) + 4) + "\n"
        + "|" + " " * (len(text) + 2) + "|" + "\n"
        + "|" + " " + text + " " + "|" + "\n"
        + "|" + " " * (len(text) + 2) + "|" + "\n"
        + "‾" * (len(text) + 4) + "\n"
    )

    print_chars(welcome, 0.01)
    time.sleep(0.5)


def display_page(page_text: str, to_upper: bool = False):
    """Clear the terminal and display a page."""
    if to_upper:
        page_text = page_text.upper()

    clear_screen()
    print(page_text)


def print_table(headers: list, rows: list):
    """Display query results in an aligned text table."""
    if not rows:
        print('\n  No records found.')
        return

    rows = [
        ['N/A' if val is None else str(val) for val in row]
        for row in rows
    ]

    headers = [h.replace('_', ' ').title() for h in headers]

    widths = [
        max(len(h), *(len(row[i]) for row in rows))
        for i, h in enumerate(headers)
    ]

    print()
    print('  '.join(h.ljust(w) for h, w in zip(headers, widths)))
    print('  '.join('-' * w for w in widths))

    for row in rows:
        print('  '.join(val.ljust(w) for val, w in zip(row, widths)))

    count = len(rows)
    print(f'\n({count} row{"" if count == 1 else "s"})')


def pause(message: str = 'Press Enter to continue...'):
    """Wait for the user to press Enter."""
    input(f'\n{message}')
