from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref


Base = declarative_base()

class Hostmask(Base):
    __tablename__ = "hostmask"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    hostname = Column(String, nullable=False)
    added = Column(DateTime, default=datetime.now, nullable=False)

    __table_args__ = (UniqueConstraint(username, hostname, name='username_host_uc'),)

    def __init__(self, username, hostname):
        self.username = username
        self.hostname = hostname


class Nickname(Base):
    __tablename__ = "nickname"

    id = Column(Integer, primary_key=True)
    nickname = Column(String, nullable=False)
    first_seen = Column(DateTime, default=datetime.now, nullable=False)
    last_seen = Column(DateTime, default=datetime.now, nullable=False)

    hostmask_id = Column(Integer, ForeignKey('hostmask.id'), nullable=False)
    hostmask = relationship('Hostmask', backref=backref('nickname', order_by=id))

    def __init__(self, nickname):
        self.nickname = nickname


class Consumption(Base):
    __tablename__ = "consumption"

    id = Column(Integer, primary_key=True)
    when = Column(DateTime, default=datetime.now) 
    channel = Column(String)

    hostmask_id = Column(Integer, ForeignKey('hostmask.id'))
    hostmask = relationship('Hostmask', backref=backref('consumption', order_by=id))

    consumable = relationship("Consumable", uselist=False, backref="consumption")

    def __init__(self, channel=None, consumable=None):
        self.channel = channel
        self.consumable = consumable


class Consumable(Base):
    __tablename__ = "consumable"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    added = Column(DateTime, default=datetime.now, nullable=False)

    consumption_id = Column(Integer, ForeignKey('consumption.id'))

    def __init__(self, name):
        self.name = name


class URL(Base):
    __tablename__ = "url"

    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    added = Column(DateTime, nullable=False)
    channel = Column(String)

    hostmask_id = Column(Integer, ForeignKey('hostmask.id'))
    hostmask = relationship('Hostmask', backref=backref('url', order_by=id))


def drop(engine):
    Base.metadata.drop_all(engine)

def create(engine):
    Base.metadata.create_all(engine)

