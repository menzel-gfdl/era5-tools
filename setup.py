from setuptools import setup

entry_points = {"console_scripts" : ["era5=era5.main:main"]}
setup(name="era5", version="alpha", packages=["era5",], entry_points=entry_points)
