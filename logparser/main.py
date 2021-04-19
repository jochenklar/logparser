import argparse

from .config import settings
from .utils import (get_hash, parse_agent, parse_country, parse_date,
                    parse_log_line, parse_referrer, parse_request, parse_size,
                    parse_status, read_log_lines, write_csv, write_json,
                    write_sql)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_path', metavar='path',
                        help='Path to the file to process, can be a pattern using *')
    parser.add_argument('--format', choices=['json', 'csv', 'sql'],
                        help='Output format, default: json')
    parser.add_argument('--host', dest='host',
                        help='Host for this log, useful if logs of multiple hosts are aggregated in one place, default: localhost')
    parser.add_argument('--database', dest='database',
                        help='Database connection string, e.g. postgresql+psycopg2://username:password@host:port/dbname')
    parser.add_argument('--geoip2-database', dest='geoip2_database',
                        help='Path to the geoip2 database')
    parser.add_argument('--ignore-host', dest='ignore_host', action='append',
                        help='Host in the logs to be ignored, useful for internal ips, can be repeated')
    parser.add_argument('--ignore-path', dest='ignore_path', action='append',
                        help='Path in the logs to be ignored, useful for recurring API calls, can be repeated')
    parser.add_argument('--log-level', dest='log_level',
                        help='Log level (ERROR, WARN, INFO, or DEBUG)')
    parser.add_argument('--log-file', dest='log_file',
                        help='Path to the log file')
    parser.add_argument('--config-file', dest='config_file',
                        help='File path of the config file')

    args = parser.parse_args()

    settings.setup(args)

    rows = []
    for log_line in read_log_lines(settings.INPUT_PATH):
        match = parse_log_line(log_line)
        if match:
            request = parse_request(match)
            if request:
                method, path, query, version = request

                if settings.IGNORE_HOST and match.group('host') in settings.IGNORE_HOST:
                    continue
                if settings.IGNORE_PATH and path in settings.IGNORE_PATH:
                    continue

                row = {}
                row['sha1'] = get_hash(log_line)
                row['host'] = settings.HOST
                row['date'] = parse_date(match)
                row['method'] = method
                row['path'] = path
                row['query'] = query
                row['version'] = version
                row['status'] = parse_status(match)
                row['size'] = parse_size(match)
                row['referrer_scheme'], row['referrer_host'], row['referrer_path'], row['referrer_query'] = parse_referrer(match)
                row['agent'] = parse_agent(match)
                row['country'] = parse_country(match, settings.GEOIP2_READER)
                rows.append(row)

    if settings.FORMAT == 'json':
        write_json(rows)
    elif settings.FORMAT == 'csv':
        write_csv(rows)
    elif settings.FORMAT == 'sql':
        write_sql(rows, settings.DATABASE)
