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

current_date = None
current_records = None


def get_hash(line):
    return hashlib.sha1(line.encode()).hexdigest()


def parse_log_line(line):
    return log_pattern.match(line)


def parse_date(match):
    time = match.group('time')
    logger.debug('time "%s"', time)

    try:
        date = datetime.strptime(time, time_format).date()
        return date.isoformat()
    except ValueError:
        return None


def parse_status(match):
    status = match.group('status').strip()
    logger.debug('status "%s"', status)

    if status != '-':
        return int(status)


def parse_size(match):
    size = match.group('size').strip()
    logger.debug('size "%s"', size)

    if size != '-':
        return int(size)


def parse_request(match):
    request = match.group('request')
    logger.debug('request "%s"', request)

    m = request_pattern.match(request)
    if m:
        u = urlparse(m.group('request'))
        return m.group('method'), u.path, u.query, m.group('http_version')
    else:
        return False


def parse_referrer(match):
    referrer = match.group('referrer').strip()
    logger.debug('referrer "%s"', referrer)

    if referrer != '-':
        u = urlparse(referrer)
        return u.scheme, u.netloc, u.path, u.query
    else:
        return None, None, None, None


def parse_agent(match):
    agent = match.group('agent').split()[0].strip()
    logger.debug('agent "%s"', agent)

    if agent != '-':
        return agent
    else:
        return None


def parse_country(match, geoip2_reader):
    host = match.group('host')
    logger.debug('host "%s"', host)

    if host in host_map:
        return host_map[host]
    else:
        try:
            country_response = geoip2_reader.country(match.group('host'))
            host_map[host] = country_response.country.iso_code.lower()
        except (AddressNotFoundError, AttributeError):
            host_map[host] = None

        return host_map[host]


def open_log_file(log_path):
    logger.info('Opening %s', log_path)
    log_path = Path(log_path)

    if log_path.suffix == '.gz':
        return gzip.open(log_path, 'rt', encoding='utf-8')
    else:
        return open(log_path)


def write_csv(writer, rows, output_path=None):
    if writer is None:
        fp = open(output_path, 'w') if output_path else sys.stdout
        writer = csv.DictWriter(fp, fieldnames=rows[0].keys())
        writer.writeheader()

    writer.writerows(rows)

    return writer


def write_json(fp, rows, output_path=None):
    if fp is None:
        fp = open(output_path, 'w') if output_path else sys.stdout
    json.dump(rows, fp, indent=2)

    return fp


def write_sql(session, rows, database_settings):
    if session is None:
        engine = create_engine(database_settings)

        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        session = Session()

    session.bulk_save_objects(get_records(session, rows))

    return session


def get_records(session, rows):
    global current_date, current_records

    driver = session.get_bind().driver

    for row in rows:
        if row['date'] != current_date:
            current_date = row['date']
            current_records = set([
                sha1 for (sha1, ) in session.query(Record).filter_by(date=current_date).values('sha1')
            ])

        if row['sha1'] not in current_records:
            current_records.add(row['sha1'])

            if driver in ['sqlite']:
                row['date'] = datetime.strptime(row['date'], '%Y-%m-%d')
            elif driver in ['mysqldb']:
                for char_field in ['host', 'path', 'query', 'referrer_scheme', 'referrer_host',
                                   'referrer_path', 'referrer_query', 'agent']:
                    row[char_field] = row[char_field][:384] if row.get(char_field) else row.get(char_field)

            yield Record(**row)
