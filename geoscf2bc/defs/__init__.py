__all__ = [
    'defroot', 'defpaths', 'metdefpath', 'cb6r4defpath', 'ae7defpath',
    'griddescpath'
]
import os
from glob import glob


defroot = os.path.realpath(os.path.dirname(__file__))
defpaths = tuple(sorted(glob(defroot)))
metdefpath = [p for p in defpaths if p.endswith('geoscf_met.txt')][0]
cb6r4defpath = [p for p in defpaths if p.endswith('geoscf_cb6r4.txt')][0]
ae7defpath = [p for p in defpaths if p.endswith('geoscf_ae7.txt')][0]
griddescpath = [p for p in defpaths if p.endswith('GRIDDESC')][0]