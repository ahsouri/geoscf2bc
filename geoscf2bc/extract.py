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
import pandas as pd
import netCDF4 as nc
from datetime import datetime

warnings.simplefilter('ignore')

from joblib import Parallel, delayed
from collections import OrderedDict

def process_single_date(startdate, mf, cf, xf, metvars, wlonslice, wlatslice, plonslice, platslice, 
                        GDNAM, sfx, verbose=0, sleep=0):
    # slicing to avoid exact issues
    starttime = startdate.strftime('%Y-%m-%d %H:00')
    endtime = startdate.strftime('%Y-%m-%d %H:45')
    tv = mf.time.sel(time=slice(starttime, endtime)).values
    nhours = len(tv)
    print("Step3")
    # Tried subsetting time separately, it was horrific.
    wdwsubset = OrderedDict(time=tv, lon=wlonslice, lat=wlatslice)
    bcsubset = OrderedDict(lon=plonslice, lat=platslice)
    print("step4")
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

    # Create output directory if it doesn't exist
    os.makedirs(outdir, exist_ok=True)
    
    # Check if all files exist and skip if they do
    if os.path.exists(metpath) and os.path.exists(chmpath) and os.path.exists(xgcpath):
        if verbose > 0:
            print(f'Skipping {starttime} {endtime} (cached)')
        return []
    
    tmpcf = cf.sel(wdwsubset)
    tmpxf = xf.sel(wdwsubset)
    t1 = time.time()
    
    if verbose > 0:
        print(f'Load: {t1 - t0:.1f}s', flush=True)
        print(f'Processing {starttime}-{endtime}')
    
    local_outpaths = []
    
    if verbose > 0:
        print(f'Retrieve met for {starttime}', end='', flush=True)
    print("step5")
    process_and_save(tmpmf, bcsubset, metpath, verbose=verbose)
    local_outpaths.append(metpath)
    
    if verbose > 0:
        print(f'Retrieve xgc for {starttime}', end='', flush=True)
    process_and_save(tmpxf, bcsubset, xgcpath, verbose=verbose)
    local_outpaths.append(xgcpath)
    
    if verbose > 0:
        print(f'Retrieve chm for {starttime}', end='', flush=True)
    process_and_save(tmpcf, bcsubset, chmpath, verbose=verbose)
    local_outpaths.append(chmpath)
    
    return local_outpaths

