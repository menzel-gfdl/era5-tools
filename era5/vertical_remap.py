"""Vertically remaps netCDF data."""
from netCDF4 import Dataset
from numpy import append, asarray, copy, linspace, moveaxis, ravel, reshape, searchsorted, zeros
from scipy.interpolate import interp1d

from .cf_netcdf import CfDataset, CfVariable
from .commands import Command
from .units_converter import basic_converter, pressure


class VerticalRemap(Command):
    @staticmethod
    def arguments(subparsers):
        """Adds command specific command-line arguments.

        Args:
            subparsers: Special action object returned by ArgumentParser().add_subparsers().
        """
        command = "vertical-remap"
        parser = subparsers.add_parser(command, help="{} help".format(command))
        parser.add_argument("level_file", help="File path for pressure level data.")
        parser.add_argument("single_file", help="File path for single level data.")
        parser.add_argument("output", help="Output file path.")
        parser.set_defaults(func=remap_)


def remap_(args):
    """Perform vertical remapping on an entire dataset using ERA interim a and b parameters.

    Args:
        args: Namespace object returned by ArgumentParser().parse_args().
    """
    remap(args.level_file, args.single_file, args.output),


def remap(level_file, single_file, output):
    era_interim_remapper.remap_all(level_file, single_file, output,
                                   "sp", {"t" : "t2m"}, basic_converter)


class VerticalRemapper(object):
    """Vertically remaps data to input sigma pressure grid.

    Attributes:
        a: Pressure parameters.
        b: Surface pressure coefficients.
        units: Units of the self.a pressure parameters.
        level_map: Map from pressure levels to a and b parameters.
    """

    def __init__(self, a, b, units, level_map):
        self.a = copy(a)
        self.b = copy(b)
        self.units = units
        self.level_map = level_map

    def pressure(self, surface_pressure, units, converter):
        """Calculates the pressures that the column will be remapped to.

        Args:
            surface_pressure: Surface pressure.
            units: Surface pressure units.
            converter: UnitsConverter object.
        """
        conversion = converter.convert(self.units, units)
        pressure = zeros(len(self.level_map))
        for i, level in enumerate(self.level_map):
            phalf_lower = self.a[level]*conversion + self.b[level]*surface_pressure
            phalf_upper = self.a[level+1]*conversion + self.b[level+1]*surface_pressure
            pressure[i] = 0.5*(phalf_lower + phalf_upper)
        return pressure


    def remap_column(self, variable, pressure, surface_pressure, pressure_units, converter,
                     fill_value=0):
        """Remap a column to new pressures.

        Args:
            variable: Column variable to remap.
            pressure: Pressures the column variable is currently specified at.
            surface_pressure: Surface pressure for the column.
            pressure_units: Units of the current pressure/surface pressure.
            converter: UnitsConverter object.
            fill_value: Value used for constant extrapolation outside current pressure bounds.

        Returns:
            The new column pressures and remapped column variable values.
        """
        interpolate = interp1d(pressure, variable, bounds_error=False, fill_value=fill_value)
        p = self.pressure(surface_pressure, pressure_units, converter)
        return p, interpolate(p)

    def remap_all(self, level_dataset, surface_dataset, output, surface_pressure,
                  surface_variables, converter):
        """Remap all variables that depend on a pressure axis.

        Args:
            level_dataset: Dataset containing variables on model "full" levels.
            surface_dataset: Dataset containing surface variable values.
            output: Path to the output dataset.
            surface_pressure: Name of the surface pressure variable.
            surface_variables: Dictionary mapping variable names to their surface names.
            converter: UnitsConverter object.
        """
        with CfDataset(level_dataset, "r") as level_data, \
             Dataset(surface_dataset, "r") as surface_data, \
             CfDataset(output, "w") as new_dataset:

            dimensions = tuple([x for x in level_data.dimension_variables])
            pressure_coordinates = tuple([x for x in level_data.pressure_coordinates])
            added_p = False
            for v in level_data.variables.values():
                if v in dimensions:
                    #Ignore dimension variables.  These will be copied automatically when
                    #they are used by the other variables.
                    continue
                variable = CfVariable(v, pressure_coordinates)
                if not variable.vertically_remappable:
                    #Directly copy all non-remappable variables.
                    new_dataset.copy_variable(variable.parent, level_data)
                    continue

                #Add a new pressure dimension and variable for the remappable quantities.
                coordinate = "sigma_level"
                names = [x.name for x in variable.parent.get_dims()]
                names[variable.pressure_index] = coordinate
                if not added_p:
                    sigma = new_dataset.create_coordinate(coordinate, len(self.level_map), int)
                    sigma.setncattr("positive", "down")
                    sigma[:] = linspace(1, len(self.level_map), num=len(self.level_map))[:]
                    remapped_p_name = "p"
                    attrs = {"units" : variable.pressure_units,
                             "standard_name" : "air_pressure"}
                    for name in names:
                        if name != names[variable.pressure_index]:
                            if name not in new_dataset.dimensions:
                                new_dataset.copy_dimension(level_data.dimensions[name])
                                new_dataset.copy_variable(level_data.variables[name], level_data)
                    remapped_p = new_dataset.create_variable(remapped_p_name, float,
                                                             names, attrs)
                    added_p = True
                else:
                    remapped_p = None

                #Create the remapped variable.
                remapped_v = new_dataset.createVariable(variable.parent.name,
                                                        variable.parent.datatype, names)
                for attr in variable.parent.ncattrs():
                    if attr != "_FillValue":
                        new_dataset.copy_attribute(variable.parent, attr)

                #Vertically remap the variable.
                if variable.parent.name in surface_variables:
                    sv = surface_data.variables[surface_variables[variable.parent.name]]
                    try:
                        conversion = converter.convert(sv.getncattr("units"),
                                                       variable.parent.getncattr("units"))
                    except KeyError:
                        conversion = 1.
                    sv = sv[...]*conversion
                else:
                    sv = None

                #Reshape data.  Make the variable 2d, with pressure as the fastest dimension.
                rs = moveaxis(variable.parent[...], variable.pressure_index, -1)
                new_shape = rs.shape
                x = reshape(rs, (variable.parent.size//variable.pressure.size,
                                 variable.pressure.size))
                y = zeros(x.shape)
                if sv is not None:
                    x_surface = ravel(sv[...])
                z = zeros(x.shape)

                #Find the indices where the data in the file is underground.
                sp = surface_data.variables[surface_pressure]
                conversion = converter.convert(sp.getncattr("units"), variable.pressure_units)
                sp = sp[...]*conversion
                indices = ravel(searchsorted(variable.pressure, sp))
                sp1d = ravel(sp)

                #Loop through each column and interpolate, adding in the surface values and
                #ignoring points undergound.
                for i in range(x.shape[0]):
                    if sv is None:
                        xs = x[i,indices[i]-1]
                    else:
                        xs = x_surface[i]
                    column = append(copy(x[i,:indices[i]]), xs)
                    p = append(copy(variable.pressure[:indices[i]]), sp1d[i])
                    z[i,:], y[i,:] = self.remap_column(column, p, sp1d[i],
                                                       variable.pressure_units, converter,
                                                       fill_value=column[0])
                if remapped_p is not None:
                    remapped_p[...] = moveaxis(reshape(z, new_shape), -1,
                                               variable.pressure_index)[...]
                remapped_v[...] = moveaxis(reshape(y, new_shape), -1,
                                           variable.pressure_index)[...]


