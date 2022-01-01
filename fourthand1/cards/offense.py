import itertools
import json

from fourthand1.cards._card import Card


# backport from 3.10
def ipairwise(iterable):
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


class _PathSegment:
    @classmethod
    def create(cls, raw_seg1, raw_seg2, offset=0):
        return cls(raw_seg1["start"], raw_seg2["start"])

    def __init__(self, start, end):
        self.type = self.TYPE
        self.start = start
        self.end = end

    def asjson(self):
        return {
            "type": self.type,
            "start": self.start,
            "end": self.end
        }

class Run(_PathSegment):
    TYPE = "run"

class Pass(_PathSegment):
    TYPE = "pass"

class Lateral(Pass):
    TYPE = "lateral"

class Catch(_PathSegment):
    TYPE = "catch"


class OffenseCard(Card):
    _SEG_TYPES = (Run, Pass, Lateral, Catch)
    _SEG_TYPE_MAP = {cls.TYPE: cls for cls in _SEG_TYPES}

    @staticmethod
    def load(filepath):
        card_json = Card.load_json(filepath)

        return OffenseCard.create(**card_json)

    @staticmethod
    def create(id, name, path):
        type_map = OffenseCard._SEG_TYPE_MAP
        path = [type_map[node1["type"]].create(node1, node2) for node1, node2 in ipairwise(path)]
        return OffenseCard(id, name, path)

    def __init__(self, id, name, path):
        super().__init__(id, name)

        self.path = path

    def asjson(self):
        return {
            "id": self.id,
            "name": self.name,
            "path": [seg.asjson() for seg in self.path]
        }
