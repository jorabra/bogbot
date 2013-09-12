#!/usr/bin/env python

import sys

from sqlalchemy.orm.exc import NoResultFound
import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr

from model import Hostmask, Nickname, Consumption, Consumable
from db import DatabaseConnection

class TestBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, realname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, realname)
        self.channel = channel
        self.dbcon = DatabaseConnection()

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, srvcon, event):
        if event.arguments[0].strip().startswith("!"):
            self.do_command(event, event.arguments[0][1:])

    def add_or_update_hostmask(self, hostmask):
        nick, user, host = self.parse_hostmask(hostmask)

        with self.dbcon.scoped_db_session() as session:
            # Add check for corresponding ip-address -- host lookup
            hostmask = session.query(Hostmask).filter(Hostmask.username==user).\
                        filter(Hostmask.hostname==host).all()
            if len(hostmask) == 1:
                if nick in (obj.nickname for obj in hostmask[0].nickname):
                    print "Nickname, username and hostmask already registered."
                    return hostmask[0].id
                else:
                    print "Username and hostmask already registered; adding nick."
                    return self.dbcon.add_nick(nick, user, host)
            elif len(hostmask) > 1:
                sys.exit("Returned more than one Hostmask object.")
            else:
                print "Username and hostmask not registered; adding hostmask."
                return self.dbcon.add_hostmask(nick, user, host)
            print "What happened?"

    def add_consumption(self, hostmask_id, consumable_str, source=None):
        with self.dbcon.scoped_db_session() as session:
            consumable_qr = session.query(Consumable).\
                            filter(Consumable.name==consumable_str).all() # One?
            if len(consumable_qr) == 0:
                print "Consumable not registered. Registering."
                consumable = Consumable(consumable_str)
                session.add(consumable)
            elif len(consumable_qr) == 1:
                print "The consumable was found in database."
                consumable = consumable_qr[0]
            else:
                print "Several consumables with same name!"
                sys.exit(1)

            consumption = Consumption(source, consumable)
            hostmask = session.query(Hostmask).get(hostmask_id)
            hostmask.consumption.append(consumption)

    def do_command(self, event, cmd):
        print "%s requested command %s" % (event.source.nick, cmd)

        hostmask_id = self.add_or_update_hostmask(event.source)
        print "Hostmask ID: %s" % hostmask_id

        if cmd == "kaffe":
            self.add_consumption(hostmask_id, cmd, event.target)
            self.connection.privmsg(event.target, "Coffee added!")
        elif cmd == "brus":
            self.add_consumption(hostmask_id, cmd, event.target)
            self.connection.privmsg(event.target, "Brus added!")
        elif cmd == "halt" and event.source == "jabr!jorabra@cringer.pludre.net":
            self.die()
        elif cmd == "stats":
            for chname, chobj in self.channels.items():
                c.notice(nick, "--- Channel statistics ---")
                c.notice(nick, "Channel: " + chname)
                users = chobj.users()
                users.sort()
                c.notice(nick, "Users: " + ", ".join(users))
                opers = chobj.opers()
                opers.sort()
                c.notice(nick, "Opers: " + ", ".join(opers))
                voiced = chobj.voiced()
                voiced.sort()
                c.notice(nick, "Voiced: " + ", ".join(voiced))

    def parse_hostmask(self, hostmask):
        nick = hostmask.split('!', 1)[0]
        user_host = hostmask.split('!', 1)[1].split('@', 1)
        user = user_host[0]
        host = user_host[1]
        return nick, user, host


def main():
    import sys
    if len(sys.argv) != 5:
        print("Usage: testbot <server[:port]> <channel> <nickname> <realname>")
        sys.exit(1)

    s = sys.argv[1].split(":", 1)
    server = s[0]
    if len(s) == 2:
        try:
            port = int(s[1])
        except ValueError:
            print("Error: Erroneous port.")
            sys.exit(1)
    else:
        port = 6667
    channel = sys.argv[2]
    nickname = sys.argv[3]
    realname = sys.argv[4]

    bot = TestBot(channel, nickname, realname, server, port)
    bot.start()

if __name__ == "__main__":
    main()

