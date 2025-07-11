# geoscf2bc


Amir: I've forked this repo so that I can tune it to work with the actual GEOS-CF files stored on NASA's discover without having to download the data as part of the process. 



Create lateral boundary conditions from GEOS-CF for CMAQ. Like aqmbc, but specifically for GEOS-CF.

Overview
--------

I've been using GMAO's OpenDAP server to extract GEOS-CF composition from cells
at the perimeter of a CMAQ domain from the GEOS-CF 36-layer archives (met, xgc,
chm). These results are being used for Lateral Boundary Conditons for CMAQ.

For more information on GEOS-CF, see https://gmao.gsfc.nasa.gov/weather_prediction/GEOS-CF/docs/.

The geoscf2bc installation, application, and conceptual process are described below.

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

# The example processes just a single day including 00Z of the next day.
# It uses a built-in GRIDDESC. To provide your own, change gdpath:
# gdpath='/path/to/your/GRIDDESC'
gdpath = None
outpaths = default(
    GDNAM='36US3', gdpath=gdpath, SDATE='2024-01-01T00', EDATE='2024-01-02T00'
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
