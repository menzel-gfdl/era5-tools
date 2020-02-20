"""Combines netCDF datasets.  Requires ncrcat and ncpdq from CDO."""
from os.path import basename, join
from shutil import which
from subprocess import run
from tempfile import TemporaryDirectory

from .commands import Command


ncrcat = "ncrcat"
ncpdq = "ncpdq"


class Combine(Command):
    @staticmethod
    def arguments(subparsers):
        """Adds command specific command-line arguments.

        Args:
            subparsers: Special action object returned by ArgumentParser().add_subparsers().
        """
        command = "combine"
        parser = subparsers.add_parser(command, help="{} help.".format(command))
        parser.add_argument("datasets", nargs="+", help="input datasets.")
        parser.add_argument("output", help="output file path.")
        parser.set_defaults(func=combine_)


def combine_(args):
    """Concatenates netCDF datasets together.

    Args:
        args: Namespace object returned by ArgumentParser().parse_args().

    Raises:
        EnvironmentError if ncrcat and/or ncpdq are/is not found.
    """
    combine(args.datasets, args.output)

def combine(datasets, output):
    """Concatenates netCDF datasets together.

    Args:
        datasets: List of paths to input files.
        output: Path to output file.

    Raises:
        EnvironmentError if ncrcat and/or ncpdq are/is not found.
    """
    if which(ncrcat) is None or which(ncpdq) is None:
        raise EnvironmentError("you must have {} and {} installed.".format(ncrcat, ncpdq))
    cat(sorted(datasets), output)


def unpack(datasets, directory):
    """Unpacks datasets, to avoid any nasty surprises when running ncrcat.

    Args:
        datasets: List of netCDF dataset paths.
        directory: Directory where the unpacked datasets are stored.

    Returns:
        paths: List of unpacked netCDF datasets.
    """
    paths = []
    for dataset in datasets:
        paths.append(join(directory, basename(dataset)))
        run([ncpdq, "--unpack", dataset, paths[-1]], check=True)
    return paths


def cat(datasets, output):
    """Concatenates datasets together.

    Args:
        datasets: List of netCDF dataset paths.
        output: Path to the output netCDF dataset.
    """
    with TemporaryDirectory() as directory:
        paths = unpack(datasets, directory)
        run([ncrcat] + paths + [output], check=True)
