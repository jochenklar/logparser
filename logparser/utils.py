import gzip
import hashlib
import logging
import lzma
import secrets
import string
import sys
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


def open_output_file(output_path, mode='rt'):
    if output_path is None:
        return sys.stdout

    output_path = Path(output_path)

    if mode.startswith('w'):
        output_path.parent.mkdir(exist_ok=True, parents=True)

    if output_path.suffix == '.gz':
        return gzip.open(output_path, mode, encoding='utf-8')
    elif output_path.suffix == '.xz':
        return lzma.open(output_path, mode, encoding='utf-8')
    else:
        return open(output_path, mode)


def get_output_path(input_path, output_base_path, output_format):
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
