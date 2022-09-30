from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Record(Base):

    __tablename__ = 'records'

    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True, autoincrement=True)
    sha1 = Column(Text().with_variant(String(40), 'mysql'), nullable=False)
    host = Column(Text().with_variant(String(384), 'mysql'))
    remote_host = Column(Text().with_variant(String(64), 'mysql'))
    remote_country = Column(Text().with_variant(String(2), 'mysql'))
    remote_user = Column(Text().with_variant(String(384), 'mysql'))
    time = Column(DateTime, nullable=False)
    request_method = Column(Text().with_variant(String(16), 'mysql'))
    request_path = Column(Text().with_variant(String(384), 'mysql'))
    request_query = Column(Text().with_variant(String(384), 'mysql'))
    request_version = Column(Text().with_variant(String(4), 'mysql'))
    status = Column(Integer)
    size = Column(BigInteger().with_variant(Integer, 'sqlite'))
    referrer_scheme = Column(Text().with_variant(String(384), 'mysql'))
    referrer_host = Column(Text().with_variant(String(384), 'mysql'))
    referrer_path = Column(Text().with_variant(String(384), 'mysql'))
    referrer_query = Column(Text().with_variant(String(384), 'mysql'))
    user_agent = Column(Text().with_variant(String(384), 'mysql'))
    user_agent_device = Column(Text().with_variant(String(384), 'mysql'))
    user_agent_os = Column(Text().with_variant(String(384), 'mysql'))
    user_agent_browser = Column(Text().with_variant(String(384), 'mysql'))
    country = Column(Text().with_variant(String(2), 'mysql'))

    def __repr__(self):
        return str(self.id)
