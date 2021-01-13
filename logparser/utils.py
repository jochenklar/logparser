import csv
import gzip
import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from geoip2.errors import AddressNotFoundError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base, Record

logger = logging.getLogger(__name__)

# Regex for the common Apache log format.
# from https://gist.github.com/sumeetpareek/9644255
log_parts = [
    r'(?P<host>\S+)',                   # host %h
    r'\S+',                             # indent %l (unused)
    r'(?P<user>\S+)',                   # user %u
    r'\[(?P<time>.+)\]',                # time %t
    r'"(?P<request>.*)"',               # request "%r"
    r'(?P<status>[0-9]+)',              # status %>s
    r'(?P<size>\S+)',                   # size %b (careful, can be '-')
    r'"(?P<referrer>.*)"',              # referrer "%{Referer}i"
    r'"(?P<agent>.*)"',                 # user agent "%{User-agent}i"
]
log_pattern = re.compile(r'\s+'.join(log_parts)+r'\s*\Z')

time_format = "%d/%b/%Y:%H:%M:%S %z"

request_pattern = re.compile(r'(?P<method>[A-Z-]+) (?P<request>.*?) HTTP/(?P<http_version>.*)')

bulk_save_chunk_size = 100000

host_map = {}


def read_log_lines(log_path):
    logger.info('Reading %s', log_path)

    log_path = Path(log_path)

    if log_path.suffix == '.gz':
        with gzip.open(log_path) as f:
            return [line.strip().decode() for line in f.readlines() if line]

    else:
        with open(log_path) as f:
            return [line.strip() for line in f.readlines() if line]


def get_hash(line):
    return hashlib.sha1(line.encode()).hexdigest()


def parse_log_line(line):
    return log_pattern.match(line)


def parse_date(match):
    time = datetime.strptime(match.group('time'), time_format)
    date = time.date()
    return date.isoformat()


def parse_status(match):
    status = match.group('status').strip()
    if status != '-':
        return int(status)


def parse_size(match):
    size = match.group('size').strip()
    if size != '-':
        return int(size)


def parse_request(match):
    m = request_pattern.match(match.group('request'))
    u = urlparse(m.group('request'))
    return m.group('method'), u.path, u.query, m.group('http_version')


def parse_referrer(match):
    referrer = match.group('referrer').strip()
    if referrer != '-':
        u = urlparse(referrer)
        return u.scheme, u.netloc, u.path, u.query
    else:
        return None, None, None, None


def parse_agent(match):
    agent = match.group('agent').split()[0].strip()
    if agent != '-':
        return agent
    else:
        return None


def parse_country(match, geoip2_reader):
    host = match.group('host')

    if host in host_map:
        return host_map[host]
    else:
        try:
            country_response = geoip2_reader.country(match.group('host'))
            host_map[host] = country_response.country.iso_code.lower()
        except (AddressNotFoundError, AttributeError):
            host_map[host] = None

        return host_map[host]


def write_csv(rows, output_path=None):
    fp = open(output_path, 'w') if output_path else sys.stdout
    writer = csv.DictWriter(fp, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    fp.close()


def write_json(rows, output_path=None):
    fp = open(output_path, 'w') if output_path else sys.stdout
    json.dump(rows, fp, indent=2)
    fp.close()


def write_sql(rows, database_settings):
    engine = create_engine(database_settings)

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    records = []
    for row in rows:
        if engine.driver in ['sqlite']:
            row['date'] = datetime.strptime(row['date'], '%Y-%m-%d')
        elif engine.driver in ['mysqldb']:
            for key in ['host', 'path', 'query', 'referrer_scheme', 'referrer_host', 'referrer_path', 'referrer_query', 'agent']:
                row[key] = row[key][:384] if row.get(key) else row.get(key)

        records.append(Record(**row))

        if len(records) >= bulk_save_chunk_size:
            session.bulk_save_objects(records)
            records = []

    session.bulk_save_objects(records)
    session.commit()
