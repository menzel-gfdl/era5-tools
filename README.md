# era5-tools

This repository contains tools specifically aimed at downloading/processing
ERA5 data for clear-sky radiative transfer calculations.

## Requirements
These tools are written in Python 3.5 (or later).  Required python packages
are listed in `requirements.txt` in the base of the repository.  Some features
also require the external tools `cdo`, `ncrcat`, and `ncpdq`.

## Potential Pitfalls

##### Pressure levels ignore orography
Data downloaded on "pressure levels" may contain values below Earth's surface.
Whether or not this occurs for a specific grid point can be determined
by comparing the pressure levels to the surface pressure at that point.
Surface pressure can be downloaded from the "single level" data product.

###### Scale and offset factors for a variable may vary between files
Many of the ERA5 variables in the netCDF files are provided as short
integers, which may be converted to floating-point using the included
`scale_factor` and `add_offset` attributes.  For any variable, these
`scale_factor` and `add_offset` attributes are not guaranteed to be
the same in two different files.  If the two or more files are combined
without first "unpacking" the data, differences in these `scale_factor`
and `add_offset` variables can introduce artificial noise into the data.
The common combining tool `ncrcat` does print a warning if it detects
differences in the `scale_factor` and `add_offset` attributes for a variable
between files, but continues to run and produces erroneous data.  For example,
running:

```
$ ncrcat file1.nc file2.nc output.nc
ncrcat: INFO/WARNING Multi-file concatenator encountered packing attribute add_offset
for variable alnid. NCO copies the packing attributes from the first file to the output
file. The packing attributes from the remaining files must match exactly those in the
first file or data from subsequent files will not unpack correctly. Be sure all input
files share the same packing attributes. If in doubt, unpack (with ncpdq -U) the input
files, then concatenate them, then pack the result (with ncpdq). This message is printed
only once per invocation.```

produces a file `output.nc` containing incorrect data for `alnid` and possibly
other variables.

##### Variables may contain non-physical negative values
I have found a few instances where some variables contain non-physical
negative values.  I suspect these negative values arise when the floating point
data is "offset" and "scaled" down to short integers.