# Main function that uses joblib to parallelize processing
def process_dates_parallel(dates, mf, cf, xf, metvars, wlonslice, wlatslice, plonslice, platslice, 
                           GDNAM, sfx, n_jobs=-1, verbose=0, sleep=0):
    """
    Process dates in parallel using joblib
    
    Parameters:
    -----------
    dates: list of datetime objects
        Dates to process
    n_jobs: int
        Number of parallel jobs. -1 means using all processors
    """
    results = Parallel(n_jobs=n_jobs, verbose=10)(
        delayed(process_single_date)(
            startdate, mf, cf, xf, metvars, wlonslice, wlatslice, plonslice, platslice,
            GDNAM, sfx, verbose=max(0, verbose-1), sleep=sleep
        ) for startdate in dates
    )

    # Maintain original order: results are returned in same order as input dates
    outpaths = []
    for date_results in results:  # This preserves date order
        outpaths.extend(date_results)  # This preserves met->xgc->chm order within each date
    
    return outpaths    

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
        return dt
    else:
        t0 = time.time()
        print("step 6")
        # Process the data
        subset_data = tmpf.sel(bcsubset)
        encoding = {}
        for var in subset_data.variables:
            # Remove chunking, use compression only
            encoding[var] = {
              '_FillValue': None,
              'zlib': True,
              'complevel': 1,
              'chunksizes': None  # Disable explicit chunking
            }

        print("step 7")
        #subset_data.to_netcdf(outpath,engine='scipy',format='NETCDF3_64BIT')
        clean_data = subset_data
        # Create new netCDF4 file



    # Create new netCDF4 file
    with nc.Dataset(outpath, 'w', format='NETCDF4') as ncfile:
    
        # Create dimensions
        for dim_name, dim_size in clean_data.dims.items():
            ncfile.createDimension(dim_name, dim_size)
    
        # Create coordinate variables first
        for coord_name in clean_data.coords:
            coord_data = clean_data[coord_name]
        
            # Check if it's a datetime variable
            if np.issubdtype(coord_data.dtype, np.datetime64):
                # Convert datetime64 to days since a reference date
                reference_date = datetime(1900, 1, 1)  # Common reference
            
                # Convert to numeric (days since reference)
                try:
                    # First convert datetime64[ns] to datetime objects
                    datetime_objects = coord_data.values.astype('datetime64[s]').astype(datetime)
                
                    # Then convert to numeric values using netCDF4's function
                    numeric_data = nc.date2num(
                        datetime_objects,
                        units=f'days since {reference_date.strftime("%Y-%m-%d %H:%M:%S")}',
                        calendar='gregorian'
                    )
                
                    # Create variable as float64
                    var = ncfile.createVariable(
                        coord_name, 
                        'f8',  # float64
                        coord_data.dims,
                        zlib=True,
                        complevel=4
                    )
                
                    # Write numeric data
                    var[:] = numeric_data
                
                    # Add time attributes
                    var.units = f'days since {reference_date.strftime("%Y-%m-%d %H:%M:%S")}'
                    var.calendar = 'gregorian'
                    var.long_name = coord_data.attrs.get('long_name', coord_name)
                
                except Exception as e:
                    print(f"Error converting datetime for {coord_name}: {e}")
                    # Fallback: store as strings
                    string_dates = np.array([str(d) for d in coord_data.values])
                    var = ncfile.createVariable(coord_name, 'S50', coord_data.dims)
                    var[:] = string_dates
        
            else:
                # Create variable with original datatype
                var = ncfile.createVariable(
                    coord_name, 
                    coord_data.dtype, 
                    coord_data.dims,
                    zlib=True,
                    complevel=4
                )
            
                # Write data
                var[:] = coord_data.values
            
                # Add minimal attributes if needed
                var.units = coord_data.attrs.get('units', '')
                var.long_name = coord_data.attrs.get('long_name', coord_name)
    
        # Create data variables
        for var_name in clean_data.data_vars:
            var_data = clean_data[var_name]
        
            # Check if it's a datetime variable
            if np.issubdtype(var_data.dtype, np.datetime64):
                # Convert datetime64 to days since a reference date
                reference_date = datetime(1900, 1, 1)
            
                try:
                    # Convert to datetime objects then to numeric
                    datetime_objects = var_data.values.astype('datetime64[s]').astype(datetime)
                    numeric_data = nc.date2num(
                        datetime_objects,
                        units=f'days since {reference_date.strftime("%Y-%m-%d %H:%M:%S")}',
                        calendar='gregorian'
                    )
                
                    # Create variable
                    var = ncfile.createVariable(
                        var_name,
                        'f8',
                        var_data.dims,
                        zlib=True,
                        complevel=4,
                        fill_value=None
                    )
                
                    # Write data
                    var[:] = numeric_data
                
                    # Add time attributes
                    var.units = f'days since {reference_date.strftime("%Y-%m-%d %H:%M:%S")}'
                    var.calendar = 'gregorian'
                    var.long_name = var_data.attrs.get('long_name', var_name)
                
                except Exception as e:
                    print(f"Error converting datetime for {var_name}: {e}")
                    # Fallback to string representation
                    string_dates = np.array([str(d) for d in var_data.values])
                    var = ncfile.createVariable(var_name, 'S50', var_data.dims)
                    var[:] = string_dates
            else:
                # Create variable
                var = ncfile.createVariable(
                    var_name,
                    var_data.dtype,
                    var_data.dims,
                    zlib=True,
                    complevel=4,
                    fill_value=None
                )
            
                # Write data
                var[:] = var_data.values
            
                # Add minimal attributes if needed
                var.units = var_data.attrs.get('units', '')
                var.long_name = var_data.attrs.get('long_name', var_name)
    
        # Add global attributes (minimal)
        ncfile.title = "Processed data"
        ncfile.history = f"Created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        print("step 8")
        #clean_data.to_netcdf(outpath)
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
    if verbose > 0:
        print('GRID', 'ROWS', 'COLS', 'CELLS', flush=True)
        print(GDNAM, gf.NROWS, gf.NCOLS, lonb.size, flush=True)
    print("step1")
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

    print("step2")
    outpaths = process_dates_parallel(
       dates, mf, cf, xf, metvars, wlonslice, wlatslice, plonslice, platslice,
       GDNAM, sfx, n_jobs=1, verbose=verbose, sleep=sleep)
