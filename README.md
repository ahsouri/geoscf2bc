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

% pip install git+https://github.com/barronh/geoscf2bc.git

Application
-----------

The example described here creates a boundary condition file for CMAQ for
2024-01-01.


```python
from geoscf2bc.drivers import default
outpaths = default(GDNAM='12US1', gdpath='GRIDDESC', '2024-01-01T00', '2024-01-02T00')
```

In doing so, it creates 38 file artifacts.
* 1 csv definition of the domain perimeter
* 4 files for each hour extracted from GEOS-CF.
  * At 3h (8x), that is 32 files for the first day, and
  * 1h for the 0Z of the next day, that is 4 more files
* 1 CMAQ-ready boundary conditon for 2024-01-01

```
./12US1
|   # Definition of perimeter cells from CMAQ in GEOS-cF
|-- 12US1_locs.csv
|-- 2022/01/01/
|   |   # Hourly chm, met, and xgc extracted from GEOS-CF at perimeter of domain
|   |-- chm_tavg_1hr_g1440x721_v36_2022-01-01T00_2022-01-01T%H_1h.nc
|   |-- met_tavg_1hr_g1440x721_v36_2022-01-01T00_2022-01-01T%H_1h.nc
|   |-- xgc_tavg_1hr_g1440x721_v36_2022-01-01T00_2022-01-01T%H_1h.nc
|   |   # Hourly CMAQ convention boundary condition file with just 1 time step.
|   |-- BCON_geoscf_cb6r3_ae7_12US1_2022-01-01T00_2022-01-01T%H_1h.nc
|   |   # 25h file appropriate for CMAQ lateral boundary conditions for 1 day.
|   `-- BCON_geoscf_cb6r3_ae7_12US1_2022-01-01T00_25h.nc
`-- 2022/01/02/
    |-- chm_tavg_1hr_g1440x721_v36_2022-01-02T00_2022-01-02T00_1h.nc
    |-- met_tavg_1hr_g1440x721_v36_2022-01-02T00_2022-01-02T00_1h.nc
    |-- xgc_tavg_1hr_g1440x721_v36_2022-01-02T00_2022-01-02T00_1h.nc
    `-- BCON_geoscf_cb6r3_ae7_12US1_2022-01-02T00_2022-01-02T00_00h.nc
```


The main driver can also be called from the command line.

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
