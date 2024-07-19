import gzip
import logging
import lzma
from pathlib import Path

logger = logging.getLogger(__name__)

def open_log_file(log_path):
    logger.info('open %s', log_path)

    log_path = Path(log_path)

    if log_path.suffix == '.gz':
        return gzip.open(log_path, 'rt', encoding='utf-8')
    elif log_path.suffix == '.xz':
        return lzma.open(log_path, 'rt', encoding='utf-8')
    else:
        return open(log_path)
