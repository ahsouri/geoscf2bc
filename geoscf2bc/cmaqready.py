__doc__ = """
# Convert hourly Translated Files to CMAQ-Ready

---
    author: Barron H. Henderson
    date: 2023-01-16
    last update: 2024-02-26
---

CMAQ requires hourly files that cover an entire day. This notebook takes
instantaneous files at a varible frequency (3h), stacks them, and interpolates
between them to make CMAQ-Ready inputs


Example Application:

    from geoscf2bc.cmaqready import concat
    GDNAM = '12US1'
    prefix = 'BCON_geoscf_cb6r3_ae7'
    intmpl = f'{GDNAM}/%Y/%m/%d/{prefix}_{GDNAM}_%Y-%m-%dT%H_%Y-%m-%dT%H_1h.nc'
    outtmpl = f'{GDNAM}/%Y/%m/%d/{prefix}_{GDNAM}_%Y-%m-%dT%H_25h.nc'
    dates = pd.date_range('2023-01-01', '2023-01-07', freq='1d')
    outpaths = concat(GDNAM, dates, intmpl, outtmpl)

"""


def concat(
    GDNAM, dates, intmpl, outtmpl, infreq='3h', outfreq='1h', verbose=0
):
    """
    Arguments
    ---------
    GDNAM : str
        Grid name (e.g., 12US1, etc)
    dates : iterable
        List of dates that are readable by pandas.to_datetime
    intmpl : str
        strftime template to find input files
    outtmpl : str
        strftime template to define output files
    infreq : str
        Frequency of input files to read (e.g., 3h=every 3 hours)
    outfreq : str
        Output files are daily and typically have hourly (1h) frquency.
    verbose : int
        Level of verbosity

    Returns
    -------
    outpaths : list
        List of files made by concat
    """
    import pandas as pd
    import xarray as xr
    import numpy as np
    import os
    from . import __version__ as proc_version

    outpaths = []
    dates = pd.to_datetime(dates)
    for date in dates:
        edate = date + pd.Timedelta(24, unit='h')
        times = pd.date_range(date, edate, freq=infreq)
        hourly_times = pd.date_range(date, edate, freq=outfreq)
        daypath = date.strftime(outtmpl)
        if os.path.exists(daypath):
            outpaths.append(daypath)
            print('Using cached', daypath, flush=True)
            continue

        paths = [hdate.strftime(intmpl) for hdate in times]

        bcfiles = [xr.open_dataset(path) for path in paths]
        bcfile = xr.concat(bcfiles, dim='TSTEP')
        bcfile.attrs.update(bcfiles[0].attrs)
        bcfile.coords['TSTEP'] = times
        daybcfile = bcfile.interp(TSTEP=hourly_times)
        for vk in daybcfile.data_vars:
            if vk == 'TFLAG':
                daybcfile[vk] = daybcfile[vk].astype('i')
            else:
                daybcfile[vk] = np.maximum(daybcfile[vk].astype('f'), 1e-30)

        jdays = hourly_times.strftime('%Y%j').astype('i').values[:, None]
        ihhmmss = hourly_times.strftime('%H%M%S').astype('i').values[:, None]
        daybcfile['TFLAG'][:, :, 0] = jdays
        daybcfile['TFLAG'][:, :, 1] = ihhmmss
        daybcfile['TFLAG'][:, 0]
        # Add descriptive metadata
        FILEDESC = (
            'Hourly values interpolated using default xarray'
            + f' ({xr.__version__}) DataArray. interp from individual files \n'
            + f'{os.getcwd()}/{intmpl}\nwith dates: \n - '
            + ',\n - '.join(times.strftime('%Y-%m-%dT%H:%M:%SZ'))
        )
        now = pd.to_datetime('now', utc=True)
        wdate = int(now.strftime('%Y%j'))
        wtime = int(now.strftime('%H%M%S'))
        history = f'Processed by geoscf2bc.cmaqread.concat (v{proc_version}'
        daybcfile.attrs.update(dict(
            WDATE=np.int32(wdate), WTIME=np.int32(wtime),
            CDATE=np.int32(wdate), CTIME=np.int32(wtime),
            FILEDESC=FILEDESC.ljust(80*60)[:80*60],
            HISTORY=history.ljust(80*60)[:80*60]
        ))
        daybcfile.to_netcdf(daypath, format='NETCDF4_CLASSIC')
        outpaths.append(daypath)

    return outpaths


if __name__ == '__main__':
    import argparse
    import pandas as pd

    parser = argparse.ArgumentParser()
    aa = parser.add_argument
    aa('GDNAM', help='Name of grid')
    aa('SDATE', help='Start date for pandas.date_range')
    aa('EDATE', help='Start date for pandas.date_range')
    args = parser.parse_args()

    GDNAM = args.GDNAM
    prefix = 'BCON_geoscf_cb6r3_ae7'
    intmpl = f'{GDNAM}/%Y/%m/%d/{prefix}_{GDNAM}_%Y-%m-%dT%H_%Y-%m-%dT%H_1h.nc'
    outtmpl = f'{GDNAM}/%Y/%m/%d/{prefix}_{GDNAM}_%Y-%m-%dT%H_25h.nc'
    dates = pd.date_range(args.SDATE, args.EDATE, freq='1d')
    outpaths = concat(GDNAM, dates, intmpl, outtmpl)
