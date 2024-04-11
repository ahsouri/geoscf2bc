__doc__ = """
# Translate GEOS-CF Extracted Files to BCON

---
    author: Barron H. Henderson
    date: 2023-01-16
    last update: 2023-10-26
---

The input is from geoscf2bc.extract.geoscf_extract and the output is a single
CMAQ BCON file. CMAQ typically expects a single file that contains all hours
for a day.

Update:
* 2023-10-26: Making into a script-like operation and adding default VGLVLS
"""

import pandas as pd
import PseudoNetCDF as pnc
import numpy as np
import argparse
import warnings
import PseudoNetCDF.geoschemfiles._vertcoord

hyai = pnc.geoschemfiles._vertcoord.geos_hyai['GEOS-5-NATIVE']
hybi = pnc.geoschemfiles._vertcoord.geos_hybi['GEOS-5-NATIVE']


_prsr = argparse.ArgumentParser(description="""
This script convert extracted GEOS-CF from GEOS_CF_Extract.py
 to create CMAQ or CAMx boundary conditions.

Notes:
* `gdpath` and `GDNAM` define the horizontal scope using the perimiter of GDNAM
* SDATE, EDATE and freq will be define the time by:
    dates = pandas.date_range(SDATE, EDATE, freq=freq)
""")
_ = _prsr.add_argument(
    '--freq', default='3h',
    help='Default frequency. To be read by pd.date_range'
)
_ = _prsr.add_argument(
    '--m3path', default=None,
    help='Path to IOAPI file with VGTYP, VGLVLS and VGTOP parameters'
)
_ = _prsr.add_argument(
    '--gdpath', default='GRIDDESC',
    help='Path to IOAPI GRIDDESC file with GDNAM definition'
)
_ = _prsr.add_argument(
    'GDNAM', help='Grid name (e.g., 12US1, 12US2, 36US3) defined in gdpath'
)
_ = _prsr.add_argument(
    'SDATE',
    help='Start date (e.g., %Y-%m-%d %H).'
)
_ = _prsr.add_argument(
    'EDATE', help='End date (e.g., %Y-%m-%d %H).'
)
# xxxxxxx1xxxxxxxxx2xxxxxxxxx3xxxxxxxxx4xxxxxxxxx5xxxxxxxxx6xxxxxxxxx7xxxxxxxxx
# 34567890123456789012345678901234567890123456789012345678901234567890123456789


def getvglvls(m3path=None):
    """
    Returns a set of IOAPI VGTYP, VGLVLS, and VGTOP that define the vertical
    coordinate of a CMAQ domain.

    Arguments
    ---------
    m3path : str
        Path to a METCRO3D file

    Returns
    -------
    vgtuple : tuple
        (vgtyp, vglvls, vgtop) where vgtyp is an IOAPI numeric indicator that
        specifyies the type of vertical coordinate. vglvls and vgtop are the
        IOAPI definition.
    """
    import PseudoNetCDF as pnc
    if m3path is not None:
        vgf = pnc.pncopen(m3path, format='ioapi')
        vgtop = vgf.VGTOP
        vgtyp = vgf.VGTYP
        vglvls = vgf.VGLVLS
    else:
        vgtyp = -9999
        vglvls = np.array([
            1.0000, 0.9975, 0.9950, 0.9900, 0.9850, 0.9800, 0.9700, 0.9600,
            0.9500, 0.9400, 0.9300, 0.9200, 0.9100, 0.9000, 0.8800, 0.8600,
            0.8400, 0.8200, 0.8000, 0.7700, 0.7400, 0.7000, 0.6500, 0.6000,
            0.5500, 0.5000, 0.4500, 0.4000, 0.3500, 0.3000, 0.2500, 0.2000,
            0.1500, 0.1000, 0.0500, 0.0000
        ], dtype='f')
        vgtop = 5000.
        print(
            f'Using default vertical grid: VGTYP={vgtyp} VGTOP={vgtop} and'
            + f' {len(vglvls) - 1} layers:'
        )
        print(vglvls)

    return vgtyp, vglvls, vgtop


