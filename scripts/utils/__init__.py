import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s][%(levelname)s]%(message)s',
)

from .utils import makedirs
from .calc_rmsd import calc_rmsd