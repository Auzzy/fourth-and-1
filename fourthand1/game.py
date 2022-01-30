import random

from fourthand1.events import *


class Game:
    @staticmethod
    def create(team1_name, team2_name, plays_per_quarter):
        return Game(Team(team1_name), Team(team2_name), plays_per_quarter)

    def __init__(self, team1, team2, plays_per_quarter):
        self.team1 = team1
        self.team2 = team2
        self.plays_per_quarter = plays_per_quarter

        self._ball_carrier = self._kicking = self._receiving = self._offense = self._defense = None
        self.ydline = None
        self.down = None
        self.first_down_ydline = None

        self._setup_queue = []
        self._playnum = 0
        self._quarter = 1

    def coin_flip(self):
        teams = (self.team1, self.team2)
        self.ball_carrier = teams[random.randint(0, 1)]
        self.setup_kickoff()

    def role_to_team(self, role):
        return getattr(self, role)

    def opponent(self, team):
        if team is None:
            return None
        return self.team1 if team == self.team2 else self.team2

    @property
    def ball_carrier(self):
        return self._ball_carrier

    @property
    def last_ball_carrier(self):
        return self._last_ball_carrier

    @property
    def kicking(self):
        return self._kicking

    @property
    def receiving(self):
        return self._receiving

    @property
    def offense(self):
        return self._offense

    @property
    def defense(self):
        return self._defense

    @ball_carrier.setter
    def ball_carrier(self, value):
        self._last_ball_carrier = self.ball_carrier
        self._ball_carrier = value

    @kicking.setter
    def kicking(self, team):
        self._kicking, self._receiving = team, self.opponent(team)

    @receiving.setter
    def receiving(self, team):
        self._receiving, self._kicking = team, self.opponent(team)

    @offense.setter
    def offense(self, team):
        self._offense, self._defense = team, self.opponent(team)

    @defense.setter
    def defense(self, team):
        self._defense, self._offense = team, self.opponent(team)

    def _run(self, create_event):
        self._playnum += 1

        events = create_event(self.ydline)
        events.apply(self)
        self._resolve_queue()
        return events.resolve()

    def kickoff(self):
        return self._run(KickOff.create)

    def onside(self):
        return self._run(OnSideKick.create)

    def punt_in_bounds(self):
        return self._run(Punt.create_in_bounds)

    def punt_out_of_bounds(self):
        return self._run(Punt.create_out_of_bounds)

    def field_goal(self):
        return self._run(FieldGoal.create)

    def safety_punt(self):
        return self._run(SafetyPunt.create)

    def play(self, play):
        return self._run(play.run)


    def setup_kickoff(self):
        if self.ball_carrier:
            self.kicking = self.ball_carrier
        self.offense = None
        self.down = None
        self.first_down_ydline = None
        self.ydline = 40

    def setup_safety_punt(self):
        self.kicking = self.ball_carrier
        self.offense = None
        self.down = None
        self.first_down_ydline = None
        self.ydline = 20

    def setup_drive(self):
        # The math is easier if I internally treat the field as being lined
        # from 0 to 100, with 0 being the offense's endzone.
        if self.kicking:
            if self.ball_carrier == self.receiving:
                self.ydline = 100 - self.ydline
            self.kicking = None
        else:
            self.ydline = 100 - self.ydline
        self.offense = self.ball_carrier
        self.down = 1
        self.first_down_ydline = self.ydline + 10

    def setup_next_play(self):
        if self.ydline >= self.first_down_ydline:
            self.down = 1
            self.first_down_ydline = self.ydline + 10
        else:
            # Turnover on downs.
            if self.down == 4:
                self.ball_carrier = self.defense
                self.setup_drive()
            else:
                self.down += 1

    def queue_kickoff(self):
        self._setup_queue.append(self.setup_kickoff)

    def queue_drive(self):
        self._setup_queue.append(self.setup_drive)

    def queue_next_play(self):
        self._setup_queue.append(self.setup_next_play)

    def queue_safety_punt(self):
        self._setup_queue.append(self.setup_safety_punt)

    def _resolve_queue(self):
        self._setup_queue[-1]()
        self._setup_queue = []


    def print_state(self):
        if self.ball_carrier:
            if self.ball_carrier == self.kicking:
                print(f"KICKING: {self.ball_carrier.name}")
            else:
                print(f"OFFENSE: {self.ball_carrier.name}")
        if self.ydline > 50:
            print(f"BALL ON: opponent's {100 - self.ydline}")
        else:
            print(f"BALL ON: own {self.ydline}")

        if self.down:
            print(f"DOWN: {self.down} and {self.first_down_ydline - self.ydline}")
        print(f"QUARTER: {self._quarter}")
        print(f"PLAY: {self._playnum}")

        print(f"{self.team1.name}: {self.team1.score}")
        print(f"{self.team2.name}: {self.team2.score}")


class Team:
    def __init__(self, name):
        self.name = name
        self.score = 0
