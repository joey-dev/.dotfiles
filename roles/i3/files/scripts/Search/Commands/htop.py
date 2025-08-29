from command import Command
import subprocess
from Commands.system import System

class HtopCommand(Command):
    @property
    def letter(self):
        return "h"

    @property
    def name(self):
        return "htop"

    @property
    def is_optional(self):
        return False

    @property
    def must_be_first_character(self):
        return False

    @property
    def is_depended_on(self):
        return System()

    @property
    def can_be_executed(self):
        return True

    @property
    def can_be_copied(self):
        return True

    @property
    def can_type(self):
        return False

    @property
    def is_last_command(self):
        return True

    def execute(self, text):
        subprocess.Popen(["xterm", "-hold", "-e", "htop"])
        return True

    def copy(self, text):
        return "xterm -hold -e htop"
