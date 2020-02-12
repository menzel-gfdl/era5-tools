"""Horizontally remaps netCDF data."""
from os.path import join
from shutil import which
from subprocess import run
from tempfile import TemporaryDirectory

from .commands import Command


class HorizontalRemap(Command):
    @staticmethod
    def arguments(subparsers):
        """Adds command specific command-line arguments.

        Args:
            subparsers: Special action object returned by ArgumentParser().add_subparsers().
        """
        command = "horizontal-remap"
        parser = subparsers.add_parser(command, help="{} help".format(command))
        parser.add_argument("dataset", help="Dataset to be remapped.")
        parser.add_argument("output", help="Output file path.")
        parser.add_argument("nlon", help="Number of longitude points.", type=int)
        parser.add_argument("nlat", help="Number of latitude points.", type=int)
        parser.set_defaults(func=remap)


def remap(args):
    """Perform horizontal remapping on an entire dataset using cdo.

    Args:
        args: Namespace object returned by ArgumentParser().parse_args().

    Raises:
        EnvironmentError if cdo is not found.
    """
    cdo = "cdo"
    if which(cdo) is None:
        raise EnvironmentError("you must have {} installed.".format(cdo))
    with TemporaryDirectory() as directory:
        weights = join(directory, "remap-weights.nc")
        run([cdo, "gencon,r{}x{}".format(args.nlon, args.nlat), args.dataset, weights],
            check=True)
        run([cdo, "-f", "nc4", "remap,r{}x{},{}".format(args.nlon, args.nlat, weights),
            args.dataset, args.output], check=True)
