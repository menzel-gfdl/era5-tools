from argparse import ArgumentParser

from .combine import Combine
from .download import Download
from .horizontal_remap import HorizontalRemap
from .vertical_remap import VerticalRemap


def main():
    parser = ArgumentParser(description="ERA5 reanalysis radiation tool.")
    subparsers = parser.add_subparsers(title="commands", help="command help")

    Combine().arguments(subparsers)
    Download().arguments(subparsers)
    HorizontalRemap().arguments(subparsers)
    VerticalRemap().arguments(subparsers)
    args = parser.parse_args()
#   try:
    args.func(args)
#   except AttributeError as e:
#       print(str(e))
#       parser.error("Please specify a valid command.")
