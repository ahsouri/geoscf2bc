# geoscf2bc

Create lateral boundary conditions from GEOS-CF for CMAQ. Like aqmbc, but specifically for GEOS-CF.

Overview
--------

I've been using GMAO's OpenDAP server to extract just the grid cells at
the border of a CMAQ simulation from the GEOS-CF 36-layer archives (met, xgc,
chm). These results are being used for Lateral Boundary Conditons for CMAQ.

The Current Process is described below, followed by a "how-to" for EPA's atmos
cluster. Finally, the directory structure is described with annotations.

Installation
------------

```bash
python -m pip install git+https://github.com/barronh/geoscf2bc.git
```

Application
-----------

The example described here creates a boundary condition file for CMAQ for
2024-01-01. A more detailed explanation is available in the
[example tutorial](example/README.md).


```python
from geoscf2bc.drivers import default

# This example makes its own GRIDDESC. Normally, you use your own.
with open('GRIDDESC', 'w') as gf:
    gf.write("""' '
'LamCon_40N_97W'
  2 33.0 45.0 -97.0 -97.0 40.0
' '
'36US3'
'LamCon_40N_97W' -2952000.0 -2772000.0 36000.0 36000.0 172 148 1
' '""")

# The example processes just a single day including 00Z of the next day.
outpaths = default(
    GDNAM='36US3', gdpath='GRIDDESC',
    SDATE='2024-01-01T00', EDATE='2024-01-02T00'
)
```

The main driver can also be called from the command line. This assumes you have
a GRIDDESC in your home directory.

```bash
python -m geoscf2bc --cffreq=3h --gdpath=~/GRIDDESC 12US1 2024-01-01T00 2024-01-02T00
```

Conceptual Process
------------------

1. Extract extract fields from GMAO's OpenDAP server
  * Sources
    * Met File (met)
      * meturl = 'https://opendap.nccs.nasa.gov/dods/gmao/geos-cf/assim/met_tavg_1hr_g1440x721_v36'
      * vars = ['zl', 'airdens', 'ps', 'delp', 'q']
    * 1hr average Chemistry (chm) File
      * chmurl = 'https://opendap.nccs.nasa.gov/dods/gmao/geos-cf/assim/chm_tavg_1hr_g1440x721_v36'
      * vars = all
    * eXtra GEOS-Chem (xgc) outputs File
      * xgcurl = 'https://opendap.nccs.nasa.gov/dods/gmao/geos-cf/assim/xgc_tavg_1hr_g1440x721_v36'
      * vars = all
  * Output: unique perimiter cell values in {GDNAM}/%Y/%m/%d/
2. Translate uses definitions that convert GEOS-CF variables to CMAQ
  * geoscf_met.txt : defines PRES, ZH, and DENS consistent with MCIP expectations
  * geoscf_cb6r4.txt : defines most gas-phase chemistry variables
  * geoscf_ae7.txt : defines aerosol-phase variables
3. Concatenate and Interpolate
  * CMAQ requires hourly files that overlap the entire simulation period (typically 1d)
  * If 3 hourly data was downloaded, then data is concatenated and interpolated to 1h intervals.
