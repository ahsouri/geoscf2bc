__all__ = ['geoscf_extract']
__doc__ = """
# Extract GEOS-CF Data for use in BCON

---
    author: Barron H. Henderson
    date: 2023-01-16
    last update: 2024-02-26
---

The input is an OpenDAP file served by NASA GMAO for their analysis run of
GEOS-CF. The output is simply an extraction at boundary cells of a CMAQ Domain.

Updates:
* updated to extract a slice and then the perimiter from that slice.

Example Application
-------------------

    import geoscf2bc
    import pandas as pd
    dates = pd.date_range('2023-01-01 00', '2023-01-01 03', freq='3h')
    outpaths = geoscf2bc.extract.geoscf_extract(
        '12US1', '/home/bhenders/GRIDDESC', dates
    )
    print(len(outpaths), 'files')
    # 6 files
    # 3 from each hour extracted

Notes
-----

total wall time ~= 5min / hour * days / (8h / day)
One month costs about a day:
   20.7h = 5 min / hour * 31 days / (8h / day)
"""

import time
import warnings

warnings.simplefilter('ignore')


def tryandtime(tmpf, bcsubset, outpath, maxtries=10, verbose=0):
    """
    This function tries to download data in tmpf via OpenDAP. If it fails,
    then it tries again up to maxtries. The entire process is timed.

    Arguments
    ---------
    tmpf : xarray.Dataset
        File from GEOS-CF
    bcsubset : dict
        Mappable of slices
    outpath : str
        Path to archive results
    maxtries: int
        Number of times to retry if there is a failure.
    verbose: int
        Print logging data
    Returns
    -------
    dt : float
        Time elapsed.

    """
    import os

    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    if verbose > 0:
        print(outpath, end='', flush=True)
    if os.path.exists(outpath):
        if verbose > 0:
            print('cached', flush=True)
        dt = 0
    else:
        t0 = time.time()
        ntries = 0
        while not os.path.exists(outpath) and ntries < maxtries:
            ntries += 1
            try:
                # Might fail
                tmpf.load()
                # Unlikely to fail
                tmpf.sel(bcsubset).to_netcdf(outpath)
            except Exception as e:
                if verbose > 0:
                    print(str(e), end='.retry.', flush=True)

        t1 = time.time()
        dt = t1 - t0
        if verbose > 0:
            print(f'{dt:.0f}s ({ntries} tries)', flush=True)

    return dt


