import hashlib
import logging
import re
from datetime import datetime
from urllib.parse import urlparse

from user_agents import parse

logger = logging.getLogger(__name__)

class LogParser:
    # Regex for the common Apache log format.
    # from https://gist.github.com/sumeetpareek/9644255
    line_parts = [
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
    line_pattern = re.compile(r'\s+'.join(line_parts)+r'\s*\Z')

    time_format = "%d/%b/%Y:%H:%M:%S %z"

    request_pattern = re.compile(r'(?P<method>[A-Z-]+) (?P<request>.*?) HTTP/(?P<http_version>.*)')

    def __init__(self, host='localhost', geoip2_database=None):
        self.host = host
        self.host_map = {}

        if geoip2_database:
            import geoip2.database
            self.geoip2_reader = geoip2.database.Reader(geoip2_database)
        else:
            self.geoip2_reader = None

    def parse_line(self, line):
        if line:
            match = self.line_pattern.match(line)
            if match:
                time = self.parse_time(match)
                if time:
                    request = self.parse_request(match)
                    if request:
                        request_method, request_path, request_query, request_version = request
                        status = self.parse_status(match)
                        referrer_scheme, referrer_host, referrer_path, referrer_query = self.parse_referrer(match)
                        user_agent, user_agent_device, user_agent_os, user_agent_browser = self.parse_user_agent(match)

                        return {
                            'sha1': hashlib.sha1(line.encode()).hexdigest(),
                            'host': self.host,
                            'remote_host': match.group('host'),
                            'remote_country': self.get_country(match),
                            'remote_user': match.group('user'),
                            'time': time,
                            'request_method': request_method,
                            'request_path': request_path,
                            'request_query': request_query,
                            'request_version': request_version,
                            'status': status,
                            'size': self.parse_size(match),
                            'referrer_scheme': referrer_scheme,
                            'referrer_host': referrer_host,
                            'referrer_path': referrer_path,
                            'referrer_query': referrer_query,
                            'user_agent': user_agent,
                            'user_agent_device': user_agent_device,
                            'user_agent_os': user_agent_os,
                            'user_agent_browser': user_agent_browser
                        }

    def parse_time(self, match):
        time = match.group('time')
        logger.debug('time "%s"', time)

        try:
            return datetime.strptime(time, self.time_format)
        except ValueError:
            return None


    def parse_status(self, match):
        status = match.group('status').strip()
        logger.debug('status "%s"', status)

        if status != '-':
            return int(status)


    def parse_size(self, match):
        size = match.group('size').strip()
        logger.debug('size "%s"', size)

        if size != '-':
            return int(size)


    def parse_request(self, match):
        request = match.group('request')
        logger.debug('request "%s"', request)

        m = self.request_pattern.match(request)
        if m:
            u = urlparse(m.group('request'))
            return m.group('method'), u.path, u.query, m.group('http_version')
        else:
            return False


    def parse_referrer(self, match):
        referrer = match.group('referrer').strip()
        logger.debug('referrer "%s"', referrer)

        if referrer != '-':
            u = urlparse(referrer)
            return u.scheme, u.netloc, u.path, u.query
        else:
            return None, None, None, None


    def parse_user_agent(self, match):
        agent = match.group('agent').strip()
        logger.debug('agent "%s"', agent)
        parsed_agent = parse(agent)
        return agent, parsed_agent.get_device(), parsed_agent.get_os(), parsed_agent.get_browser()


    def get_country(self, match):
        if self.geoip2_reader is None:
            return None

        from geoip2.errors import AddressNotFoundError

        host = match.group('host')
        logger.debug('host "%s"', host)

        if host in self.host_map:
            return self.host_map[host]
        else:
            try:
                country_response = self.geoip2_reader.country(match.group('host'))
                self.host_map[host] = country_response.country.iso_code.lower()
            except (AddressNotFoundError, AttributeError):
                self.host_map[host] = None

            return self.host_map[host]
