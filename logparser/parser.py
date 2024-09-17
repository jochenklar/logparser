import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from user_agents import parse

from .models import LogEntry
from .utils import get_random_salt, get_sha1

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

    def __init__(self, host='localhost', anon=None, noua=None, salts=None, geoip2_database=None):
        self.host = host
        self.host_map = {}
        self.salt_map = {}

        self.anon = anon
        self.noua = noua
        self.salts = salts

        if geoip2_database:
            import geoip2.database
            geoip2_database = Path(geoip2_database).expanduser()
            self.geoip2_reader = geoip2.database.Reader(geoip2_database)
        else:
            self.geoip2_reader = None

    def parse_line(self, line):
        if line:
            match = self.line_pattern.match(line)
            if match:
                time = self.parse_time(match.group('time'))
                if time:
                    request = self.parse_request(match.group('request'))
                    if request:
                        request_method, request_path, request_query, request_version = request

                        status = self.parse_int(match.group('status'))
                        size = self.parse_int(match.group('size'))

                        referrer_scheme, referrer_host, referrer_path, referrer_query = \
                            self.parse_referrer(match.group('referrer'))
                        user_agent, user_agent_device, user_agent_os, user_agent_browser = \
                            self.parse_user_agent(match.group('agent'))

                        remote_host = self.get_remote_host(match.group('host'), time, user_agent)
                        remote_country = self.get_remote_country(match.group('host'))
                        remote_user = self.get_remote_user(match.group('user'))

                        return LogEntry(
                            sha1=get_sha1(line),
                            host=self.host,
                            remote_host=remote_host,
                            remote_country=remote_country,
                            remote_user=remote_user,
                            time=time,
                            request_method=request_method,
                            request_path=request_path,
                            request_query=request_query,
                            request_version=request_version,
                            status=status,
                            size=size,
                            referrer_scheme=referrer_scheme,
                            referrer_host=referrer_host,
                            referrer_path=referrer_path,
                            referrer_query=referrer_query,
                            user_agent=user_agent,
                            user_agent_device=user_agent_device,
                            user_agent_os=user_agent_os,
                            user_agent_browser=user_agent_browser
                        )

    def parse_time(self, time):
        try:
            return datetime.strptime(time, self.time_format)
        except ValueError:
            return None

    def parse_int(self, value):
        value = value.strip()
        if value != '-':
            return int(value)

    def parse_request(self, request):
        match = self.request_pattern.match(request)
        if match:
            u = urlparse(match.group('request'))
            return match.group('method'), u.path, u.query, match.group('http_version')
        else:
            return None, None, None, None

    def parse_referrer(self, referrer):
        referrer = referrer.strip()
        if referrer != '-':
            u = urlparse(referrer)
            return u.scheme, u.netloc, u.path, u.query
        else:
            return None, None, None, None

    def parse_user_agent(self, agent):
        agent = agent.strip()
        parsed_agent = parse(agent)
        return agent, parsed_agent.get_device(), parsed_agent.get_os(), parsed_agent.get_browser()

    def get_remote_host(self, remote_host, time, user_agent):
        if not self.anon:
            return remote_host
        elif self.noua:
            return get_sha1(self.get_salt(time) + remote_host)
        else:
            return get_sha1(self.get_salt(time) + remote_host + user_agent)

    def get_remote_country(self, remote_host):
        if self.geoip2_reader is None:
            return None

        from geoip2.errors import AddressNotFoundError

        if remote_host in self.host_map:
            return self.host_map[remote_host]
        else:
            try:
                country_response = self.geoip2_reader.country(remote_host)
                self.host_map[remote_host] = country_response.country.iso_code.lower()
            except (AddressNotFoundError, AttributeError, ValueError):
                self.host_map[remote_host] = None

            return self.host_map[remote_host]

    def get_remote_user(self, user):
        return user if self.anon is None else None

    def get_salt(self, time):
        date = time.date()

        if self.anon == 'daily':
            salt_date = date
        elif self.anon == 'weekly':
            salt_date = date - timedelta(days=date.weekday())
        elif self.anon == 'monthly':
            salt_date = date - timedelta(days=date.day-1)
        elif self.anon == 'eternally':
            salt_date = date.fromtimestamp(0)
        else:
            raise RuntimeError('anon must be one of (daily, weekly, monthly, eternally)')

        salt = self.salt_map.get(salt_date)
        if salt is None:
            salt_path = Path(self.salts).expanduser() / str(salt_date)
            if salt_path.exists():
                salt = salt_path.read_text()
            else:
                salt = get_random_salt()
                salt_path.parent.mkdir(exist_ok=True, parents=True)
                salt_path.write_text(salt)

            self.salt_map[salt_date] = salt

        return salt
