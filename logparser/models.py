from sqlalchemy import BigInteger, Column, Date, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Record(Base):

    __tablename__ = 'records'

    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True, autoincrement=True)
    sha1 = Column(Text().with_variant(String(40), 'mysql'), nullable=False)
    host = Column(Text().with_variant(String(384), 'mysql'))
    date = Column(Date, nullable=False)
    method = Column(Text().with_variant(String(16), 'mysql'))
    path = Column(Text().with_variant(String(384), 'mysql'))
    query = Column(Text().with_variant(String(384), 'mysql'))
    version = Column(Text().with_variant(String(4), 'mysql'))
    status = Column(Integer)
    size = Column(BigInteger().with_variant(Integer, 'sqlite'))
    referrer_scheme = Column(Text().with_variant(String(384), 'mysql'))
    referrer_host = Column(Text().with_variant(String(384), 'mysql'))
    referrer_path = Column(Text().with_variant(String(384), 'mysql'))
    referrer_query = Column(Text().with_variant(String(384), 'mysql'))
    agent = Column(Text().with_variant(String(384), 'mysql'))
    country = Column(Text().with_variant(String(2), 'mysql'))

    def __repr__(self):
        return str(self.id)
