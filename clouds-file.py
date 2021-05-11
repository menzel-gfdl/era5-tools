from argparse import ArgumentParser
from datetime import datetime, timedelta
from os import getcwd
from os.path import join
from re import match
from shutil import copyfile
from tempfile import TemporaryDirectory

from netCDF4 import Dataset
from numpy import argwhere, copy

from era5.horizontal_remap import remap as remaph
from era5.vertical_remap import remap as remapv


def get_surface_pressure(path, output, era5_dir, surface_pressure_name="sp"):
    """Put all the necessary ERA5 surface pressures into a single netCDF dataset so
       they can be used to do the vertical remapping.

    Args:
        path: Path to the input dataset.
        output: Path of the output dataset.
        era5_dir: Directory with ERA5 monthly mean inputs (1 year per file).
        surface_pressure_name: ERA5 variable name for surface pressure.
    """
    print("gathering surface pressures ... ")
    with Dataset(path, "r") as dataset, Dataset(output, "w") as surface:
        v = dataset.variables["time"]
        units = v.getncattr("units")
        values = match(r"days since ([0-9]+)-([0-9]+)-([0-9]+) ([0-9]+):([0-9]+):([0-9]+)",
                       units)
        start_time = datetime(int(values.group(1)), int(values.group(2)), int(values.group(3)),
                              hour=int(values.group(4)),  minute=int(values.group(5)),
                              second=int(values.group(6)), tzinfo=None)
        surface.createDimension("time")
        new_time_var = surface.createVariable("time", int, ("time",))
        new_time_var.setncattr("units", units)
        current_dataset = None
        for i in range(len(v)):
            new_time_var[i] = v[i]
            current_time = start_time + timedelta(days=int(v[i]))
            path = join(era5_dir, "{}-era5.nc".format(current_time.year))
            if current_dataset is None or path != str(current_dataset.filepath()):
                print("new path: {}".format(path))
                if current_dataset is not None: current_dataset.close()
                try:
                    current_dataset = Dataset(path, "r")
                except FileNotFoundError:
                    break
                sp = current_dataset.variables[surface_pressure_name]
            if surface_pressure_name not in surface.variables.keys():
                for dim in sp.dimensions:
                    if dim not in surface.dimensions.keys():
                        surface.createDimension(dim, current_dataset.dimensions[dim].size)
                p = surface.createVariable(sp.name, sp.dtype, sp.dimensions)
                p.setncattr("units", sp.getncattr("units"))
            p[i, ...] = sp[current_time.month - 1, ...]


def remove_fill_values(path):
    print("removing fill values ... ")
    with Dataset(path, "a") as dataset:
        for name in ["cc", "lwp_cc", "iwp_cc"]:
            v = dataset.variables[name]
            data = copy(v[...])
            indices = argwhere(data > 1.e30)
            for i in range(indices.shape[0]):
                v[tuple(indices[i, ...])] = 0.


def reverse_z(path):
    print("reversing z ... ")
    with Dataset(path, "a") as dataset:
        v = dataset.variables["pressure"]
        p = copy(v[::-1])
        v[...] = p[...]
#       for name in ["cc", "lwp_cc", "iwp_cc"]:
#           v = dataset.variables[name]
#           data = copy(v[:, ::-1, :, :])
#           v[...] = data[...]


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("path", help="input netcdf dataset.")
    parser.add_argument("output", help="output netcdf dataset.")
    args = parser.parse_args()
    with TemporaryDirectory() as directory:
        new_file = join(directory, "new.nc")
        copyfile(args.path, new_file)
#       remove_fill_values(new_file)
        reverse_z(new_file)
        lonlat_remapped_file = join(directory, "lonlat-remap.nc")
        remaph(new_file, lonlat_remapped_file, nlon=144, nlat=90)
        surface_pressure_file = join(directory, "sp-new.nc")
        get_surface_pressure(lonlat_remapped_file, surface_pressure_file,
                             "/archive/rlm/era5-prp")
#       z_remapped_file = join(directory, "z-remap.nc")
        z_remapped_file = join(getcwd(), "z-remap.nc")
        remapv(lonlat_remapped_file, surface_pressure_file, z_remapped_file)
        copyfile(z_remapped_file, join(getcwd(), args.output))
