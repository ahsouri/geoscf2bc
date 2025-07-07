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
import os
import numpy as np

warnings.simplefilter('ignore')

# Function to get file patterns for a given date
def get_file_paths(date, file_type):
    """
    Get file paths for a specific date and file type
    file_type should be 'met', 'chm', or 'xgc'
    """
    date_str = date.strftime('%Y%m%d')
    year = date.strftime('%Y')
    month = date.strftime('%m')
    day = date.strftime('%d')
    base_path = "/discover/nobackup/projects/gmao/geos_cf/pub/GEOS-CF_NRT/ana"
    # Construct the directory path - you may need to adjust this based on actual structure
    dir_path = f'{base_path}/Y{year}/M{month}/D{day}'
    
    # File naming pattern - adjust based on actual GEOS-CF file naming convention
    file_pattern = f'GEOS-CF.v01.rpl.{file_type}_tavg_1hr_g1440x721_v36.{date_str}_*.nc4'
    #print(file_pattern)
    return dir_path, file_pattern

# For processing multiple files, we'll need to open them differently
# Since we're reading local files, we can use glob to find matching files
import glob
import xarray as xr

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
    import pandas as pd
    print("trying")
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
                    now = pd.to_datetime('now', utc=True)
                    msg = f'\n{now:%Y-%m-%dT%H:%M:%S.%f}: {str(e)}'
                    print(msg, end='.retry\n', flush=True)

        t1 = time.time()
        dt = t1 - t0
        if verbose > 0:
            print(f'{dt:.0f}s ({ntries} tries)', flush=True)

    return dt

def clean_dataset_attributes(ds):
    """Remove problematic attributes that can cause HDF5 errors"""
    import copy
    
    # Create a copy to avoid modifying the original
    ds_clean = ds.copy()
    
    # List of potentially problematic attributes
    problematic_attrs = [
        '_ChunkSizes', '_DeflateLevel', '_Shuffle', '_Fletcher32',
        '_Storage', '_Endianness', '_NoFill', '_Compression',
        'chunks', 'preferred_chunks'
    ]
    
    # Clean global attributes
    for attr in problematic_attrs:
        if attr in ds_clean.attrs:
            del ds_clean.attrs[attr]
    
    # Clean variable attributes
    for var_name in ds_clean.variables:
        for attr in problematic_attrs:
            if attr in ds_clean[var_name].attrs:
                del ds_clean[var_name].attrs[attr]
        
        # Also remove encoding that might cause issues
        if hasattr(ds_clean[var_name], 'encoding'):
            ds_clean[var_name].encoding = {}
    
    return ds_clean

def process_and_save(tmpf, bcsubset, outpath, verbose=0):
    """
    Process data from tmpf and save to outpath with attribute cleaning.
    """
    import os
    import time
    
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    
    if verbose > 0:
        print(outpath, end='', flush=True)
    
    if os.path.exists(outpath):
        if verbose > 0:
            print(' cached', flush=True)
        dt = 0
    else:
        t0 = time.time()
        
        # Process the data
        subset_data = tmpf.sel(bcsubset)
            
        # Clean problematic attributes
        clean_data = clean_dataset_attributes(subset_data)
            
        # Save with explicit encoding to avoid HDF5 issues
        encoding = {}
        for var in clean_data.data_vars:
                encoding[var] = {
                    'zlib': True,
                    'complevel': 1,
                    '_FillValue': None
                }
            
        clean_data.to_netcdf(outpath, encoding=encoding)
            
        t1 = time.time()
        dt = t1 - t0
        if verbose > 0:
                print(f' {dt:.1f}s', flush=True)
        #except Exception as e:
        #print(f' ERROR: {str(e)}', flush=True)
        #dt = 0
            
    return dt

