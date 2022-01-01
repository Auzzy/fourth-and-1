import argparse
import json
from os.path import dirname, join

from fourthand1.cards import DefenseCard, OffenseCard
from fourthand1.play import Play


TEMPLATE_PATH = join(dirname(__file__), "template.html")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("offense_card_file", nargs="?")
    parser.add_argument("defense_card_file", nargs="?")
    parser.add_argument("--off-offset", "--offsensive-offset", type=int, choices=(-2, -1, 0, 1, 2), default=0)
    parser.add_argument("--def-offset", "--defsensive-offset", type=int, choices=(-2, -1, 0, 1, 2), default=0)

    return vars(parser.parse_args())

if __name__ == "__main__":
    args = parse_args()

    off_card, def_card = None, None
    with open(TEMPLATE_PATH) as template_file:
        card = template_file.read()

    offense_card_filepath = args.get("offense_card_file")
    if offense_card_filepath:
        off_card = OffenseCard.load(offense_card_filepath)

    defense_card_filepath = args.get("defense_card_file")
    if defense_card_filepath:
        def_card = DefenseCard.load(defense_card_filepath)

    if off_card and def_card:
        play = Play.create(off_card, def_card, args["off_offset"], args["def_offset"])
        off_card_json = play.off_play.asjson()
        def_card_json = play.def_play.asjson()
    elif off_card:
        off_card_json = off_card.asjson()
    elif def_card:
        def_card_json = def_card.asjson()


    card = card \
        .replace("\"\";//{{OFFENSE_CARD_JSON}}", f"{json.dumps(off_card_json)};") \
        .replace("\"\";//{{DEFENSE_CARD_JSON}}", f"{json.dumps(def_card_json)};")

    print(card)
