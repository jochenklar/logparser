import gzip
import hashlib
import logging
import lzma
import secrets
import string
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


def get_sha1(string):
    return hashlib.sha1(string.encode()).hexdigest()


def get_random_salt():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(8))
