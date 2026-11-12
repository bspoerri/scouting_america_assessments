# Window module

class Window():

    def __init__(self, name: str, options: list=None):

        self.name = name

        if options is None:
            self.options = []
        else:
            self.options = options

    def __str__(self):
        string = f'{self.name.upper()}\n' 
        for i in range(len(self.options)):
            string = string + f'\n {i}) {self.options[i]}'
        print(string)

