import os
import subprocess
import time


def clear_screen():
    # clear twice to ensure clear window
    for i in range(2):
        subprocess.run('cls' if os.name == 'nt' else 'clear', shell=True)


def print_chars(message: str, speed: float=0.03):
    print("\n")
    for char in message:
        print(char, end='', flush=True)
        time.sleep(speed)
    print("\n")


def display_greeting(greeting_text: str):
    '''
    This function generates the text for the greeting display when the application is opened.
    '''
    clear_screen()
    text = greeting_text
    welcome = "_" * (len(text) + 4) + "\n" + \
              "|" + " " * (len(text) + 2) + "|" + "\n" + \
              "|" + " " + text + " " + "|" + "\n" + \
              "|" + " " * (len(text) + 2) + "|" + "\n" + \
              "‾" * (len(text) + 4) + "\n"
    print_chars(welcome, 0.025)
    time.sleep(0.5)


def display_page(page_text: str):
    clear_screen()
    print(page_text)


