from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from model import Hostmask, Nickname, drop, create


class DatabaseConnection(object):

    def __init__(self):
        self.engine = create_engine('sqlite:///botbot.db')
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        if self.Session is not None:
            return self.Session()

    @contextmanager
    def scoped_db_session(self):
        session = self.Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def add_hostmask(self, nickname, username, hostname):
        hostmask = Hostmask(username, hostname)
        n = Nickname(nickname)
        hostmask.nickname.append(n)

        with self.scoped_db_session() as session:
            session.add(hostmask)
            session.commit()
            if hostmask.id is None:
                sys.exit("hostmask ID not given")
            return hostmask.id

    def add_nick(self, nickname, username, hostname):
        hostmask_id = None
        with self.scoped_db_session() as session:
            try:
                hostmask = session.query(Hostmask).\
                            filter(Hostmask.username==username).\
                            filter(Hostmask.hostname==hostname).one()
                hostmask.nickname.append(Nickname(nickname))
                session.add(hostmask)
                hostmask_id = hostmask.id
            except NoResultFound, e:
                print e
        return hostmask_id

    def drop_and_create_db(self):
        drop(self.engine)
        create(self.engine)

