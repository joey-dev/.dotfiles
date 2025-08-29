from abc import ABC, abstractmethod

class Command(ABC):
    @property
    @abstractmethod
    def letter(self):
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def is_optional(self):
        return False

    @property
    @abstractmethod
    def must_be_first_character(self):
        return False

    @property
    @abstractmethod
    def is_depended_on(self):
        return None

    @property
    @abstractmethod
    def can_be_executed(self):
        return False

    @property
    @abstractmethod
    def can_be_copied(self):
        return False

    @property
    @abstractmethod
    def is_last_command(self):
        return False

    @property
    @abstractmethod
    def can_type(self):
        return False

    @property
    @abstractmethod
    def has_input_field(self):
        return False

    @abstractmethod
    def input_fields(self):
        pass

    @abstractmethod
    def execute(self, text):
        pass

    @abstractmethod
    def copy(self, text):
        pass

    def __str__(self):
        return f"{self.letter} ({self.name})"

