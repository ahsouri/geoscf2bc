# geoscf2bc

Create lateral boundary conditions from GEOS-CF for CMAQ. Like aqmbc, but specifically for GEOS-CF.

Overview
--------

I've been using GMAO's OpenDAP server to extract just the grid cells at
the border of a CMAQ simulation from the GEOS-CF 36-layer archives (met, xgc,
chm). These results are being used for Lateral Boundary Conditons for CMAQ.

The Current Process is described below, followed by a "how-to" for EPA's atmos
cluster. Finally, the directory structure is described with annotations.

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

How-To
------

### Python Driver Interface

from geoscf2bc.drivers import default
outpaths = default(GDNAM='12US1', gdpath='GRIDDESC', '2024-01-01T00', '2024-01-02T00')


### Command Line Interface

The main driver system can do all the processing.

$ python -m geoscf2bc --cffreq=3h --gdpath=~/GRIDDESC 12US1 2024-01-01T00 2024-01-02T00

Optionally, you can run just the extract portion -- which can take a long time.

$ python -m geoscf2bc.extract --freq=3h --gdpath=~/GRIDDESC 12US1 2024-01-01T00 2024-01-02T00
