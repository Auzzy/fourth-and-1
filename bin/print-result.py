import argparse
import random

from fourthand1.cards import DefenseCard, OffenseCard
from fourthand1.play import Play


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("offense_card_file")
    parser.add_argument("defense_card_file")
    parser.add_argument("--off-offset", "--offsensive-offset", type=int, choices=(-2, -1, 0, 1, 2), default=0)
    parser.add_argument("--def-offset", "--defsensive-offset", type=int, choices=(-2, -1, 0, 1, 2), default=0)
    parser.add_argument("--from", type=int)

    return vars(parser.parse_args())


if __name__ == "__main__":
    args = parse_args()

    off_card = OffenseCard.load(args.get("offense_card_file"))
    def_card = DefenseCard.load(args.get("defense_card_file"))
    play = Play.create(off_card, def_card, args["off_offset"], args["def_offset"])
    # print(play.result().asjson())
    print([event.asjson() for event in play.run(args["from"]).resolve()])
