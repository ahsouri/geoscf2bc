if __name__ == '__main__':
    import argparse
    from .drivers import default

    prsr = argparse.ArgumentParser(description="""
This script extracts the perimiter concentrations from GEOS-CF along
the perimiter of a CMAQ or CAMx boundary.

Notes:
* `gdpath` and `GDNAM` define the horizontal scope using the perimiter of GDNAM
* SDATE, EDATE and freq will be define the time by:
    dates = pandas.date_range(SDATE, EDATE, freq=freq)
""")
    _ = prsr.add_argument(
        '-v', '--verbose', default=0, action='count'
    )
    _ = prsr.add_argument(
        '--cffreq', default='3h',
        help='Default frequency. To be read by pd.date_range'
    )
    _ = prsr.add_argument(
        '--gdpath', default='GRIDDESC',
        help='Path to IOAPI GRIDDESC file with GDNAM definition'
    )
    _ = prsr.add_argument(
        '--m3path', default=None,
        help='Path to METCRO2D from MCIP. Used for VGTYP, VGLVLS, VGTOP'
    )
    _ = prsr.add_argument(
        'GDNAM', help='Grid name (e.g., 12US1, 12US2, 36US3) defined in gdpath'
    )
    _ = prsr.add_argument(
        'SDATE',
        help='Start date (e.g., %%Y-%%m-%%d %%H).'
    )
    _ = prsr.add_argument(
        'EDATE',
        help='End date (e.g., %%Y-%%m-%%d %%H).'
    )

    args = prsr.parse_args()
    default(**vars(args))
