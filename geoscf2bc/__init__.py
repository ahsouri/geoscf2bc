__all__ = ['extract', 'translate', 'cmaqready', 'drivers']
__doc__ = """
Overview
--------

Extract concentrations and meteorology from GEOS-CF to create lateral boundary
conditons for CMAQ. If the files are local, you should use aqmbc. This software
is specifically to utilize OpenDAP with GEOS-CF.

Examples
--------

Within Python:

    from geoscf2bc.drivers import default
    gdpath = '/home/bhenders/GRIDDESC'
    outpaths = default('12US1', gdpath, '2024-01-01T00', '2024-01-02T00')
    print(len(outpaths))
    print('e.g.', outpaths[0])

As a script:

    $ python -m geoscf2bc 12US1 2024-01-01T00 2024-01-02T00
"""
from . import extract
from . import drivers
from . import translate
from . import cmaqready

__version__ = '0.2'
