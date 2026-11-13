# Window module

class Window:

    def __init__(self, name: str, window_options: list, home_ind: bool = False, title: str = None):

        self.name = name
        self.window_options = dict(enumerate(window_options, start=1))
        self.home_ind = home_ind
        if title is None:
            self.title = name
        else:
            self.title = title

    def __str__(self):
        string = f'{self.title.upper()}\n'
        for code, option in self.window_options.items():
            string += f'\n {code}) {option}'
        string += f'\n\nEnter "0" to {"exit" if self.home_ind else "return"}'
        return string

    def get_selection(self):
        '''
        Loop until the user enters 0 or a valid option code and return it.
        '''
        while True:
            action = input('\nSelect option: ').strip()
            if action.isdigit() and (int(action) == 0 or int(action) in self.window_options):
                return int(action)
            print(f'  Please enter a number from 0 to {len(self.window_options)}.')
