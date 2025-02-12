from geoscf2bc.drivers import default
bcpaths = default(
    GDNAM='TEST', gdpath='./GRIDDESC',
    SDATE='2024-01-01T00', EDATE='2024-01-02T00'
)
print(len(bcpaths), bcpaths[0])
icpaths = default(
    GDNAM='TEST', gdpath='./GRIDDESC', ftype=1,
    SDATE='2024-01-01T00', EDATE='2024-01-01T00'
)
print(len(icpaths), icpaths[0])
