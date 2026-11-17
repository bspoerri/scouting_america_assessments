# Window module

class Window:

    def __init__(self, name: str, window_options: list,
                 home_ind: bool = False, title: str = None):
        '''
        Create a menu window with numbered options.

        Parameters:
            name (string) - name of the page this window displays
            window_options (list) - option names shown to the user
            home_ind (bool) - True if this is the home page, which
                changes the 0 option from "return" to "exit"
            title (string) - heading for the window, defaults to name
        '''
        self.name = name
        # map option codes (starting at 1) to option names, 0 is
        # reserved for exit/return
        self.window_options = dict(enumerate(window_options, start=1))
        self.home_ind = home_ind
        # fall back to the page name if no title is given
        if title is None:
            self.title = name
        else:
            self.title = title

    def __str__(self):
        '''
        Build the text shown for this window: title, numbered
        options, and the exit/return instruction.

        Returns:
            string (string) - formatted window text
        '''
        string = f'{self.title.upper()}\n'
        # list each option with its selection code
        for code, option in self.window_options.items():
            string += f'\n {code}) {option}'
        # home page exits the program, other pages return to the
        # previous page
        string += f'\n\nEnter "0" to {"exit" if self.home_ind else "return"}'
        return string

    def get_selection(self):
        '''
        Loop until the user enters 0 or a valid option code and
        return it.

        Returns:
            action (int) - the selected option code
        '''
        while True:
            action = input('\nSelect option: ').strip()
            # accept 0 (exit/return) or any listed option code
            if action.isdigit() and (int(action) == 0
                                     or int(action) in self.window_options):
                return int(action)
            # re-prompt if input conditions are not met
            print('  Please enter a number from 0 to '
                  f'{len(self.window_options)}.')