def geoscf_extract(GDNAM, gdpath, dates, sleep=60, verbose=0):
    """
    Arguments
    ---------
    GDNAM : str
        Grid definition name.
    gdpath : str
        Grid definition file path (GRIDDESC)
    dates : list
        Dates to process
    sleep : int
        Number of seconds to sleep in between requests.
    verbose : int
        Degree of verbosity

    Returns
    -------
    None
    """
    import xarray as xr
    import pandas as pd
    import os
    import PseudoNetCDF as pnc
    from collections import OrderedDict
    from .defs import griddescpath

    if gdpath is None:
        gdpath = griddescpath
    dates = pd.to_datetime(dates)

    os.makedirs(GDNAM, exist_ok=True)
    gf = pnc.pncopen(gdpath, format='griddesc', GDNAM=GDNAM, FTYPE=2)

    # perimiter lon/lat
    lonb = xr.DataArray(gf.variables['longitude'], dims=('PERIM',))
    latb = xr.DataArray(gf.variables['latitude'], dims=('PERIM',))

    if verbose > 0:
        print('GRID', 'ROWS', 'COLS', 'PERIM', flush=True)
        print(GDNAM, gf.NROWS, gf.NCOLS, lonb.size, flush=True)

    rooturl = 'https://opendap.nccs.nasa.gov/dods/gmao/geos-cf/assim'
    meturl = f'{rooturl}/met_tavg_1hr_g1440x721_v36'
    chmurl = f'{rooturl}/chm_tavg_1hr_g1440x721_v36'
    xgcurl = f'{rooturl}/xgc_tavg_1hr_g1440x721_v36'

    if verbose > 0:
        print('opening files', flush=True)

    mf = xr.open_dataset(meturl)
    cf = xr.open_dataset(chmurl)
    xf = xr.open_dataset(xgcurl)

    if verbose > 0:
        print('mapping PERIM to lon/lat', flush=True)

    lonidx = mf.lon.sel(lon=lonb, method='nearest')
    latidx = mf.lat.sel(lat=latb, method='nearest')

    locidx = pd.DataFrame(dict(
        lonb=lonb, latb=latb, lon=lonidx, lat=latidx, count=1
    )).set_index(['lonb', 'latb'])
    locuidx = locidx.groupby(['lat', 'lon'], as_index=True).count(
    ).reset_index()

    locidx.to_csv(f'{GDNAM}/{GDNAM}_locs.csv')

    metvars = ['zl', 'airdens', 'ps', 'delp', 'q', 't']

    # Define the slice that extracts a window of the original model
    wlonslice = slice(*locuidx.lon.quantile([0, 1]).values)
    wlatslice = slice(*locuidx.lat.quantile([0, 1]).values)
    # Define the slice that extracts the perimiter from the window (or original
    # model)
    plonslice = xr.DataArray(locuidx.lon, dims=('PERIM',))
    platslice = xr.DataArray(locuidx.lat, dims=('PERIM',))
    outpaths = []
    for startdate in dates:
        # slicing to avoid exact issues
        starttime = startdate.strftime('%Y-%m-%d %H:00')
        endtime = startdate.strftime('%Y-%m-%d %H:45')
        tv = mf.time.sel(time=slice(starttime, endtime)).values
        nhours = len(tv)
        # Tried subsetting time separately, it was horrific.
        wdwsubset = OrderedDict(time=tv, lon=wlonslice, lat=wlatslice)
        bcsubset = OrderedDict(lon=plonslice, lat=platslice)
        t0 = time.time()
        tmpmf = mf[metvars].sel(wdwsubset)
        times = pd.to_datetime(tmpmf.time.values).to_pydatetime()
        stime = times[0]
        etime = times[-1]

        outdir = f'{GDNAM}/{stime:%Y/%m/%d}'
        pathsuf = f'{stime:%Y-%m-%dT%H}_{etime:%Y-%m-%dT%H}_{nhours}h.nc'
        metpath = f'{outdir}/met_tavg_1hr_g1440x721_v36_{pathsuf}'
        chmpath = f'{outdir}/chm_tavg_1hr_g1440x721_v36_{pathsuf}'
        xgcpath = f'{outdir}/xgc_tavg_1hr_g1440x721_v36_{pathsuf}'

        if (
            os.path.exists(metpath)
            and os.path.exists(chmpath)
            and os.path.exists(xgcpath)
        ):
            print(
                'Skipping', starttime, endtime, 'cached', end='\r', flush=True
            )
            continue
        tmpcf = cf.sel(wdwsubset)
        tmpxf = xf.sel(wdwsubset)
        t1 = time.time()
        if verbose > 0:
            print(f'Load: {t1 - t0:.1}s', flush=True)
        if verbose > 0:
            print('Retrieve met', end='', flush=True)
        tryandtime(tmpmf, bcsubset, metpath, verbose=verbose)
        outpaths.append(metpath)
        if verbose > 0:
            print('Retrieve xgc', end='', flush=True)
        tryandtime(tmpxf, bcsubset, xgcpath, verbose=verbose)
        outpaths.append(xgcpath)
        if verbose > 0:
            print('Retrieve chm', end='', flush=True)
        tryandtime(tmpcf, bcsubset, chmpath, verbose=verbose)
        outpaths.append(chmpath)
        if len(dates) > 1:
            time.sleep(sleep)