def open_dataset_from_files(dates, file_type):
    """
    Open dataset from local files for given dates and file type
    """
    all_files = []
    for date in dates:
        dir_path, file_pattern = get_file_paths(date, file_type)
        file_path = os.path.join(dir_path, file_pattern)
        matching_files = glob.glob(file_path)
        all_files.extend(matching_files)
    
    if not all_files:
        raise FileNotFoundError(f"No files found for {file_type}")
    
    # Sort files to ensure proper time ordering
    all_files.sort()
    #print(all_files)
    # Open multiple files as a single dataset
    return xr.open_mfdataset(all_files, combine='by_coords')


def geoscf_extract(GDNAM, gdpath, dates, ftype=2, sleep=60, verbose=1):
    """
    Arguments
    ---------
    GDNAM : str
        Grid definition name.
    gdpath : str
        Grid definition file path (GRIDDESC)
    dates : list
        Dates to process
    ftype : int
        Type 2=bcon; 1=icon
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
    sfx = {1: 'ICON', 2: 'BCON'}[ftype]
    gf = pnc.pncopen(gdpath, format='griddesc', GDNAM=GDNAM, FTYPE=ftype)

    # perimiter lon/lat
    dims = ('CELLS',)
    lonb = xr.DataArray(gf.variables['longitude'].ravel(), dims=dims)
    latb = xr.DataArray(gf.variables['latitude'].ravel(), dims=dims)
    print(np.size(lonb))
    print(np.size(latb))
    if verbose > 0:
        print('GRID', 'ROWS', 'COLS', 'CELLS', flush=True)
        print(GDNAM, gf.NROWS, gf.NCOLS, lonb.size, flush=True)

    try:
       print("Reading mf...")
       mf = open_dataset_from_files(dates, 'met')
       print("Reading cf...")
       cf = open_dataset_from_files(dates, 'chm')
       print("Reading xf...")
       xf = open_dataset_from_files(dates, 'xgc')
    except FileNotFoundError as e:
       print(f"Error opening files: {e}")
       print("Please check the file paths and naming conventions")
    # You may need to adjust the file paths based on actual structure
    if verbose > 0:
       print('mapping PERIM to lon/lat', flush=True)

    lonidx = mf.lon.sel(lon=lonb, method='nearest')
    latidx = mf.lat.sel(lat=latb, method='nearest')
    locidx = pd.DataFrame(dict(
        lonb=lonb, latb=latb, lon=lonidx, lat=latidx, count=1
    )).set_index(['lonb', 'latb'])
    locuidx = locidx.groupby(['lat', 'lon'], as_index=True).count(
    ).reset_index()

    locidx.to_csv(f'{GDNAM}/{GDNAM}_{sfx}.csv')

    metvars = ['zl', 'airdens', 'ps', 'delp', 'q', 't']
    metvars_upper = [var.upper() for var in metvars]
    metvars = metvars_upper
    # Define the slice that extracts a window of the original model
    wlonslice = slice(*locuidx.lon.quantile([0, 1]).values)
    wlatslice = slice(*locuidx.lat.quantile([0, 1]).values)
    # Define the slice that extracts the perimiter from the window (or original
    # model)
    plonslice = xr.DataArray(locuidx.lon, dims=('CELLS',))
    platslice = xr.DataArray(locuidx.lat, dims=('CELLS',))
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
        pathsuf = f'{stime:%Y-%m-%dT%H}_{etime:%Y-%m-%dT%H}_{nhours}h_{sfx}.nc'
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
            print('Retrieve met ', end='', flush=True)
        process_and_save(tmpmf, bcsubset, metpath, verbose=verbose)
        outpaths.append(metpath)
        if verbose > 0:
            print('Retrieve xgc ', end='', flush=True)
        process_and_save(tmpxf, bcsubset, xgcpath, verbose=verbose)
        outpaths.append(xgcpath)
        if verbose > 0:
            print('Retrieve chm ', end='', flush=True)
        process_and_save(tmpcf, bcsubset, chmpath, verbose=verbose)
        outpaths.append(chmpath)
        if len(dates) > 1:
            time.sleep(sleep)
