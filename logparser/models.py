from dataclasses import asdict, dataclass, fields
from datetime import datetime


@dataclass
class LogEntry:
    sha1: str
    host: str
    remote_host: str
    remote_country: str
    remote_user: str
    time: datetime
    request_method: str
    request_path: str
    request_query: str
    request_version: str
    status: str
    size: int
    referrer_scheme: str
    referrer_host: str
    referrer_path: str
    referrer_query: str
    user_agent: str
    user_agent_device: str
    user_agent_os: str
    user_agent_browser: str

    @classmethod
    def get_fields(cls):
        return [field.name for field in fields(cls)]

    def serialize(self):
        data = asdict(self)
        data['time'] = data['time'].isoformat()
        return data

    def __post_init__(self):
        if isinstance(self.time, str):
            self.time = datetime.fromisoformat(self.time)
