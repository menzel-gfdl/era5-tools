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
        parser.set_defaults(func=remap_)


def remap_(args):
    """Perform horizontal remapping on an entire dataset using cdo.

    Args:
        args: Namespace object returned by ArgumentParser().parse_args().
    """
    remap(args.dataset, args.output, args.nlon, args.nlat)


def remap(dataset, output, nlon, nlat):
    """Perform horizontal remapping on an entire dataset using cdo.

    Args:
        dataset: Path to netCDF4 dataset that will be remapped.
        output: Path to output netCDF4 dataset.
        nlon: Number of longitude points to remap to.
        nlat: Number of latitude points to remap to.

    Raises:
        EnvironmentError if cdo is not found.
    """
    cdo = "cdo"
    if which(cdo) is None:
        raise EnvironmentError("you must have {} installed.".format(cdo))
    with TemporaryDirectory() as directory:
        weights = join(directory, "remap-weights.nc")
        run([cdo, "gencon,r{}x{}".format(nlon, nlat), dataset, weights], check=True)
        run([cdo, "-f", "nc4", "remap,r{}x{},{}".format(nlon, nlat, weights), dataset, output], check=True)
