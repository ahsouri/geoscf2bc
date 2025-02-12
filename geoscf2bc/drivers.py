__all__ = ['default']


def default(
    GDNAM, gdpath, SDATE, EDATE, m3path=None, cffreq='3h', extract_only=False,
    ftype=2, verbose=0
):
    """
    Arguments
    ---------
    GDNAM : str
        Name of grid for boundaries.
    gdpath : str
        Path to IOAPI GRIDDESC file. If gdpath is None, use builtin.
    SDATE : str or pd.Datetime
        Start date (e.g, 2024-01-01T00)
    EDATE : str or pd.Datetime
        End date (e.g, 2024-01-02T00)
    m3path : str
        Path to METCRO3D file to use for VGTYP, VGLVLS, and VGTOP.
        If none, construct the typical US EPA 35 layer model.
    cffreq : str
        Frequency (e.g., 3h)
    extract_only : bool
        If true, exit after extracting data. Useful mainly to separate out
        the long extraction process.
    ftype : int
        2=bcon, 1=icon
    Returns
    -------
    outpaths : list
        List of output paths

    Example
    -------

.. code-block:: python

    from geoscf2bc.drivers import default
    gdpath = './GRIDDESC'
    outpaths = default('12US1', gdpath, '2024-01-01T00', '2024-01-02T00')
    print(len(outpaths), 'outputs')
    # 1 outputs
    print('e.g.', outpaths[0])
    # 12US1/2024/01/01/BCON_geoscf_cb6r3_ae7_12US1_2024-01-01T00_25h.nc
    """
    from .extract import geoscf_extract
    from .translate import geoscf2cmaq, getvglvls
    from .cmaqready import concat
    from .defs import griddescpath
    import pandas as pd

    vb = verbose
    if gdpath is None:
        gdpath = griddescpath
    sfx = {1: 'ICON', 2: 'BCON'}[ftype]
    prefix = f'{sfx}_geoscf_cb6r3_ae7'
    intmpl = f'{GDNAM}/%Y/%m/%d/{prefix}_{GDNAM}_%Y-%m-%dT%H_%Y-%m-%dT%H_1h.nc'
    outtmpl = f'{GDNAM}/%Y/%m/%d/{prefix}_{GDNAM}_%Y-%m-%dT%H_25h.nc'
    indates = pd.date_range(SDATE, EDATE, freq=cffreq)
    if vb > 0:
        print(indates, flush=True)
    # Ignore last date, which cannot be complete by definition
    outdates = pd.to_datetime(sorted(set(indates.floor('1d')))[:-1])
    if vb > 0:
        print(outdates, flush=True)
    expaths = geoscf_extract(GDNAM, gdpath, indates, ftype=ftype, verbose=vb)
    if extract_only:
        return expaths
    vgtyp, vglvls, vgtop = getvglvls(m3path)
    dpdf = pd.read_csv(f'{GDNAM}/{GDNAM}_{sfx}.csv')
    opths = geoscf2cmaq(
        GDNAM, gdpath, indates, dpdf, vglvls, vgtop, ftype=ftype, verbose=vb
    )
    if sfx == 'BCON':
        opths = concat(
            GDNAM, outdates, intmpl, outtmpl, infreq=cffreq, verbose=vb
        )
    print('\n'.join(opths), flush=True)
    return opths
