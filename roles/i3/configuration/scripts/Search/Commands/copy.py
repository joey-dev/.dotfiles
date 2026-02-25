from command import Command
import subprocess

class Copy(Command):
    @property
    def letter(self):
        return "c"

    @property
    def name(self):
        return "copy"

    @property
    def is_optional(self):
        return True

    @property
    def must_be_first_character(self):
        return True

    @property
    def is_depended_on(self):
        return None

    @property
    def can_be_executed(self):
        return False

    @property
    def can_be_copied(self):
        return False

    @property
    def can_type(self):
        return False

    @property
    def is_last_command(self):
        return False

    def execute(self, text):
        return False

    def copy(self, text):
        return False
