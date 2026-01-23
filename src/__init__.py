from ovos_utils import classproperty
from ovos_utils.log import LOG
from ovos_utils.process_utils import RuntimeRequirements
# from ovos_workshop.intents import IntentBuilder
from ovos_workshop.decorators import intent_handler
# from ovos_workshop.intents import IntentHandler # Uncomment to use Adapt intents
from ovos_workshop.skills import OVOSSkill

import json
import os
import random
import time

# import sys

from .version import (
    VERSION_MAJOR,
    VERSION_MINOR,
    VERSION_BUILD,
    VERSION_ALPHA
)

# Optional - if you want to populate settings.json with default values, do so here
DEFAULT_SETTINGS = {
    "PoetryFavorite": "eotp:ftxx01",
    "PoetryFilename": "/home/ovos/.venvs/ovos/lib/python3.11/site-packages/ovos_skill_poetry/locale/en-us/Data"
                      "/PoetryTest4-short.json",
    "log_level": "WARNING"
}


class PoetrySkill(OVOSSkill):
    def __init__(self, *args, **kwargs):
        """The __init__ method is called when the Skill is first constructed.
        Note that self.bus, self.skill_id, self.settings, and
        other base class settings are only available after the call to super().

        This is a good place to load and pre-process any data needed by your
        Skill, ideally after the super() call.
        """
        super().__init__(*args, **kwargs)
        self.learning = True
        self.poems = []
        self.is_reciting = False  # Track recitation state
        poem_file = self.settings.get('PoetryFilename')
        self.log_level = self.settings.get("log_level", "INFO")
        self.load_poems(poem_file)  # Update the path to your JSON file
        self.last_docid = None
        self.poem_count = len(self.poems)

    def load_poems(self, filepath):
        if not os.path.isfile(filepath):
            self.log.error(f"The file {filepath} does not exist.")
            return

        try:
            with open(filepath, 'r') as file:
                data = json.load(file)

            if 'LIBRARY' in data:
                for book in data['LIBRARY']:
                    book_title = book['BOOK_TITLE']
                    book_author = book['BOOK_AUTHOR']

                    for section in book['SECTIONS']:
                        section_title = section['SECTION_TITLE'] if section['SECTION_TITLE'] is not None else None

                        for poem in section['POEMS']:
                            self.poems.append({
                                "doc_id": poem["DOCID"],
                                "book_title": book_title,
                                "book_author": book_author,
                                "section_title": section_title,
                                "poem_title": poem['TITLE'],
                                "poem_author": poem['AUTHOR'] if poem['AUTHOR'] else book_author,
                                "content": "\n".join(poem['CONTENT'])
                            })

            else:
                self.log.error("Invalid JSON structure: missing 'LIBRARY'")
        except Exception as e:
            self.log.error(f"Error loading poems: {e}")

    def find_poem_by_docid(self, docid):
        for poem in self.poems:
            if poem["doc_id"] == docid:
                return poem
        return None

    @staticmethod
    def skill_version():

        version_string = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_BUILD}"
        if VERSION_ALPHA and int(VERSION_ALPHA) > 0:
            version_string += f"a{VERSION_ALPHA}"
        return version_string

    def initialize(self):
        LOG.debug("initialize() called")

        # noinspection PyUnresolvedReferences
        self.register_homescreen_example("Read me a poem")
        # noinspection PyUnresolvedReferences
        self.register_homescreen_example("Tell me your favorite poem")

        # merge default settings
        # self.settings is a jsondb, which extends the dict class and adds helpers like merge
        self.settings.merge(DEFAULT_SETTINGS, new_only=True)
        self.log_level = self.settings.get("log_level", "INFO")

        # Speak version if log_level != INFO
        if self.log_level.upper() != "INFO":
            ver = self.skill_version()
            spoken_version = ver.replace("a", " alpha ")
            self.speak(
                f"Poetry skill, version {spoken_version}, initialized",
                wait=False
            )

        LOG.info(f"Poetry Skill version={self.skill_version()}")

    @classproperty
    def runtime_requirements(self):
        return RuntimeRequirements(
            internet_before_load=False,
            network_before_load=False,
            gui_before_load=False,
            requires_internet=False,
            requires_network=False,
            requires_gui=False,
            no_internet_fallback=True,
            no_network_fallback=True,
            no_gui_fallback=True,
        )

    @property
    def my_setting(self):
        """Dynamically get the my_setting from the skill settings file.
        If it doesn't exist, return the default value.
        This will reflect live changes to settings.json files (local or from backend)
        """
        return self.settings.get("my_setting", "default_value")

    @intent_handler("FavoritePoem.intent")
    def favorite_poem_intent(self):
        """This is a Padatious intent handler.
        It is triggered using a list of sample phrases."""
        self.is_reciting = True  # Set flag at start
        try:
            favorite_docid = self.settings.get("PoetryFavorite")
            if not favorite_docid:
                self.speak("I don't have a favorite poem at this time.")
                return

            result = self.find_poem_by_docid(favorite_docid)

            if result:
                # Remember we just recited this one
                self.last_docid = favorite_docid
                # Unpack the returned tuple
                book_title = result["book_title"]
                book_author = result["book_author"]
                poem_title = result["poem_title"]
                # poem_author = result["poem_author"]
                content = result["content"]

                # Check to see if we should continue talking before each speak
                if not self.is_reciting:
                    return
                self.speak("Here's my current favorite poem.  It is from the book " + book_title + ".", wait=True)
                if not self.is_reciting:
                    return
                self.speak("by " + book_author + ".", wait=True)
                if not self.is_reciting:
                    return
                self.speak("the poem is called " + poem_title + ".", wait=True)
                if not self.is_reciting:
                    return
                self.speak("and it goes like this! ", wait=True)

                # Split the content by newline and speak each line individually
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if not self.is_reciting:
                        return
                    if line.strip():
                        if i == len(lines) - 1:  # Last line
                            self.speak(line.strip())
                        else:
                            self.speak(line.strip(), wait=True)
                        time.sleep(1)
            else:
                self.speak("I'm struggling to come up with a favorite poem!  Please try again later.")

        finally:
            self.is_reciting = False  # Reset flag when done

    @intent_handler("ReadPoem.intent")
    def handle_tell_me_a_poem_intent(self):
        """This is a Padatious intent handler.
        It is triggered using a list of sample phrases."""
        self.is_reciting = True  # Set state to know we are currently reciting a poem
        try:
            poem = random.choice(self.poems)
            # Avoid reciting same poem 2 times in a row
            if self.poem_count > 1:
                while poem["doc_id"] == self.last_docid:
                    poem = random.choice(self.poems)
            self.last_docid = poem["doc_id"]

            # Check if stopped before each speak
            if not self.is_reciting:
                return
            self.speak("Here's a poem from the book " + str({poem["book_title"]}), wait=True)
            if not self.is_reciting:
                return
            self.speak("by " + str({poem["book_author"]}), wait=True)
            if not self.is_reciting:
                return
            self.speak("the poem is called " + str({poem["poem_title"]}), wait=True)
            if not self.is_reciting:
                return
            self.speak("and it goes like this ... ", wait=True)

            # Split the content by newline and speak each line individually
            lines = poem["content"].split('\n')
            for i, line in enumerate(lines):
                if not self.is_reciting:
                    return
                if line.strip():
                    if i == len(lines) - 1:  # Last line
                        self.speak(line.strip())
                    else:
                        self.speak(line.strip(), wait=True)
                    time.sleep(1)
        finally:
            self.is_reciting = False   # Reset reciting state when done

    def stop(self):
        """Handle Stop request from the user ... stops long-winded poems"""
        if self.is_reciting:
            self.is_reciting = False
            self.speak_dialog("poem.stopped")  # Optional: Add feedback
            return True
        return False
