import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
import os
import subprocess
import importlib.util
from command import Command
import pyperclip

class SuggestionWindow(Gtk.Window):
    def __init__(self):
        self.all_commands_cache = None
        self.all_commands_by_letter_cache = {}
        self.all_commands_by_depdency_letter_cache = {}
        self.history_input_field = None
        self.command_tree_by_letter = {}
        self.current_suggestions = []
        self.last_command_file = "history.txt"

        Gtk.Window.__init__(self, title="Suggestion Menu")
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG) # Hint to WM that this is a dialog
        self.set_decorated(False) # Remove window decorations for a cleaner look

        # Create a vertical box to hold the input field and suggestion list
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        # Create the input field
        self.entry = Gtk.Entry()
        self.entry.connect("changed", self.on_text_changed)
        self.entry.connect("activate", self.on_enter_pressed)
        self.connect("key-press-event", self.on_key_press)
        vbox.pack_start(self.entry, False, False, 0)

        # Create the suggestion list (using a ListStore and TreeView for simplicity)
        self.liststore = Gtk.ListStore(str)
        self.suggestion_list = Gtk.TreeView(model=self.liststore)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Suggestions", renderer, text=0)
        self.suggestion_list.append_column(column)
        vbox.pack_start(self.suggestion_list, True, True, 0)

        self.suggestion_list.connect("row-activated", self.on_suggestion_selected)

        self.load_starting_commands()

    def load_starting_commands(self):
        commands = self.all_commands()
        command_list = []
        history_command = None

        with open(self.last_command_file, "r") as file:
            first_line = file.readline().strip()
            if first_line:
                self.history_input_field = first_line.split(" ")[-1]
                history_command = self.find_command_by_command_string(first_line.split(" ")[0]).get('command')

        if history_command:
            command_list.append(history_command)

        for command_key in commands:
            command = commands[command_key]["command"]
            command_list.append(command)

        self.update_suggestions(command_list)

    def find_command_by_command_string(self, command_string):
        current_level = self.command_tree_by_letter
        results = []

        loop_count = 0
        for char in command_string:
            if char in current_level:
                loop_count += 1
                current_command = current_level[char]["command"]
                if current_command.is_optional:
                    continue;
                current_object = current_level[char]
                current_level = current_level[char].get('children')
                if current_level is None:
                    return []
                if loop_count == len(command_string):
                    return current_object

        print("Nothing found for that search string")
        return []

    def find_children_by_command_string(self, command_string):
        return self.find_command_by_command_string(command_string).get('children', {})

    def all_commands(self):
        if (self.command_tree_by_letter):
            return self.command_tree_by_letter

        commands_dir = "Commands"
        command_list = []

        if not os.path.isdir(commands_dir):
            print(f"Error: {commands_dir} directory not found.")
            return []

        for filename in os.listdir(commands_dir):
            if filename.endswith(".py"):
                filepath = os.path.join(commands_dir, filename)
                module_name = filename[:-3]

                spec = importlib.util.spec_from_file_location(module_name, filepath)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                all_commands = []
                for name in dir(module):
                    obj = getattr(module, name)
                    if isinstance(obj, type) and issubclass(obj, Command) and obj != Command:
                        all_commands.append(obj())

                current_loop = 0
                while all_commands:
                    if current_loop > 1000:
                        break
                    current_loop += 1

                    command = all_commands.pop(0)
                    did_add_command = False

                    for command_found_key in self.command_tree_by_letter:
                        command_found = self.command_tree_by_letter[command_found_key]
                        if str(command_found.get("command")) == str(command.is_depended_on):
                            self.command_tree_by_letter[command_found.get("command").letter]["children"][command.letter] = {
                                "command": command,
                                "children": {}
                            }
                            did_add_command = True
                            break
                        for command_found2_key in command_found["children"]:
                            command_found2 = command_found["children"][command_found2_key]
                            if str(command_found2.get("command")) == str(command.is_depended_on):
                                self.command_tree_by_letter[command_found.letter]["children"][command_found2.letter]["children"][command.letter] = {
                                    "command": command,
                                    "children": {}
                                }
                                did_add_command = True
                                break
                            for command_found3_key in command_found2["children"].items():
                                command_found3 = command_found2["children"][command_found3_key]
                                if str(command_found3.get("command")) == str(command.is_depended_on):
                                    self.command_tree_by_letter[command_found.letter]["children"][command_found2.letter]["children"][command_found3.letter]["children"][command.letter] = {
                                        "command": command,
                                        "children": {}
                                    }
                                    did_add_command = True
                                    break

                    if command.must_be_first_character:
                        did_add_command = True
                        if command.letter in self.command_tree_by_letter:
                            continue
                        self.command_tree_by_letter[command.letter] = {
                            "command": command,
                            "children": {}
                        }
                        continue

                    if did_add_command is False:
                        all_commands.append(command)

        if not self.command_tree_by_letter:
            print("No valid Command subclasses found in the Python files within the Commands directory.")

        return self.command_tree_by_letter

    def update_suggestions(self, new_suggestions):
        self.current_suggestions = new_suggestions
        self.liststore.clear()
        for suggestion in new_suggestions:
            self.liststore.append([self.format_command_name(suggestion)])

    def format_command_name(self, command):
        if command.is_optional:
            return f"{command.letter}? {command.name}"
        else:
            return f"{command.letter}! {command.name}"

    def on_text_changed(self, entry):
        text = entry.get_text()

        if not text:
            self.load_starting_commands()
            return

        if " " in text:
            return

        last_letter = text[-1]

        for current_suggestion in reversed(self.current_suggestions):
            print(current_suggestion.name)
            if current_suggestion.letter == last_letter and current_suggestion.is_optional:
                return
            if current_suggestion.letter == last_letter and current_suggestion.is_last_command:
                self.update_suggestions([current_suggestion])
                return
            if current_suggestion.letter == last_letter:
                break

        new_command_list = self.find_children_by_command_string(text)
        command_list = []
        for new_command_key in new_command_list:
            command_list.append(new_command_list[new_command_key]["command"])
        self.update_suggestions(command_list)

    def on_enter_pressed(self, entry):
        if not self.current_suggestions:
            return

        text = entry.get_text()
        customText = ""

        if not text and self.history_input_field:
            print("history")
            self.current_suggestions[0].execute(self.history_input_field)
            self.destroy()
            return

        if self.current_suggestions[0].can_type:
            customText = text.split(" ")[-1]

        if text and text[0] == "c":
            with open(self.last_command_file, "w") as file:
                file.write(text)
            pyperclip.copy(self.current_suggestions[0].copy(customText))
            self.destroy()
            return

        with open(self.last_command_file, "w") as file:
            file.write(text)

        self.current_suggestions[0].execute(customText)
        self.destroy()

    # todo
    def on_suggestion_selected(self, treeview, path, column):
        model = treeview.get_model()
        iter = model.get_iter(path)
        if iter is not None: # Ensure a valid row is selected
            selected_suggestion = model.get_value(iter, 0)
            print(f"Selected suggestion: {selected_suggestion}")
            self.entry.set_text(selected_suggestion)
            self.on_enter_pressed(self.entry)

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True

if __name__ == '__main__':
    window = SuggestionWindow()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()
