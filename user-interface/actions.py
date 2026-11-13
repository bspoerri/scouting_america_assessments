# Module that controls all submenu actions available to users
import display_support

def not_implemented(name: str):
    print(f'\n"{name}" is not implemented yet.')

def add_camp(name: str):
    page_title = name.upper()
    display_support.display_page(page_title)
    # TODO: prompt for camp fields and INSERT INTO camp
   

def edit_camp(name: str):
    # TODO
    not_implemented(name)

def delete_camp(name: str):
    # TODO
    not_implemented(name)

def add_program(name: str):
    # TODO
    not_implemented(name)

def edit_program(name: str):
    # TODO
    not_implemented(name)

def delete_program(name: str):
    # TODO
    not_implemented(name)

def schedule_assessment(name: str):
    # TODO
    not_implemented(name)

def modify_assessment(name: str):
    # TODO
    not_implemented(name)

def cancel_assessment(name: str):
    # TODO
    not_implemented(name)

def add_volunteer(name: str):
    # TODO: prompt for volunteer fields and INSERT INTO volunteer
    not_implemented(name)

def edit_volunteer(name: str):
    # TODO
    not_implemented(name)

def delete_volunteer(name: str):
    # TODO
    not_implemented(name)


actions = {
    'add camp': add_camp,
    'edit camp': edit_camp,
    'delete camp': delete_camp,
    'add program': add_program,
    'edit program': edit_program,
    'delete program': delete_program,
    'schedule assessment': schedule_assessment,
    'modify assessment': modify_assessment,
    'cancel assessment': cancel_assessment,
    'add volunteer': add_volunteer,
    'edit volunteer': edit_volunteer,
    'delete volunteer': delete_volunteer,
}


def run_action(name: str):
    actions.get(name, not_implemented)(name)
    input('\nPress Enter to continue...')