a_era_interim = asarray([0.00, 0.20, 0.38, 0.64, 0.96,
                         1.34, 1.81, 2.35, 2.98, 3.74,
                         4.65, 5.76, 7.13, 8.84, 10.95,
                         13.56, 16.81, 20.82, 25.80, 31.96,
                         39.60, 49.07, 60.18, 73.07, 87.65,
                         103.76, 120.77, 137.75, 153.80, 168.19,
                         180.45, 190.28, 197.55, 202.22, 204.30,
                         203.84, 200.97, 195.84, 188.65, 179.61,
                         168.99, 157.06, 144.11, 130.43, 116.33,
                         102.10, 88.02, 74.38, 61.44, 49.42,
                         38.51, 28.88, 20.64, 13.86, 8.55,
                         4.67, 2.10, 0.66, 0.07, 0.00,
                         0.00])
b_era_interim = asarray([0.00000, 0.00000, 0.00000, 0.00000, 0.00000,
                         0.00000, 0.00000, 0.00000, 0.00000, 0.00000,
                         0.00000, 0.00000, 0.00000, 0.00000, 0.00000,
                         0.00000, 0.00000, 0.00000, 0.00000, 0.00000,
                         0.00000, 0.00000, 0.00000, 0.00000, 0.00008,
                         0.00046, 0.00182, 0.00508, 0.01114, 0.02068,
                         0.03412, 0.05169, 0.07353, 0.09967, 0.13002,
                         0.16438, 0.20248, 0.24393, 0.28832, 0.33515,
                         0.38389, 0.43396, 0.48477, 0.53571, 0.58617,
                         0.63555, 0.68327, 0.72879, 0.77160, 0.81125,
                         0.84737, 0.87966, 0.90788, 0.93194, 0.95182,
                         0.96765, 0.97966, 0.98827, 0.99402, 0.99763,
                         1.00000])
level_map_era_interim = (5, 7, 8, 11, 12,
                         14, 17, 19, 22, 23,
                         25, 26, 28, 29, 30,
                         31, 32, 33, 35, 36,
                         38, 39, 40, 42, 43,
                         44, 45, 46, 47, 48,
                         49, 50, 51, 52, 53,
                         55, 57)
era_interim_remapper = VerticalRemapper(a_era_interim, b_era_interim, "hPa",
                                        level_map_era_interim)
