from fourthand1.cards._card import Card


class _DefensivePlayer:
    @classmethod
    def create(cls, coord, offset):
        return cls([coord[0] + offset, coord[1]])

    def __init__(self, coord):
        self.coord = coord

    @property
    def x(self):
        return self.coord[0]

    @property
    def y(self):
        return self.coord[1]

    def asjson(self):
        return self.coord


class Tackler(_DefensivePlayer):
    pass

class Fumbler(_DefensivePlayer):
    pass


class DefenseCard(Card):
    @staticmethod
    def _sort_players(players):
        return sorted(players, key=lambda player: tuple(reversed(player.coord)))

    @staticmethod
    def load(filepath):
        card_json = Card.load_json(filepath)

        return DefenseCard.create(**card_json)

    @staticmethod
    def create(id, name, description, players):
        tacklers = [Tackler(coord) for coord in players["tacklers"]]
        fumblers = [Fumbler(coord) for coord in players["fumblers"]]
        return DefenseCard(id, name, description, tacklers, fumblers)

    def __init__(self, id, name, description, tacklers, fumblers):
        super().__init__(id, name, description)

        self.tacklers = DefenseCard._sort_players(tacklers)
        self.fumblers = DefenseCard._sort_players(fumblers)

    @property
    def players(self):
        return DefenseCard._sort_players(self.tacklers + self.fumblers)

    def asjson(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "players": {
                "tacklers": [player.asjson() for player in self.tacklers],
                "fumblers": [player.asjson() for player in self.fumblers]
            }
        }
