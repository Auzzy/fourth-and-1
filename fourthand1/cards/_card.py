import json


class Card:
    @staticmethod
    def load_json(filepath):
        with open(filepath) as card_file:
            return json.load(card_file)

    def __init__(self, id_, name, description=None):
        self.id = id_
        self.name = name
        self.description = description
