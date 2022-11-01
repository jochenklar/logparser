import argparse

from .config import settings
from .utils import (open_log_file, parse_log_line, write_csv, write_json, write_sql)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_paths', metavar='path', nargs='+',
                        help='Paths to the files to process, can be a pattern using *')
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
    parser.add_argument('--ignore-method', dest='ignore_method', action='append',
                        help='Methods in the logs to be ignored, useful for HEAD, OPTIONS, can be repeated')
    parser.add_argument('--ignore-path', dest='ignore_path', action='append',
                        help='Path in the logs to be ignored, useful for recurring API calls, can be repeated')
    parser.add_argument('--ignore-status', dest='ignore_status', action='append',
                        help='Status in the logs to be ignored, useful for 206, 404, can be repeated')
    parser.add_argument('--chunking', dest='chunking', type=int,
                        help='Optional chunking used to process the logfiles on low memory machines.')
    parser.add_argument('--log-level', dest='log_level',
                        help='Log level (ERROR, WARN, INFO, or DEBUG)')
    parser.add_argument('--log-file', dest='log_file',
                        help='Path to the log file')
    parser.add_argument('--config-file', dest='config_file',
                        help='File path of the config file')

    args = parser.parse_args()

    settings.setup(args)

    # create rows buffer
    rows = []

    # init output handle (file handle or db connection), will be opened on first write
    oh = None

    for input_path in settings.INPUT_PATHS:

        with open_log_file(input_path) as fp:
            log_lines = fp.readlines()

        for log_line in log_lines:

            log_entry = parse_log_line(log_line, host=settings.HOST, geoip2_reader=settings.GEOIP2_READER)
            if log_entry:

                if settings.IGNORE_HOST and any(log_entry['host'].startswith(ignore_host)
                                                for ignore_host in settings.IGNORE_HOST):
                    continue

                if settings.IGNORE_METHOD and any(log_entry['request_method'] == ignore_method
                                                  for ignore_method in settings.IGNORE_METHOD):
                    continue

                if settings.IGNORE_PATH and any(log_entry['request_path'].startswith(ignore_path)
                                                for ignore_path in settings.IGNORE_PATH):
                    continue

                if settings.IGNORE_STATUS and any(log_entry['status'] == int(ignore_status)
                                                  for ignore_status in settings.IGNORE_STATUS):
                    continue

                # store time as isoformat
                log_entry['time'] = log_entry['time'].isoformat()

                # append to buffer
                rows.append(log_entry)

                if settings.CHUNKING and len(rows) >= settings.CHUNKING:
                    # write chunks if configured
                    if settings.FORMAT == 'csv':
                        oh = write_csv(oh, rows)
                    elif settings.FORMAT == 'sql':
                        oh = write_sql(oh, rows, settings.DATABASE)

                    # reset rows buffer
                    rows = []

    # write the remaining output
    if settings.FORMAT == 'json':
        write_json(oh, rows, close=True)
    elif settings.FORMAT == 'csv':
        write_csv(oh, rows, close=True)
    elif settings.FORMAT == 'sql':
        write_sql(oh, rows, settings.DATABASE, close=True)
