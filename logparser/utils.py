import gzip
import hashlib
import logging
import lzma
import os
import secrets
import string
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def open_log_file(log_path, mode='rt', log=True):
    if log_path is None:
        return sys.stdout

    if log:
        logger.info('%s %s (%s)', 'read' if mode.startswith('r') else 'open', log_path, mode)

    log_path = Path(log_path)

    if mode.startswith('w'):
        log_path.parent.mkdir(exist_ok=True, parents=True)

    kwargs = {}
    if 'b' not in mode:
        kwargs['encoding'] = 'utf-8'

    if log_path.suffix == '.gz':
        return gzip.open(log_path, mode, **kwargs)
    elif log_path.suffix == '.xz':
        return lzma.open(log_path, mode, **kwargs)
    else:
        return open(log_path, mode, **kwargs)


def get_output_path(input_path, output_base_path, output_format=None):
    output_path = Path(output_base_path) / Path(input_path).name
    if output_format is None:
        return output_path
    elif output_format in ['json', 'json.gz', 'json.xz', 'csv', 'csv.gz', 'csv.xz']:
        return output_path.with_suffix(f'.{output_format}')
    else:
        return None


def get_sha1(string):
    return hashlib.sha1(string.encode()).hexdigest()


def get_random_salt():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(8))


def get_first_line(path):
    with open_log_file(path, 'rb', log=False) as fp:
        return fp.readline().decode()


def get_last_line(path):
    try:
        with open_log_file(path, 'rb', log=False) as fp:
            fp.seek(-2, os.SEEK_END)
            while fp.read(1) != b'\n':
                fp.seek(-2, os.SEEK_CUR)
            return fp.readline().decode()
    except (OSError, FileNotFoundError):
        return None
