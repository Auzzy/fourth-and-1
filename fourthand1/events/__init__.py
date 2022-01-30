import itertools
import random

from fourthand1.cards.defense import DefenseCard, Fumbler, Tackler
from fourthand1.cards.offense import OffenseCard, Catch, Lateral, Pass, Run


def _ydline_str(absydline):
    if absydline == 50:
        return "midfield"
    else:
        ydline = absydline if absydline < 50 else (100 - absydline)
        display_ydline = "goal line" if ydline == 0 else ydline
        return f"their own {display_ydline}" if absydline < 50 else f"the opponent's {display_ydline}"

def roll_dice():
    return sum(random.randint(1, 6) for k in range(3))

class _Event:
    @classmethod
    def factory(cls, *args, **kwargs):
        return type(cls.__name__, (_EventFactory, ), {"CLS": cls})(*args, **kwargs)

    @classmethod
    def create(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def __init__(self, yds=None):
        self.yds = yds

    def resolve(self):
        return [self]

    def apply(self, game):
        pass

    def asjson(self):
        result_json = {"type": self.TYPE}
        if self.yds is not None:
            result_json["yds"] = self.yds
        return result_json

    def __str__(self):
        string = self.TYPE
        if self.yds is not None:
            string += f" {self.yds}"
        return string

class _InitialEvent(_Event):
    def __init__(self, from_ydline, yds=None):
        super().__init__(yds)

        self.from_ydline = from_ydline

    @property
    def penalties(self):
        return []

    def asjson(self):
        return {
            **super().asjson(),
            "from": self.from_ydline
        }

class _EventFactory:
    def __init__(self, play_yds=0, *args, **kwargs):
        self.play_yds = play_yds
        self.args = args
        self.kwargs = kwargs

    def create(self, from_ydline):
        return self.CLS.create(from_ydline + self.play_yds, *self.args, **self.kwargs)

    @property
    def yds(self):
        return self.play_yds

class Stop(_Event):
    def resolve(self):
        return []

class Tackle(Stop):
    TYPE = "tackle"

    @classmethod
    def create(cls, play_end):
        if play_end > 100:
            return Touchdown.create()
        elif play_end < 0:
            return Safety.create()
        else:
            return cls()

    def apply(self, game):
        game.queue_next_play()

class Incomplete(_Event):
    TYPE = "incomplete"

    def apply(self, game):
        game.queue_next_play()

    def __str__(self):
        return "Batted down. Incomplete."

class Touchdown(_Event):
    TYPE = "touchdown"

    @classmethod
    def create(cls):
        return cls(PATResult.create())

    def __init__(self, pat):
        super().__init__()

        self.pat = pat

    def resolve(self):
        return [self] + self.pat.resolve()

    def apply(self, game):
        game.ball_carrier.score += 6
        self.pat.apply(game)

        game.queue_kickoff()

    def __str__(self):
        return "Touchdown!"

class Penalty(_Event):
    TYPE = "penalty"

    @classmethod
    def create(cls, play_end, penalty_dist):
        against = "offense" if roll_dice() <= 10 else "defense"
        return cls(play_end, penalty_dist, against)

    def __init__(self, play_end, penalty_dist, against):
        super().__init__(play_end)

        self.penalty_dist = penalty_dist
        self.against = against

    def asjson(self):
        return {
            **super().asjson(),
            "penaltyYd": self.penalty_dist,
            "against": self.against
        }

    def apply(self, game):
        game.ydline += self.yds
        if self.against == "offense":
            game.ydline -= self.penalty_dist
        else:
            game.ydline += self.penalty_dist

class SpecialTeamsPenalty(Penalty):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.against in ("offense", "defense"):
            self.against = "kicking" if self.against == "offense" else "receiving"

    def apply(self, game):
        game.ydline += self.yds
        if self.against == "kicking":
            game.ydline -= self.penalty_dist
        else:
            game.ydline += self.penalty_dist

class Fumble(_Event):
    TYPE = "fumble"

    @classmethod
    def create(cls, recovered_from, retyds=0, recovered_by=None):
        recovered_by = recovered_by or ("offense" if roll_dice() <= 10 else "defense")

        result = None
        if recovered_by == "offense":
            play_end = recovered_from + retyds
            if play_end > 100:
                result = Touchdown.create()
            elif play_end < 0:
                result = Safety.create()
        else:
            play_end = recovered_from - retyds
            if play_end < 0:
                result = Touchdown.create()
            elif play_end > 100:
                result = Touchback.create()

        return cls(retyds, recovered_by, result)

    def __init__(self, yds, recovered_by, result=None):
        super().__init__(yds)

        self.recovered_by = recovered_by
        self.result = result

    def asjson(self):
        return {
            **super().asjson(),
            "recoveredBy": self.recovered_by
        }

    def resolve(self):
        result = self.result.resolve() if self.result else []
        return [self] + result

    def apply(self, game):
        game.ball_carrier = game.role_to_team(self.recovered_by)

        if game.ball_carrier in (game.kicking, game.offense):
            game.ydline += self.yds
        elif game.ball_carrier in (game.receiving, game.defense):
            game.ydline -= self.yds

        if game.ball_carrier == game.offense:
            game.queue_next_play()
        elif game.ball_carrier in (game.kicking, game.receiving, game.defense):
            game.queue_drive()

        if self.result:
            self.result.apply(game)

    def __str__(self):
        return f"Fumble! Recovered by the {self.recovered_by}."

class SpecialTeamsFumble(Fumble):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.recovered_by in ("offense", "defense"):
            self.recovered_by = "kicking" if self.recovered_by == "offense" else "receiving"

    def __str__(self):
        return f"Fumble! Recovered by the {self.recovered_by} team."


class Touchback(_Event):
    TYPE = "touchback"

    def __init__(self):
        super().__init__()

    def apply(self, game):
        game.ball_carrier = game.receiving
        game.ydline = 80

        game.queue_drive()

    def __str__(self):
        return "Touchback."

class GoalLine(_Event):
    TYPE = "goal line"

    def resolve(self):
        return []

class FairCatch(_Event):
    TYPE = "fair catch"

    def apply(self, game):
        game.queue_drive()

    def __str__(self):
        return "A fair catch is called."

class OutOfBounds(_Event):
    TYPE = "out of bounds"

    @classmethod
    def create(cls, return_from):
        if return_from > 100:
            return Touchback.create()

        return cls()

    def apply(self, game):
        game.ball_carrier = game.receiving

        game.queue_drive()

    def __str__(self):
        return "Out of bounds."

class Interception(_Event):
    TYPE = "interception"
    YDS = {
        3: Touchdown,
        4: 30,
        5: 3,
        6: 2,
        7: 0,
        8: 6,
        9: 8,
        10: 15,
        11: 15,
        12: 5,
        13: 8,
        14: 20,
        15: Touchdown,
        16: 25,
        17: (Penalty, (30, 15)),
        18: 35
    }

    @classmethod
    def create(cls, return_from):
        penalty = None
        returned = get_outcome(Interception.YDS)
        return_yds = return_from if isinstance(returned, Touchdown) else returned.yds
        if isinstance(returned, Penalty):
            penalty, returned = returned, Stop.create(returned.yds)
            penalty.yds = None

        if return_yds > return_from:
            returned = Touchdown.create()

        return cls(return_yds, returned, penalty)

    def __init__(self, yds, returned, penalty=None):
        super().__init__(yds)

        self.returned = returned
        self.penalty = penalty

    @property
    def penalties(self):
        return [self.penalty] if self.penalty else []

    def resolve(self):
        return [self] + self.returned.resolve()

    def apply(self, game):
        game.ball_carrier = game.opponent(game.ball_carrier)
        game.ydline -= self.yds

        game.queue_drive()

        self.returned.apply(game)

    def __str__(self):
        return f"Intercepted! Returned {self.yds} yards."

class KickOff(_InitialEvent):
    TYPE = "kick-off"

    YDS = {
        3: Touchback,
        4: Touchback,
        5: Touchback,
        6: (SpecialTeamsPenalty, (10, 5)),
        7: GoalLine,
        8: GoalLine,
        9: 45,
        10: 55,
        11: 55,
        12: 50,
        13: 50,
        14: 45,
        15: 40,
        16: 35,
        17: (SpecialTeamsPenalty, (30, 15)),
        18: 40
    }

    @classmethod
    def create(cls, kick_from):
        penalty = None
        kick_result = get_outcome(KickOff.YDS)
        if isinstance(kick_result, GoalLine):
            kick_yds = 100 - kick_from
        elif isinstance(kick_result, Touchback):
            kick_yds = 111 - kick_from
        else:
            kick_yds = kick_result.yds
            if isinstance(kick_result, Penalty):
                penalty, kick_result = kick_result, Stop.create(kick_result.yds)
                penalty.yds = None

        if kick_from + kick_yds > 110:
            kick_result = Touchback.create()

        returned = None if isinstance(kick_result, Touchback) else KickOffReturn.create(kick_from + kick_yds)
        return cls(kick_from, kick_yds, kick_result, returned, penalty)

    def __init__(self, kick_from, kick_yds, kick_result, returned, penalty=None):
        super().__init__(kick_from, kick_yds)

        self.kick_result = kick_result
        self.returned = returned
        self.penalty = penalty

    @property
    def penalties(self):
        return [penalty for penalty in (self.penalty, self.returned.penalty) if penalty]

    def resolve(self):
        kick_result = self.kick_result.resolve()
        returned = self.returned.resolve() if self.returned else []
        return [self] + kick_result + returned

    def apply(self, game):
        game.ball_carrier = game.kicking
        game.ydline = self.from_ydline + self.yds
        self.kick_result.apply(game)
        if self.returned:
            self.returned.apply(game)

    def __str__(self):
        end_ydline = self.from_ydline + self.yds
        return f"Kicked off from {_ydline_str(self.from_ydline)} yard line. Travels {self.yds} yards to {_ydline_str(end_ydline)}."

class KickOffReturn(_Event):
    TYPE = "kick-off return"

    YDS = {
        3: Touchdown,
        4: 70,
        5: SpecialTeamsFumble.factory(0, recovered_by="kicking"),
        6: 5,
        7: 10,
        8: 15,
        9: 25,
        10: 20,
        11: 20,
        12: 25,
        13: 10,
        14: 15,
        15: 30,
        16: 40,
        17: 50,
        18: (SpecialTeamsPenalty, (60, 15))
    }

    @classmethod
    def create(cls, return_from):
        penalty = None
        returned = get_outcome(KickOffReturn.YDS)
        return_yds = return_from if isinstance(returned, Touchdown) else returned.yds
        if isinstance(returned, _EventFactory):
            returned = returned.create(return_from)
        if isinstance(returned, Penalty):
            penalty, returned = returned, Stop.create(returned.yds)
            returned.yds = None

        if return_yds > return_from:
            returned = Touchdown.create()

        return cls(return_yds, returned, penalty)

    def __init__(self, return_yds, returned, penalty=None):
        super().__init__(return_yds)

        self.returned = returned
        self.penalty = None

    def resolve(self):
        return [self] + self.returned.resolve()

    def apply(self, game):
        game.ball_carrier = game.receiving
        game.ydline -= self.yds

        game.queue_drive()

        self.returned.apply(game)

    def __str__(self):
        return f"Returned {self.yds} yards."

class OnSideKick(_InitialEvent):
    TYPE = "on-side kick"

    YDS = {
        3: 4,
        4: 5,
        5: 6,
        6: 7,
        7: 8,
        8: SpecialTeamsFumble.factory(9),
        9: SpecialTeamsFumble.factory(10),
        10: SpecialTeamsFumble.factory(11),
        11: SpecialTeamsFumble.factory(12),
        12: 13,
        13: 14,
        14: 15,
        15: 16,
        16: 17,
        17: 18,
        18: 20
    }

    @classmethod
    def create(cls, kick_from):
        result = get_outcome(OnSideKick.YDS)
        kick_yds = result.yds
        if isinstance(result, _EventFactory):
            result = result.create(kick_from)
        return cls(kick_from, kick_yds, result)

    def __init__(self, kick_from, kick_yds, result=None):
        super().__init__(kick_from, kick_yds)

        self.result = result

    def resolve(self):
        result = self.result.resolve() if self.result else []
        return [self] + result

    def apply(self, game):
        game.ball_carrier = game.receiving
        game.ydline = self.from_ydline + self.yds

        game.queue_drive()

        self.result.apply(game)

    def __str__(self):
        end_ydline = self.from_ydline + self.yds
        return f"Onside kick from {_ydline_str(self.from_ydline)}. Travels {self.yds} to {_ydline_str( end_ydline)}."

class BlockedKick(_Event):
    TYPE = "blocked kick"

    # Note: This table makes little sense. No matter who recovers the ball,
    # it travels in the same direction: behind the line of scrimmage (from the
    # offensive perspective). And yet the rules imply the offense could get a
    # first down. Maybe the intention is the yards are supposed to be read from
    # the defense's perspective? But that means if your kick is blocked and you
    # recover, you always advance the ball...
    YDS = {
        3: 20,
        4: 20,
        5: 15,
        6: 15,
        7: 10,
        8: 10,
        9: 5,
        10: 5,
        11: -5,
        12: -5,
        13: -10,
        14: -10,
        15: -15,
        16: -15,
        17: -20,
        18: -20
    }

    @classmethod
    def create(cls, kick_from):
        returned = get_outcome(BlockedKick.YDS)
        recovered_by = "kicking" if returned.yds < 0 else "receiving"

        result = None
        if recovered_by == "kicking":
            if kick_from + returned.yds < 0:
                result = Safety.create()
        else:
            if kick_from - returned.yds < 0:
                result = Touchdown.create()

        return cls(returned.yds, recovered_by, result)

    def __init__(self, yds, recovered_by, result=None):
        super().__init__(yds)

        self.recovered_by = recovered_by
        self.result = result

    def asjson(self):
        return {
            **super().asjson(),
            "recoveredBy": self.recovered_by
        }

    def resolve(self):
        result = self.result.resolve() if self.result else []
        return [self] + result

    def apply(self, game):
        game.ball_carrier = game.role_to_team(self.recovered_by)
        game.ydline += self.yds

        if game.last_ball_carrier == game.ball_carrier:
            game.queue_next_play()
        else:
            game.queue_drive()

        if self.result:
            self.result.apply(game)

    def __str__(self):
        yddir = "gain" if self.yds > 0 else "loss"
        return f"Blocked! Recovered by the {self.recovered_by} team for a {abs(self.yds)} {yddir}."

class PuntReturn(_Event):
    TYPE = "punt return"

    YDS = {
        3: Touchdown,
        4: FairCatch,
        5: FairCatch,
        6: SpecialTeamsFumble.factory(0, recovered_by="kicking"),
        7: 2,
        8: 5,
        9: 9,
        10: 7,
        11: 10,
        12: 8,
        13: 10,
        14: 15,
        15: 20,
        16: 30,
        17: (SpecialTeamsPenalty, (40, 15)),
        18: Touchdown
    }

    @classmethod
    def create(cls, return_from):
        penalty = None
        returned = get_outcome(PuntReturn.YDS)
        if isinstance(returned, _EventFactory):
            returned = returned.create(return_from)
        if isinstance(returned, Penalty):
            penalty, returned = returned, Stop.create(returned.yds)
            penalty.yds = None

        if return_from > 100:
            if return_from > 110 or isinstance(returned, FairCatch) or roll_dice() <= 10:
                # 50% chance the punt is returned if into the endzone. The
                # official rules say it's player's choice, but this simplifies
                # things, at least for now.
                return Touchback.create()
        elif isinstance(returned, FairCatch):
            return returned

        return_yds = return_from if isinstance(returned, Touchdown) else returned.yds
        if return_yds > return_from:
            returned = Touchdown.create()
        elif return_from - return_yds > 100:
            returned = Touchback.create()

        return cls(return_yds, returned, penalty)

    def __init__(self, return_yds, returned, penalty=None):
        super().__init__(return_yds)

        self.returned = returned
        self.penalty = penalty

    def resolve(self):
        return [self] + self.returned.resolve()

    def apply(self, game):
        game.ball_carrier = game.receiving
        game.ydline -= self.yds

        game.queue_drive()

        self.returned.apply(game)

    def __str__(self):
        return f"Returned {self.yds}."

class Punt(_InitialEvent):
    TYPE = "punt"

    IN_BOUNDS_YDS = {
        3: 20,
        4: BlockedKick.factory(0),
        5: 30,
        6: (SpecialTeamsPenalty, (35, 5)),
        7: 20,
        8: 25,
        9: 40,
        10: 40,
        11: 40,
        12: 40,
        13: 45,
        14: 50,
        15: 55,
        16: 60,
        17: (SpecialTeamsPenalty, (65, 15)),
        18: 70
    }

    OUT_OF_BOUNDS_YDS = {
        3: BlockedKick.factory(0),
        4: BlockedKick.factory(0),
        5: 20,
        6: (SpecialTeamsPenalty, (25, 5)),
        7: 15,
        8: 15,
        9: 20,
        10: 25,
        11: 30,
        12: 35,
        13: 40,
        14: 45,
        15: 40,
        16: PuntReturn.factory(40),
        17: PuntReturn.factory(25),
        18: PuntReturn.factory(35)
    }

    @classmethod
    def create_out_of_bounds(cls, kick_from):
        return cls.create(kick_from, Punt.OUT_OF_BOUNDS_YDS, OutOfBounds)

    @classmethod
    def create_in_bounds(cls, kick_from):
        return cls.create(kick_from, Punt.IN_BOUNDS_YDS, PuntReturn)

    @classmethod
    def create_safety(cls, kick_from):
        return SafetyPunt.create(kick_from)

    @classmethod
    def create(cls, kick_from, outcome_table, result_event):
        penalty = None
        kick_result = get_outcome(outcome_table)
        kick_yds = kick_result.yds
        if isinstance(kick_result, _EventFactory):
            kick_result = kick_result.create(kick_from)

        if isinstance(kick_result, Penalty):
            penalty, kick_result = kick_result, Stop.create(kick_result.yds)
            penalty.yds = None

        if not isinstance(kick_result, (BlockedKick, Touchback, PuntReturn)):
            kick_result = result_event.create(kick_from + kick_yds)

        return cls(kick_from, kick_yds, kick_result, penalty)

    def __init__(self, kick_from, kick_yds, kick_result, penalty=None):
        super().__init__(kick_from, kick_yds)

        self.kick_result = kick_result
        self.penalty = penalty

    @property
    def penalties(self):
        result_penalty = self.kick_result.penalty if isinstance(self.kick_result, PuntReturn) else []
        return [penalty for penalty in (self.penalty, result_penalty) if penalty]

    def resolve(self):
        return [self] + self.kick_result.resolve()

    def apply(self, game):
        game.ball_carrier = game.kicking
        game.ydline = self.from_ydline + self.yds
        self.kick_result.apply(game)

    def __str__(self):
        end_ydline = self.from_ydline + self.yds
        return f"Punted from {_ydline_str(self.from_ydline)}. Travels {self.yds} to {_ydline_str( end_ydline)}."

class FieldGoal(_InitialEvent):
    TYPE = "field goal"

    PROB = {
        (91, 100): [(3, 11)],
        (86, 90): [(3, 10)],
        (81, 85): [(3, 9)],
        (76, 80): [(3, 8)],
        (71, 75): [(3, 7)],
        (66, 70): [(3, 6)],
        (61, 65): [(3, 5)],
        (55, 60): [(3, 4)]
    }
    BLOCKED_ROLL = (14, )
    MIN_YDLINE = min(min(ydlines) for ydlines in PROB)

    # I've seen pictures of another printing of the '77 edition with this chart.
    ALT_PROB = {
        (95, 100): [(3, 14)],
        (90, 94): [(3, 12), (14, ), (17, )],
        (85, 89): [(4, 12), (17, )],
        (80, 84): [(3, 4), (6, 10), (12, ), (14, )],
        (75, 79): [(4, 5), (7, 10), (13, ), (17, )],
        (70, 74): [(4, 5), (7, 10)],
        (65, 69): [(3, 5), (7, 9)],
        (60, 64): [(3, ), (5, ), (7, 8)],
    }
    ALT_BLOCKED_ROLL = (15, 16)
    ALT_MIN_YDLINE = min(min(ydlines) for ydlines in ALT_PROB)

    @classmethod
    def create(cls, kick_from):
        blocked_roll = FieldGoal.BLOCKED_ROLL * (2 if len(FieldGoal.BLOCKED_ROLL) == 1 else 1)
        roll_val = roll_dice()
        if blocked_roll[0] <= roll_val <= blocked_roll[1]:
            result = BlockedKick.create(kick_from)
        else:
            for yd_range, dice_ranges in FieldGoal.PROB.items():
                if yd_range[0] <= kick_from <= yd_range[1]:
                    for dice_range in dice_ranges:
                        dice_range *= 2 if len(dice_range) == 1 else 1
                        if dice_range[0] <= roll_val <= dice_range[1]:
                            result = FieldGoalResult.create(True)
                            break
                    else:
                        result = FieldGoalResult.create(False)

                    break
            else:
                # Out of range.
                result = FieldGoalResult.create(False)

        return cls(kick_from, result)

    def __init__(self, kick_from, result):
        super().__init__(kick_from)

        self.result = result

    def resolve(self):
        return [self] + self.result.resolve()

    def apply(self, game):
        self.result.apply(game)

    def __str__(self):
        return "Attempting a {self.yds} yard field goal."

class FieldGoalResult(_Event):
    TYPE = "field goal result"

    def __init__(self, made):
        super().__init__()

        self.made = made

    def asjson(self):
        return {
            **super().asjson(),
            "fgResult": "made" if self.made else "missed"
        }

    def apply(self, game):
        if self.made:
            game.ball_carrier.score += 3

            game.setup_kickoff()
        else:
            # A missed (not blocked) FG is a turnover. If the FG was taken
            # inside the opponent's 20, then it comes out to the 20.
            game.ydline = min(game.ydline, 80)
            game.queue_drive()

    def __str__(self):
        return "It's good!" if self.made else "Missed! Turnover on downs."

class PATResult(_Event):
    TYPE = "point after"

    @classmethod
    def create(cls):
        return PATResult(3 <= roll_dice() <= 14)

    def __init__(self, made):
        super().__init__()

        self.made = made

    def asjson(self):
        return {
            **super().asjson(),
            "patResult": "made" if self.made else "missed"
        }

    def apply(self, game):
        if self.made:
            game.ball_carrier.score += 1

        game.setup_kickoff()

    def __str__(self):
        return f"Point after is {'good.' if self.made else 'no good!'}"

class Safety(_Event):
    TYPE = "safety"

    def apply(self, game):
        game.opponent(game.ball_carrier).score += 2

        game.queue_safety_punt()

    def __str__(self):
        return "Safety."

class SafetyPunt(Punt):
    TYPE = "safety punt"

    # There's no safety punt table, so I modified the in-bounds punt table.
    # Removed the block, and pumped the distance by 10 yards for all but the
    # longest kicks.
    YDS = {
        3: 30,
        4: 35,
        5: 40,
        6: (SpecialTeamsPenalty, (45, 5)),
        7: 30,
        8: 35,
        9: 50,
        10: 50,
        11: 50,
        12: 50,
        13: 55,
        14: 60,
        15: 60,
        16: 65,
        17: (SpecialTeamsPenalty, (70, 15)),
        18: 75
    }

    @classmethod
    def create(cls, kick_from):
        return super().create(kick_from, SafetyPunt.YDS, PuntReturn)

    def __str__(self):
        end_ydline = self.from_ydline + self.yds
        return f"Safety punt from {_ydline_str(self.from_ydline)}. Travels {self.yds} to {_ydline_str( end_ydline)}."

class PlayResult(_InitialEvent):
    TYPE = "play from scrimmage"

    @classmethod
    def _eval_play(cls, from_ydline, off_play, def_play):
        for segment in off_play.path[1:]:
            for player in def_play.players:
                if segment.rect.contains_square(player.rect):
                    play_yds = round(player.y)
                    play_end = from_ydline + play_yds
                    int_rect = segment.int_rect
                    if int_rect and int_rect.contains_square(player.rect):
                        result = Interception.create(play_end)
                    elif isinstance(segment, (Run, Catch)):
                        result = Fumble.create(play_end) if isinstance(player, Fumbler) else Tackle.create(play_end)
                    elif isinstance(segment, Lateral):
                        result = Fumble.create(play_end)
                    elif isinstance(segment, Pass):
                        result = Incomplete.create()
                        play_yds = 0

                    return result, play_yds
        else:
            return Touchdown.create(), 100 - from_ydline

    @classmethod
    def create(cls, from_ydline, off_play, def_play):
        result, play_yds = cls._eval_play(from_ydline, off_play, def_play)
        return cls(from_ydline, play_yds, result)

    def __init__(self, from_ydline, yds, result):
        super().__init__(from_ydline, yds)

        self.result = result

    def resolve(self):
        return [self] + self.result.resolve()

    def apply(self, game):
        game.ydline = self.from_ydline + self.yds
        self.result.apply(game)

    def __str__(self):
        if self.yds == 0:
            yds_str = "no gain"
        else:
            yds_str = f"a {self.yds} gain" if self.yds > 0 else f"a {abs(self.yds)} loss"
        return f"Play from scrimmage at {_ydline_str(self.from_ydline)} goes for {yds_str}."



# Might want to develop a way to handle successive events. For example, an entry should be able to be "3: (10, SpecialTeamPenalty, (15, ))", and have that interpreted as "[Stop.create(10), SpecialTeamsPenalty(15)]". This also means the corresponding classes (e.g. KickOff, KickOffReturn) would need to handle them. Probably by treating the first result as normal, and the second result in a special, specific way.
def get_outcome(outcome_table):
    outcome = outcome_table[roll_dice()]
    if not isinstance(outcome, (_Event, _EventFactory)):
        outcome_type = outcome if isinstance(outcome, type) else type(outcome)
        if issubclass(outcome_type, (tuple, _Event)):
            if issubclass(outcome_type, _Event):
                outcome = (outcome, tuple())
            return outcome[0].create(*outcome[1])
        elif isinstance(outcome, int):
            return Stop.create(outcome)
    return outcome
