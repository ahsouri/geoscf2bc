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

.. code-block:: python

    from geoscf2bc.drivers import default
    gdpath = './GRIDDESC'
    outpaths = default('12US1', gdpath, '2024-01-01T00', '2024-01-02T00')
    print(len(outpaths), 'outputs')
    # 1 outputs
    print('e.g.', outpaths[0])
    # 12US1/2024/01/01/BCON_geoscf_cb6r3_ae7_12US1_2024-01-01T00_25h.nc

As a script:

.. code-block:: bash

    $ python -m geoscf2bc 12US1 2024-01-01T00 2024-01-02T00
"""
from . import extract
from . import drivers
from . import translate
from . import cmaqready

__version__ = '0.3.0'
