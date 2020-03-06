"""Downloads ERA5 data for radiation calculations from the Copernicus Data Store."""
from collections import namedtuple

from cdsapi import Client

from .commands import Command


class Download(Command):
    @staticmethod
    def arguments(subparsers):
        """Adds command specific command-line arguments.

        Args:
            subparsers: Special action object returned by ArgumentParser().add_subparsers().
        """
        command = "download"
        parser = subparsers.add_parser(command, help="{} help.".format(command))
        parser.add_argument("level_file", help="output file path for pressure level data.")
        parser.add_argument("single_file", help="output file path for single level data.")
        parser.add_argument("timescale", choices=["hourly", "monthly"])
        parser.add_argument("-y", help="Starting year.", type=int)
        parser.add_argument("-Y", help="Ending year.", type=int)
        parser.add_argument("-m", help="Starting month.", type=int)
        parser.add_argument("-M", help="Ending month.", type=int)
        parser.add_argument("-d", help="Starting day.", type=int)
        parser.add_argument("-D", help="Ending day.", type=int)
        parser.add_argument("-t", help="Starting hour.", type=int)
        parser.add_argument("-T", help="Ending hour.", type=int)
        parser.set_defaults(func=download_)


def download_(args):
    """Downloads ERA5 clear-sky radiation-related data.

    Args:
        args: Namespace object returned by ArgumentParser().parse_args().
    """
    download(args.level_file, args.single_file, args.timescale,
             args.y, args.Y, args.m, args.M, args.d, args.D, args.t, args.T)


def download(level_output, single_output, timescale, y, Y, m, M, d=None,
             D=None, t=None, T=None):
    """Download data from the Copernicus Data Store (CDS).  This requires an
       account, and associated credientials in a file $HOME/.cdsapirc.

    Args:
        level_output: Output file containing data on pressure levels.
        single_output: Output file containing data on single levels.
        y: Starting year.
        Y: Ending year.
        m: Starting month.
        M: Ending month.
    """
    client = Client()
    Product = namedtuple("Product", ("type", "level_name", "single_name"))
    monthly = Product(type="monthly_averaged_reanalysis",
                      level_name="reanalysis-era5-pressure-levels-monthly-means",
                      single_name="reanalysis-era5-single-levels-monthly-means")
    hourly = Product(type="reanalysis", level_name="reanalysis-era5-pressure-levels",
                     single_name="reanalysis-era5-single-levels")
    products = {"monthly" : monthly, "hourly" : hourly}

    years = tuple([x for x in range(y, Y+1)])
    months = tuple([x for x in range(m, M+1)])
    try:
        days = tuple([x for x in range(d, D+1)])
    except TypeError:
        days = None
    try:
        times = tuple([x for x in range(t, T+1)])
    except TypeError:
        times = None

    #Level variables.
    variables = ("ozone_mass_mixing_ratio", "specific_humidity", "temperature",
                 "fraction_of_cloud_cover", "specific_cloud_ice_water_content",
                 "specific_cloud_liquid_water_content")
    pressure_levels = (1, 2, 3, 5, 7, 10, 20, 30, 50, 70, 100, 125, 150, 175, 200,
                       225, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750,
                       775, 800, 825, 850, 875, 900, 925, 950, 975, 1000)
    retrieve(client, products[timescale].level_name, products[timescale].type, level_output,
             variables, years, months, days=days, times=times, pressure_levels=pressure_levels)

    #Surface and TOA variables.
    variables = ("near_ir_albedo_for_diffuse_radiation",
                 "near_ir_albedo_for_direct_radiation",
                 "skin_temperature",
                 "surface_pressure",
                 "toa_incident_solar_radiation",
                 "uv_visible_albedo_for_diffuse_radiation",
                 "uv_visible_albedo_for_direct_radiation",
                 "2m_temperature",
                 "mean_surface_downward_long_wave_radiation_flux_clear_sky",
                 "mean_surface_downward_short_wave_radiation_flux_clear_sky",
                 "mean_surface_net_long_wave_radiation_flux_clear_sky",
                 "mean_surface_net_short_wave_radiation_flux_clear_sky",
                 "mean_top_downward_short_wave_radiation_flux",
                 "mean_top_net_long_wave_radiation_flux_clear_sky",
                 "mean_top_net_short_wave_radiation_flux_clear_sky"
                 "mean_surface_downward_long_wave_radiation_flux",
                 "mean_surface_downward_short_wave_radiation_flux",
                 "mean_surface_downward_uv_radiation_flux",
                 "mean_surface_net_long_wave_radiation_flux",
                 "mean_surface_net_short_wave_radiation_flux",
                 "mean_top_downward_short_wave_radiation_flux",
                 "mean_top_net_long_wave_radiation_flux",
                 "mean_top_net_short_wave_radiation_flux")
    retrieve(client, products[timescale].single_name, products[timescale].type, single_output,
             variables, years, months, days=days, times=times)


def retrieve(client, name, product, output, variables, years, months, days=None, times=None,
             pressure_levels=None):
    """Helper function to facilitate the downloads from CDS.

    Args:
        client: cdsapi Client object.
        name: Dataset name.
        product: Dataset type.
        output: Name of the output file.
        variables: Tuple of variable names.
        years: Tuple of years.
        months: Tuple of months.
        days: Tuple of days.
        times: Tuple of times.
        pressure_levels: Tuple of pressure levels.
     """
    parameters = {"format" : "netcdf", "month" : ["{:02}".format(x) for x in months],
                  "product_type" : product, "variable" : variables,
                  "year": ["{:04d}".format(x) for x in years]}
    if days is not None:
        parameters["day"] = ["{:02d}".format(x) for x in days]
    if times is None:
        parameters["time"] = "00:00"
    else:
        parameters["time"] = ["{:02d}:00".format(x) for x in times]
    if pressure_levels is not None:
        parameters["pressure_level"] = [str(x) for x in pressure_levels]
    client.retrieve(name, parameters, output)
