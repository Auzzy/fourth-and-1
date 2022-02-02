from copy import deepcopy

from fourthand1.cards.offense import OffenseCard, Catch, Pass, Run
from fourthand1.cards.defense import DefenseCard
from fourthand1.events import PlayResult
from fourthand1.play._geo import catch_zone, defender_zone, path_segment


class Play:
    @staticmethod
    def create(off_card, def_card, off_offset=0, def_offset=0):
        return Play(
            _OffensePlay.apply_offset(off_card, off_offset),
            _DefensePlay.apply_offset(def_card, def_offset))

    def __init__(self, off_play, def_play):
        self.off_play = off_play
        self.def_play = def_play

    def run(self, from_ydline):
        return PlayResult.create(from_ydline, self.off_play, self.def_play)


class _OffensePlay(OffenseCard):
    @staticmethod
    def apply_offset(card, offset=0):
        def _int_rect(seg):
            if isinstance(seg, Pass):
                return catch_zone(seg.end)
            elif isinstance(seg, Catch):
                return catch_zone(seg.start)

        coord_shift = lambda coord: [coord[0] + offset, coord[1]]
        card_path = deepcopy(card.path)
        for seg in card_path:
            seg.start = coord_shift(seg.start)
            seg.end = coord_shift(seg.end)
            seg.rect = path_segment(seg.start, seg.end)
            seg.int_rect = _int_rect(seg)
        return _OffensePlay(card.id, card.name, card_path)


class _DefensePlay(DefenseCard):
    @staticmethod
    def _offset_players(players, offset):
        players_copy = deepcopy(players)
        for player in players_copy:
            player.coord = [player.coord[0] + offset, player.coord[1]]
            player.rect = defender_zone(player.coord)
        return players_copy

    @staticmethod
    def apply_offset(card, offset=0):
        tacklers = _DefensePlay._offset_players(card.tacklers, offset)
        fumblers = _DefensePlay._offset_players(card.fumblers, offset)
        return _DefensePlay(card.id, card.name, card.description, tacklers, fumblers)
