geoscf2bc Example
==================

The example provided here is a minimum working example for a single day. You should start by running this example as is. To do, so you first have to install. Then, run as-is. Finally, after the example is working, you can make changes and try again.

Step 1: Install
---------------

```bash
pip install git+https://github.com/barronh/geoscf2bc.git
```

Step 2: Run Example As-is
-------------------------

Running the script is easy, but it does take time. The example uses a small "TEST" domain in the western US. The TEST grid has huge grid cells (108km by 108km), which is not typical -- but  it should run faster than a normal domain (e.g., 12US1). Run the command below, and wait. Depending on your network and the server, it may take 30min.

```bash
python run.py
```

When the run is complete, it should have created 38 file artifacts.
* 1 csv definition of the domain perimeter
* 4 files for each hour extracted from GEOS-CF.
  * At 3h (8x), that is 32 files for the first day, and
  * 1h for the 0Z of the next day, that is 4 more files
* 1 CMAQ-ready boundary conditon for 2024-01-01

The TEST directory should look like this, but files with `%H` in the name will be repeated for 00, 03, 06, 09, 12, 15, 18, and 00+1day. The `BCON_geoscf_cb6r3_ae7_TEST_2024-01-01T00_25h.nc` should be ready for use with CMAQ using TEST domain for 2024-01-01.

```
./TEST
|   # Definition of perimeter cells from CMAQ in GEOS-cF
|-- TEST_locs.csv
|-- 2024/01/01/
|   |   # Hourly chm, met, and xgc extracted from GEOS-CF at perimeter of domain
|   |-- chm_tavg_1hr_g1440x721_v36_2024-01-01T00_2024-01-01T%H_1h.nc
|   |-- met_tavg_1hr_g1440x721_v36_2024-01-01T00_2024-01-01T%H_1h.nc
|   |-- xgc_tavg_1hr_g1440x721_v36_2024-01-01T00_2024-01-01T%H_1h.nc
|   |   # Hourly CMAQ convention boundary condition file with just 1 time step.
|   |-- BCON_geoscf_cb6r3_ae7_TEST_2024-01-01T00_2024-01-01T%H_1h.nc
|   |   # 25h file appropriate for CMAQ lateral boundary conditions for 1 day.
|   `-- BCON_geoscf_cb6r3_ae7_TEST_2024-01-01T00_25h.nc
`-- 2024/01/02/
    |-- chm_tavg_1hr_g1440x721_v36_2024-01-02T00_2024-01-02T00_1h.nc
    |-- met_tavg_1hr_g1440x721_v36_2024-01-02T00_2024-01-02T00_1h.nc
    |-- xgc_tavg_1hr_g1440x721_v36_2024-01-02T00_2024-01-02T00_1h.nc
    `-- BCON_geoscf_cb6r3_ae7_TEST_2024-01-02T00_2024-01-02T00_00h.nc
```


Step 3: Edit Example
--------------------

When you are comfortable running the examples, you can apply it to different dates or apply it to a different domain.

### Alternate Dates

To extend the dates, simply edit the SDATE and EDATE in run.py. Note that the GEOS-CF dataset starts in 2018. Years before that are not available at the time of this writing.

### Change Domains

To apply to a different domain, requires two basic steps. First, change the GRIDDESC file. Second, edit the GDNAM parameter to use the name of the grid you want to use.

To change the GRIDDESC, there are three options:
  1. edit the GRIDDESC file,
  2. replace it with your own, or
  3. edit gdpath to point to your GRIDDESC file.

Note that the TEST domain takes about 20 min per day, while the 12US1 takes more like 50 min per day. The bigger your domain, the more data must be unpacked and transferred.

Report Any Issues
-----------------

If you have any problems, feel free to open an issue at https://github.com/barronh/geoscf2bc/issues. 
