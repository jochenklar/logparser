import argparse
import logging
import os

from dotenv import find_dotenv, load_dotenv

from .parser import LogParser
from .utils import get_output_path, open_log_file
from .writer import Writer

FORMATS = ['json', 'json.gz', 'json.xz', 'csv', 'csv.gz', 'csv.xz', 'sql']


def main():
    load_dotenv(find_dotenv(usecwd=True))

    parser = argparse.ArgumentParser()
    parser.add_argument('input_paths', metavar='path', nargs='+',
                        help='Paths to the files to process, can be a pattern using *')
    parser.add_argument('-f|--format', dest='format', default=os.environ.get('FORMAT'),
                        choices=['json', 'json.gz', 'json.xz', 'csv', 'csv.gz', 'csv.xz', 'sql'],
                        help='Output format, if non is provided, the input is given as output.')
    parser.add_argument('-h|--host', dest='host', default=os.environ.get('HOST', 'localhost'),
                        help='Host for this log, useful if logs of multiple hosts are'
                             ' aggregated in one place, default: localhost')
    parser.add_argument('-o|--output-path', dest='output_path', default=os.environ.get('OUTPUT_PATH', '.'),
                        help='Path where the outputs are written to')
    parser.add_argument('-d|--database', dest='database', default=os.environ.get('DATABASE'),
                        help='Database connection string, e.g. postgresql+psycopg2://username:password@host:port/dbname')
    parser.add_argument('-g|--geoip2-database', dest='geoip2_database', default=os.environ.get('GEOIP2_DATABASE'),
                        help='Path to the geoip2 database')
    parser.add_argument('-a|--anon', dest='anon', default=os.environ.get('ANON'),
                        choices=['daily', 'weekly', 'monthly', 'eternally'],
                        help='Anonymize the remote hosts (IP adresses), using daily, weekly,'
                             'monthly or eternally unique IDs')
    parser.add_argument('-s|--salts', dest='salts', default=os.environ.get('SALTS', 'salts'),
                        help='Path where the salts for the anonymization are stored [default: salts]')
    parser.add_argument('-c|--chunking', dest='chunking', type=int, default=os.environ.get('CHUNKING'),
                        help='Optional chunking used to process the logfiles on low memory machines.')
    parser.add_argument('--noua', dest='noua', action='store_true', default=False,
                        help='Do not use the user agent to compute the anonymized remote host.')
    parser.add_argument('--ignore-host', dest='ignore_host', action='append',
                        help='Host in the logs to be ignored, useful for internal ips, can be repeated')
    parser.add_argument('--ignore-method', dest='ignore_method', action='append',
                        help='Methods in the logs to be ignored, useful for HEAD, OPTIONS, can be repeated')
    parser.add_argument('--ignore-path', dest='ignore_path', action='append',
                        help='Path in the logs to be ignored, useful for recurring API calls, can be repeated')
    parser.add_argument('--ignore-status', dest='ignore_status', action='append',
                        help='Status in the logs to be ignored, useful for 206, 404, can be repeated')
    parser.add_argument('--log-level', dest='log_level', default=os.environ.get('LOG_LEVEL', 'INFO'),
                        help='Log level (ERROR, WARN, INFO, or DEBUG)')
    parser.add_argument('--log-file', dest='log_file', default=os.environ.get('LOG_FILE'),
                        help='Path to the log file')

    args = parser.parse_args()

    # setup logging
    logging.basicConfig(level=args.log_level.upper(), filename=args.log_file,
                        format='[%(asctime)s] %(levelname)s: %(message)s')

    # init LogParser
    parser = LogParser(host=args.host, anon=args.anon, noua=args.noua, salts=args.salts,
                       geoip2_database=args.geoip2_database)

    for input_path in args.input_paths:
        # create output path for this input path
        output_path = get_output_path(input_path, args.output_path, args.format)
        if output_path and output_path.exists():
            continue

        # init writer
        writer = Writer(format=args.format, chunking=args.chunking, path=output_path, database_settings=args.database)
        writer.open()

        # open log file
        with open_log_file(input_path) as fp:
            log_lines = fp.readlines()

        # loop over log_lines in the log_file
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
                writer.append(log_entry if args.format else log_line)
                if writer.chunk():
                    writer.write()

        # write the remaining output
        writer.write()
        writer.close()
