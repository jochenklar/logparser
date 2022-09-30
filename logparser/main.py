import argparse

from .config import settings
from .utils import (get_hash, open_log_file, parse_country, parse_user_agent,
                    parse_time, parse_log_line, parse_referrer, parse_request,
                    parse_size, parse_status, write_csv, write_json, write_sql)


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

        # open input file handle
        fp = open_log_file(input_path)

        for log_line in fp:
            if log_line:
                match = parse_log_line(log_line)
                if match:
                    request = parse_request(match)
                    if request:
                        request_method, request_path, request_query, request_version = request
                        status = parse_status(match)
                        referrer_scheme, referrer_host, referrer_path, referrer_query = parse_referrer(match)
                        user_agent, user_agent_device, user_agent_os, user_agent_browser = parse_user_agent(match)

                        # apply ignore lists
                        if settings.IGNORE_HOST and any(match.group('host').startswith(ignore_host)
                                                        for ignore_host in settings.IGNORE_HOST):
                            continue

                        if settings.IGNORE_METHOD and any(request_method == ignore_method
                                                          for ignore_method in settings.IGNORE_METHOD):
                            continue

                        if settings.IGNORE_PATH and any(request_path.startswith(ignore_path)
                                                        for ignore_path in settings.IGNORE_PATH):
                            continue

                        if settings.IGNORE_STATUS and any(status == int(ignore_status)
                                                          for ignore_status in settings.IGNORE_STATUS):
                            continue

                        row = {
                            'sha1': get_hash(log_line),
                            'host': settings.HOST,
                            'remote_host': match.group('host'),
                            'remote_country': parse_country(match, settings.GEOIP2_READER),
                            'remote_user': match.group('user'),
                            'time': parse_time(match),
                            'request_method': request_method,
                            'request_path': request_path,
                            'request_query': request_query,
                            'request_version': request_version,
                            'status': status,
                            'size': parse_size(match),
                            'referrer_scheme': referrer_scheme,
                            'referrer_host': referrer_host,
                            'referrer_path': referrer_path,
                            'referrer_query': referrer_query,
                            'user_agent': user_agent,
                            'user_agent_device': user_agent_device,
                            'user_agent_os': user_agent_os,
                            'user_agent_browser': user_agent_browser
                        }

                        # append to buffer
                        if row['time'] is not None:
                            rows.append(row)

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
