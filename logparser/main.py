import argparse
import logging
import os

from dotenv import load_dotenv

from .parser import LogParser
from .utils import open_log_file
from .writer import Writer


def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument('input_paths', metavar='path', nargs='+',
                        help='Paths to the files to process, can be a pattern using *')
    parser.add_argument('--format', choices=['raw', 'json', 'csv', 'sql'], default=os.environ.get('FORMAT', 'raw'),
                        help='Output format, default: raw')
    parser.add_argument('--host', dest='host', default=os.environ.get('HOST', 'localhost'),
                        help='Host for this log, useful if logs of multiple hosts are'
                             ' aggregated in one place, default: localhost')
    parser.add_argument('--database', dest='database', default=os.environ.get('DATABASE'),
                        help='Database connection string, e.g. postgresql+psycopg2://username:password@host:port/dbname')
    parser.add_argument('--geoip2-database', dest='geoip2_database', default=os.environ.get('GEOIP2_DATABASE'),
                        help='Path to the geoip2 database')
    parser.add_argument('--ignore-host', dest='ignore_host', action='append',
                        help='Host in the logs to be ignored, useful for internal ips, can be repeated')
    parser.add_argument('--ignore-method', dest='ignore_method', action='append',
                        help='Methods in the logs to be ignored, useful for HEAD, OPTIONS, can be repeated')
    parser.add_argument('--ignore-path', dest='ignore_path', action='append',
                        help='Path in the logs to be ignored, useful for recurring API calls, can be repeated')
    parser.add_argument('--ignore-status', dest='ignore_status', action='append',
                        help='Status in the logs to be ignored, useful for 206, 404, can be repeated')
    parser.add_argument('--chunking', dest='chunking', type=int, default=os.environ.get('CHUNKING'),
                        help='Optional chunking used to process the logfiles on low memory machines.')
    parser.add_argument('--log-level', dest='log_level', default=os.environ.get('LOG_LEVEL', 'INFO'),
                        help='Log level (ERROR, WARN, INFO, or DEBUG)')
    parser.add_argument('--log-file', dest='log_file', default=os.environ.get('LOG_FILE'),
                        help='Path to the log file')

    args = parser.parse_args()

    if args.format == 'json' and args.chunking:
        raise RuntimeError('--format=json does not work with --chunking')

    # setup logging
    logging.basicConfig(level=args.log_level.upper(), filename=args.log_file,
                        format='[%(asctime)s] %(levelname)s: %(message)s')

    # init LogParser
    parser = LogParser(host=args.host, geoip2_database=args.geoip2_database)

    # init writer
    writer = Writer(args.format, database_settings=args.database)
    writer.open()
    for input_path in args.input_paths:

        with open_log_file(input_path) as fp:
            log_lines = fp.readlines()

        for log_line in log_lines:
            log_entry = parser.parse_line(log_line)

            if log_entry:
                if args.ignore_host and any(
                    log_entry.host.startswith(ignore_host) for ignore_host in args.ignore_host
                ):
                    continue

                if args.ignore_method and any(
                    log_entry.request_method == ignore_method for ignore_method in args.ignore_method
                ):
                    continue

                if args.ignore_path and any(
                    log_entry.request_path.startswith(ignore_path)for ignore_path in args.ignore_path
                ):
                    continue

                if args.ignore_status and any(
                    log_entry.status == int(ignore_status) for ignore_status in args.ignore_status
                ):
                    continue

                # append to buffer
                writer.append(log_line, log_entry.serialize())
                if writer.chunk():
                    writer.write()
                    writer.rows = []  # reset rows buffer

    # write the remaining output
    writer.write()
    writer.close()
