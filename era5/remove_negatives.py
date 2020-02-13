"""Removes negative values from variables in a netCDF dataset."""
from netCDF4 import Dataset
from numpy import argwhere

from .commands import Command


class RemoveNegatives(Command):
    @staticmethod
    def arguments(subparsers):
        """Adds command specific command-line arguments.

        Args:
            subparsers: Special action object returned by ArgumentParser().add_subparsers().
        """
        command = "remove-negatives"
        parser = subparsers.add_parser(command, help="{} help.".format(command))
        parser.add_argument("dataset", help="Dataset to be modified.")
        parser.set_defaults(func=remove_negatives_)


def remove_negatives_(args):
    """Replaces negative values with a small positive value.

    Args:
        args: Namespace object returned by ArgumentParser().parse_args().
    """
    remove_negatives(args.dataset)


def remove_negatives(path):
    """Replaces negative values with a small positive value.

    Args:
        path: Path to netCDF dataset that will be modified.
    """
    blacklist = ["msdwlwrfcs", "msdwswrfcs", "msnlwrfcs", "msnswrfcs",
                 "mtdwswrf", "mtnlwrfcs", "mtnswrfcs"]
    with Dataset(path, "a") as dataset:
        blacklist += [x for x in dataset.dimensions.keys()]
        for name, v in dataset.variables.items():
            if name in blacklist:
                continue
            data = v[...]
            indices = argwhere(data < 0.)
            if indices.shape[0] == 0:
                continue
            scale, offset = v.getncattr("scale_factor"), v.getncattr("add_offset")
            smallest_positive = scale*(v.datatype.type(-1.*offset/scale) + 1) + offset
            for i in range(indices.shape[0]):
                v[tuple(indices[i,...])] = smallest_positive
