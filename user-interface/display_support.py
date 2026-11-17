import os
import subprocess
import time


def clear_screen():
    '''
    Clear the terminal window on Windows ("cls") or Mac/Linux ("clear").
    '''
    # clear twice to ensure clear window
    for i in range(2):
        subprocess.run('cls' if os.name == 'nt' else 'clear', shell=True)


def print_chars(message: str, speed: float=0.03):
    '''
    Print a message one character at a time for a typing effect.

    Parameters:
        message (string) - text to print
        speed (float) - seconds to wait between characters
    '''
    print("\n")
    for char in message:
        # flush so each character appears immediately instead of
        # buffering
        print(char, end='', flush=True)
        time.sleep(speed)
    print("\n")


def display_greeting(greeting_text: str):
    '''
    Clear the screen and display the greeting text inside a box
    when the application is opened.

    Parameters:
        greeting_text (string) - text shown inside the greeting box
    '''
    clear_screen()
    text = greeting_text
    # build a box sized to the text: top border, padding, text,
    # padding, bottom border
    welcome = "_" * (len(text) + 4) + "\n" + \
              "|" + " " * (len(text) + 2) + "|" + "\n" + \
              "|" + " " + text + " " + "|" + "\n" + \
              "|" + " " * (len(text) + 2) + "|" + "\n" + \
              "‾" * (len(text) + 4) + "\n"
    print_chars(welcome, 0.025)
    # brief hold so the greeting is visible before the first page loads
    time.sleep(0.5)


def display_page(page_text: str, to_upper: bool = False):
    '''
    Clear the screen and print the page text.

    Parameters:
        page_text (string or Window) - content to display
        to_upper (bool) - if True, convert the text to uppercase
    '''
    if to_upper:
        page_text = page_text.upper()
    clear_screen()
    print(page_text)


def pause(message: str = 'Press Enter to continue...'):
    '''
    Wait for the user to press Enter before moving on.

    Parameters:
        message (string) - prompt shown while waiting
    '''
    input(f'\n{message}')

