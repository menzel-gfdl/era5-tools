"""Units conversion calculator."""
from collections import namedtuple
from re import match


class UnitsError(Exception):
    pass


Conversion = namedtuple("Conversion", ("regex", "factor", "type"))


class UnitsConverter(object):
    """A simple framework for converting units.

    Attributes:
        units: Tuple of Conversion namedtuples.
    """

    def __init__(self, units):
        self.units = units

    def convert(self, source, destination):
        """Converts from one set of units (source) to another (destination).

        Args:
            source (string): Units to convert from.
            destination (string): Units to convert to.

        Returns:
            Conversion factor from source to destination.

        Raises:
            UnitsError if source and destination are not compatible.
        """
        type1, to_si = self.to_si(source)
        type2, from_si = self.from_si(destination)
        if type1 == type2:
            return to_si*from_si
        raise UnitsError("Cannot convert {} to {}.".format(source, destination))

    def from_si(self, units):
        """Converts from SI to units.

        Args:
            units (string): Units to convert to.

        Returns:
            Units type and conversion factor from SI to units.
        """
        type_, factor = self.to_si(units)
        return type_, 1./factor

    def to_si(self, units):
        """Converts unit to SI.

        Args:
            units (string): Units to convert from.

        Returns:
            Units type and conversion factor from units to SI.

        Raises:
            UnitsError if units not found in the converter.
        """
        for unit in self.units:
            if match(unit.regex, units):
                return unit.type, unit.factor
        raise UnitsError("{} not found in converter.".format(units))


class Units(object):
    def __init__(self, current=0, distance=0, intensity=0, mass=0, mole=0,
                 temperature=0, time=0):
        self.current = current
        self.distance = distance
        self.intensity = intensity
        self.mass = mass
        self.mole = mole
        self.temperature = temperature
        self.time = time

    def __eq__(self, y):
        return all([value == getattr(y, key) for key, value in vars(self).items()])

    def __mul__(self, y):
        return Units(**{key: value + getattr(y, key) for key, value in vars(self).items()})

    def __truediv__(self, y):
        return Units(**{key: value - getattr(y, key) for key, value in vars(self).items()})


#Fundamental units.
current = Units(current=1)
distance = Units(distance=1)
intensity = Units(intensity=1)
mass = Units(mass=1)
mole = Units(mole=1)
temperature = Units(temperature=1)
time = Units(time=1)

#Derived units.
velocity = distance/time
acceleration = velocity/time
force = mass*velocity
area = distance*distance
volume = distance*area
pressure = force/area


_default = (Conversion(regex=r"(m|[Mm]eter(s)?)$", factor=1., type=distance),
            Conversion(regex=r"(atm|[Aa]tmosphere(s)?)$", factor=101325., type=pressure),
            Conversion(regex=r"[Bb]ar(s)?$", factor=100000., type=pressure),
            Conversion(regex=r"([Dd]eci)bar(s)$", factor=10000., type=pressure),
            Conversion(regex=r"(hPa|mb|([Mm]|[Mm]illi)bar(s)?)$", factor=100., type=pressure),
            Conversion(regex=r"(Pa|[Pp]ascal(s)?)$", factor=1., type=pressure),
            Conversion(regex=r"K$", factor=1., type=temperature))
basic_converter = UnitsConverter(_default)
"""Basic converter, provided for convenience."""
