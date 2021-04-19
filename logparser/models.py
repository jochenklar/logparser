from sqlalchemy import BigInteger, Column, Date, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Record(Base):

    __tablename__ = 'records'

    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True, autoincrement=True)
    sha1 = Column(Text().with_variant(String(40), 'mysql'), nullable=False, index=True)
    host = Column(Text().with_variant(String(384), 'mysql'), index=True)
    date = Column(Date, nullable=False, index=True)
    method = Column(Text().with_variant(String(16), 'mysql'), index=True)
    path = Column(Text().with_variant(String(384), 'mysql'), index=True)
    query = Column(Text().with_variant(String(384), 'mysql'), index=True)
    version = Column(Text().with_variant(String(4), 'mysql'), index=True)
    status = Column(Integer, index=True)
    size = Column(BigInteger().with_variant(Integer, 'sqlite'), index=True)
    referrer_scheme = Column(Text().with_variant(String(384), 'mysql'), index=True)
    referrer_host = Column(Text().with_variant(String(384), 'mysql'), index=True)
    referrer_path = Column(Text().with_variant(String(384), 'mysql'), index=True)
    referrer_query = Column(Text().with_variant(String(384), 'mysql'), index=True)
    agent = Column(Text().with_variant(String(384), 'mysql'), index=True)
    country = Column(Text().with_variant(String(2), 'mysql'), index=True)

    def __repr__(self):
        return str(self.id)