cf_refp = 101325.
CF_VGTOP = 5000
_approxp = (cf_refp * hybi + hyai * 100)
CF_VGLVLS = (
    (_approxp - CF_VGTOP)[:37] / (cf_refp - CF_VGTOP)
).astype('f')
warnings.warn(
    'Vertical interpolation assumes GEOS-CF is in a terrain following partial'
    + f' pressure coordinate with a surface pressure P={cf_refp} and'
    + f' VGTOP={CF_VGTOP}'
)


def geoscf2cmaq(
    GDNAM, gdpath, sdate, dpdf, vglvls, vgtop, persist=True, overwrite=False,
    verbose=0
):
    """
    Convert GEOS-CF species and format to CMAQ

    Arguments
    ---------
    GDNAM : str
        Name of grid definition
    gdpath : str
        Path to the GRIDDESC file that defines GDNAM
    sdate : datetime
        Must support strftime
    dpdf : pd.DataFrame
        Must have latitude and longitude where index is the perimiter cell in
        order of IOAPI storage. Typically, an artifact of `geoscf_extract`
    vglvls : np.ndarray
        Vertical coordinate for the output file (used by ioapi.interpSigma).
        Typically, sigma: (p - ptop) / (psfc - ptop) ranging from 1 to 0.
        Newer WRF uses a hybrid and sigma is just an approximation.
    vgtop : float
        Minimum pressure in Pascals for the output file (used by
        ioapi.interpSigma)
    presist : bool
        If True, write the file to disk
    overwrite : bool
        If True, overwrite existing files
    verbose : int
        Level of verbosity

    Returns
    -------
    bcf, outpath : PseudonetCDFFile, str
        Output file and path where it was (or could be) output
    """
    import xarray as xr
    import os
    from . import __version__ as proc_version

    # Check for recursive call
    if hasattr(sdate, '__iter__'):
        sdates = sdate
        outpaths = []
        for sdate in sdates:
            outbcf, outpath = geoscf2cmaq(
                GDNAM, gdpath, sdate, dpdf, vglvls, vgtop, persist=persist,
                overwrite=overwrite
            )
            outpaths.append(outpath)
        return outpaths
    else:
        if not hasattr(sdate, 'strftime'):
            raise ValueError('sdate must support strftime')

    # global None
    # Define file paths
    suffix = f'{sdate:%Y-%m-%dT%H}_{sdate:%Y-%m-%dT%H}_1h.nc'
    metpath = f'{GDNAM}/{sdate:%Y/%m/%d}/met_tavg_1hr_g1440x721_v36_{suffix}'
    chmpath = f'{GDNAM}/{sdate:%Y/%m/%d}/chm_tavg_1hr_g1440x721_v36_{suffix}'
    xgcpath = f'{GDNAM}/{sdate:%Y/%m/%d}/xgc_tavg_1hr_g1440x721_v36_{suffix}'
    bcsuffix = f'{GDNAM}_{sdate:%FT%H}_{sdate:%FT%H}_1h.nc'
    outpath = f'{GDNAM}/{sdate:%Y/%m/%d}/BCON_geoscf_cb6r3_ae7_{bcsuffix}'
    if os.path.exists(outpath) and persist and not overwrite:
        print(outpath, 'cached', end='\r')
        return None, outpath

    # Open input files
    metf = xr.open_dataset(metpath)
    chmf = xr.open_dataset(chmpath)
    xgcf = xr.open_dataset(xgcpath)

    # Source Perimeter Data Frame (spdf)
    spdf = metf[['lat', 'lon']].to_dataframe()

    # Mapping from source to destination
    sdpdf = dpdf.merge(
        spdf.reset_index(), left_on=['lon', 'lat'], right_on=['lon', 'lat']
    )
    assert (sdpdf.shape[0] == dpdf.shape[0])

    # Plot perimiter of source data
    # plt.scatter(sdpdf.lon, sdpdf.lat, c=dpdf.index)

    # Combine met, chm, xgc for easy access
    allvars = {k: v for k, v in metf.data_vars.items()}
    allvars.update({k: v for k, v in chmf.data_vars.items()})
    allvars.update({k: v for k, v in xgcf.data_vars.items()})

    # Calculate output met vars
    defroot = os.path.dirname(__file__)
    mcdef = open(f'{defroot}/defs/geoscf_met.txt', 'r').read()
    metsvars = {}
    exec(mcdef, allvars, metsvars)

    # Calculate output gas vars
    gcdef = open(f'{defroot}/defs/geoscf_cb6r4.txt', 'r').read()
    gcsvars = {}
    exec(gcdef, allvars, gcsvars)

    # Calculate output aerosol vars
    aedef = open(f'{defroot}/defs/geoscf_ae7.txt', 'r').read()
    aesvars = {}
    exec(aedef, allvars, aesvars)

    # Combine defined variables for easy access
    outvars = {k: v for k, v in gcsvars.items()}
    outvars.update(aesvars)
    outvars.update(metsvars)

    # Define units the easy way
    units = {k: 'ppmv'.ljust(16) for k in gcsvars}
    # not all ae7 variables are in micrograms/m**3
    # need to correct semi-volatile gases
    units.update({k: 'micrograms/m**3'.ljust(16) for k in aesvars})
    # All met vars are unknown until defined
    units.update({k: 'unknown'.ljust(16) for k in metsvars})
    # Update known units
    units['PRES'] = 'Pa'.ljust(16)
    units['ZH'] = 'm'.ljust(16)
    units['ZF'] = 'm'.ljust(16)
    units['DENS'] = 'kg/m**3'.ljust(16)
    units['AIRMOLDENS'] = 'mole/m**3'.ljust(16)

    # Prep a holder file
    bcf = pnc.pncopen(
        gdpath, format='griddesc', GDNAM=GDNAM, FTYPE=2,
        NLAYS=CF_VGLVLS.size - 1, VGLVLS=CF_VGLVLS, VGTOP=CF_VGTOP,
        VGTYP=-9999, SDATE=np.int32(sdate.strftime('%Y%j')),
        STIME=np.int32(sdate.strftime('%H%M%S')),
        TSTEP=np.int32(10000), nsteps=1, var_kwds=units, withcf=False
    )
    # Load the data into the file
    for k, v in outvars.items():
        # Invert lev to match geos-chem expectations
        # Resample PERIM to match output IOAPI PERIM order
        bcf.variables[k][:] = v.transpose(
            'time', 'lev', 'PERIM'
        )[:, ::-1, sdpdf.PERIM.values]

    outbcf = bcf.interpSigma(vglvls=vglvls, vgtop=vgtop, interptype='linear')
    FILEDESC = (
        f'BCON created using geoscf2bc.translate.geoscf2cmaq (v{proc_version})'
        + f' using files in {os.getcwd()}:\n'
        + ' - defs/geoscf_met.txt\n'
        + ' - defs/geoscf_cb6r4.txt\n'
        + ' - defs/geoscf_ae7.txt\n'
        + 'see description (non IOAPI metadata)'
    )
    description = (
        f'# defs/geoscf_met.txt:\n{mcdef}\n\n'
        + f'# defs/geoscf_cb6r4.txt:\n{gcdef}\n\n'
        + f'# defs/geoscf_ae7.txt:\n{aedef}\n\n'
    )
    outbcf.setncatts(dict(
        HISTORY='Created using GEOS_CF_Translate.ipynb'.ljust(60*80)[:60*80],
        FILEDESC=FILEDESC.ljust(60*80)[:60*80],
        description=description
    ))
    # Persist file to disk
    if persist:
        outbcf.save(outpath, format='NETCDF3_CLASSIC', verbose=0).close()

    return outbcf, outpath


if __name__ == '__main__':
    # args = _prsr.parse_args(
    #   '--gdpath=/home/bhenders/GRIDDESC', '12US1', '2023-04-01', '2023-04-02'
    # ])
    args = _prsr.parse_args()

    GDNAM = args.GDNAM
    gdpath = args.gdpath
    dpdf = pd.read_csv(f'{GDNAM}/{GDNAM}_locs.csv')
    vgtyp, vglvls, vgtop = getvglvls(args.m3path)

    for sdate in pd.date_range(args.SDATE, args.EDATE, freq=args.freq):
        bcf, bcpath = geoscf2cmaq(
            GDNAM=GDNAM, gdpath=gdpath, sdate=sdate,
            dpdf=dpdf, vglvls=vglvls, vgtop=vgtop,
            overwrite=False
        )
        print(bcpath + ' '*20, end='\r')
