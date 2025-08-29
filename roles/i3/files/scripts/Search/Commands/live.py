from command import Command
import subprocess
import webbrowser
from Commands.dyflexis import Dyflexis

class Live(Command):
    @property
    def letter(self):
        return "l"

    @property
    def name(self):
        return "live"

    @property
    def is_optional(self):
        return False

    @property
    def must_be_first_character(self):
        return False

    @property
    def is_depended_on(self):
        return Dyflexis()

    @property
    def can_be_executed(self):
        return True

    @property
    def can_be_copied(self):
        return True

    @property
    def is_last_command(self):
        return True

    @property
    def can_type(self):
        return True

    def execute(self, text):
        url = "https://app.dyflexis.com/"
        if not text:
            text = "dyflexis"
        webbrowser.open_new_tab(url + text)
        return True

    def copy(self, text):
        if not text:
            text = "dyflexis"
        return "https://app.dyflexis.com/" + text

