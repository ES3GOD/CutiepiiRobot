import yaml
import os
from typing import Dict


class Language:
    def __init__(self) -> None:
        self.languages: Dict = {}
        self.reload_strings()

    def get_string(self, lang: str, string: str) -> str:
        try:
            return self.languages[lang][string]
        except KeyError:
            # a keyerror happened, the english file must have it
            en_string = self.languages["en"].get(string)
            if en_string is None:
                raise StringNotFound(f"String: ({string}) not found.")
            return en_string

    def reload_strings(self) -> None:
        for filename in os.listdir(r"./SeiraRobot/language"):
            if filename.endswith(".yaml"):
                language_name = filename[:-5]
                self.languages[language_name] = yaml.safe_load(
                    open(f"./SeiraRobot/language/{filename}", encoding="utf8")
                )

    def get_languages(self) -> Dict:
        return {
            language: self.languages[language]["language"]
            for language in self.languages
        }

    def get_language(self, language: str) -> str:
        return self.languages[language]["language"]


class StringNotFound(Exception):
    """
    Raised when language string not found for the
    given key inside english locale.
    """


langs = Language()
