"""Extensions to netCDF4 classes to support vertical remapping."""
from re import match

from netCDF4 import Dataset

from .units_converter import basic_converter, pressure


class CfVariable(object):
    """Extension of the basic netCDF4 Variable class.

    Attributes:
        parent: netCDF4 Variable object.
        pressure: Array of pressure coordinate values.
        pressure_units: Pressure coordinate units.
        pressure_index: Index of the pressure coordinate.
        vertically_remappable: Flag telling if this variable is remappabled.
    """

    def __init__(self, variable, pressure_coordinates):
        self.parent = variable
        dimensions = [x.name for x in variable.get_dims()]
        for coordinate in pressure_coordinates:
            if coordinate.name != variable.name and coordinate.name in dimensions:
                self.pressure = coordinate[...]
                self.pressure_units = coordinate.getncattr("units")
                self.pressure_index = dimensions.index(coordinate.name)
                self.vertically_remappable = True
                break
        else:
            self.vertically_remappable = False


class CfDataset(Dataset):
    """Extentsion to the basic netCDF dataset class, assuming some CF conventions."""

    def create_coordinate(self, name, length, datatype, attrs=None):
        """Creates a new dimension and dimension variable.

        Args:
            name: Dimension name.
            length: Dimension size.
            datatype: Dimension variable type.
            attrs: Dictionary of attributes.

        Returns:
            Variable object for the new dimension.
        """
        self.createDimension(name, length)
        return self.create_variable(name, datatype, (name,), attrs)

    def create_variable(self, name, datatype, dimensions, attrs=None):
        """Creates a new variable.

        Args:
            name: Dimension name.
            datatype: Dimension variable type.
            dimensions: Tuple of dimension names.
            attrs: Dictionary of attributes.

        Returns:
            Variable object for the new variable.
        """
        v = self.createVariable(name, datatype, dimensions)
        if attrs is not None:
            v.setncatts(attrs)
        return v

    def copy_attribute(self, variable, name):
        """Copies an attribute from a variable in another dataset.

        Args:
            variable: Data from another dataset.
            name: Name of attribute to copy.
        """
        self.variables[variable.name].setncattr(name, variable.getncattr(name))

    def copy_dimension(self, dimension):
        """Copies a dimension from another dataset.

        Args:
            dimension: Dimension from another dataset.

        Returns:
            The dimension in the current dataset.
        """
        return self.createDimension(dimension.name, size=dimension.size)

    def copy_variable(self, variable, dataset):
        """Copies an entire variable from another dataset.

        Args:
            variable: Variable from another dataset.

        Returns:
            The variable in the current dataset.
        """
        v = self.copy_variable_metadata(variable, dataset)
        self.copy_variable_data(variable)
        return v

    def copy_variable_metadata(self, variable, dataset):
        """Copies the metadata (dimensions and attributes) from a variable in another dataset.

        Args:
            variable: Variable from another dataset.

        Returns:
            The variable in the current dataset.
        """
        for dimension in variable.get_dims():
            try:
                self.copy_dimension(dimension)
                self.copy_variable(dataset.variables[dimension.name], dataset)
            except RuntimeError:
                if dimension.size != self.dimensions[dimension.name].size:
                    raise
        names = [x.name for x in variable.get_dims()]
        fill = None if "_FillValue" not in variable.ncattrs() else variable.getncattr("_FillValue")
        v = self.createVariable(variable.name, variable.datatype, names, fill_value=fill)
        for attr in variable.ncattrs():
            if attr != "_FillValue":
                self.copy_attribute(variable, attr)
        return v

    def copy_variable_data(self, variable):
        """Copies a variable's data from another dataset.

        Args:
            variable: Variable from another dataset.
        """
        v = self.variables[variable.name]
        v[...] = variable[...]

    @property
    def dimension_variables(self):
        """Grabs dimension variables.

        Yields:
            Variable objects for each dimension.
        """
        for name in self.dimensions.keys():
            yield self.variables[name]

    def is_pressure_coordinate(self, variable):
        """Determine if a dimension variable is a pressure coordinate.

        Args:
            variable: Variable object.

        Returns:
            Flag telling if the dimension is a pressure coordinate.
        """
        for unit in basic_converter.units:
            if match(unit.regex, variable.getncattr("units")) and unit.type == pressure:
                return True
        return False

    @property
    def pressure_coordinates(self):
        """Grabs pressure coordinates.

        Yields:
            Variable objects for each pressure coordinate.
        """
        for variable in self.dimension_variables:
            if self.is_pressure_coordinate(variable):
                yield variable

    @property
    def vertical_coordinates(self):
        """Grabs vertical coordinates.

        Yields:
            Variable objects for all vertical coordinates.
        """
        sense = ("up", "down")
        for variable in self.dimension_variables:
            if self.is_pressure_coordinate(variable):
                yield variable
            attrs = variable.ncattrs()
            if "positive" in attrs and variable.getncattr("positive").lower() in sense:
                yield variable
            if "axis" in attrs and variable.getncattr("axis") == "Z":
                yield variable
