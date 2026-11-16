# Driver module for Scouting Assessments CLI Tool
import display_support
import pages
from actions import run_action
from window import Window
from db_connection import get_connection


def main(cnx):
    '''
    Run the main menu loop. Pages are kept on a stack: selecting a
    page pushes it, entering 0 pops back, and the program ends
    when the stack is empty.

    Parameters:
        cnx (mysql connection object) - open database connection
            passed to each action
    '''
    # display greeting on boot-up
    display_support.display_greeting("SCOUT ASSESSMENT MANAGER")

    # page navigate with a stack
    stack = ['home']

    # continue to run program while stack is not empty
    while stack:
        # active page is last pushed to stack
        page = stack[-1]
        # Use Window class to create a window object for currect page
        window = Window(
            name=page,
            window_options=pages.page_dict[page],
            home_ind=(len(stack) == 1),
            title=' > '.join(stack),
        )
        display_support.display_page(window)
        # get user command for the current page
        cmd_code = window.get_selection()
        # pop top page if user selected 0 (universal exit/return code)
        if cmd_code == 0:
            stack.pop()
            continue
        # look up the page or action name for the selected code
        next_page = window.window_options[cmd_code]

        # if next page is a window, add it to the stack
        if next_page in pages.page_dict:
            stack.append(next_page)
        # run command, theses are not windows
        else:
            run_action(next_page, cnx)

    # display goodbye once runtime condition is no longer met
    display_support.print_chars('Goodbye!')


if __name__ == '__main__':
    cnx = get_connection()
    if cnx is None:
        raise SystemExit(1)
    try:
        main(cnx)
    except (KeyboardInterrupt, EOFError):
        print('\nGoodbye!')
    finally:
        cnx.close()
