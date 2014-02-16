#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import traceback

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
import irc.bot
import irc.logging
import irc.strings
import lxml.html
import requests

from db import DatabaseConnection
from model import Hostmask, Nickname, Consumption, Consumable
from spotify_lookup import SpotifyLookup


class BogBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, realname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, realname)
        self.channel = channel
        self.dbcon = DatabaseConnection()

    def on_disconnect(self, c, e):
        raise SystemExit()

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, srvcon, event):
        try:
            if event.arguments[0].strip().startswith("!"):
                self.do_command(event, event.arguments[0][1:])
            else:
                self.process_text(event)
        except Exception as e:
            exc_type, exc_obj, exc_traceback = sys.exc_info()
            tb = traceback.format_list(traceback.extract_tb(exc_traceback)[-1:])[-1]
            tb = ''.join(tb.splitlines())
            msg = "%s: %s  %s" % (exc_type, e, tb)
            if len(msg) > 400:
                msg = "%s %s %s" % (msg[:340], "...", msg[-50])
            self.connection.privmsg("jabr", msg)

    def process_text(self, event):
        message = event.arguments[0]
        if "http" in  message:
            start = message.find("http")
            end = message.find(" ", start)
            if end == -1:
                url = message[start:]
            else:
                url = message[start:end]

            if "spotify" in url:
                spl = SpotifyLookup()
                spotify_meta = spl.lookup(url)
                self.connection.notice(event.target, spotify_meta)
                return

            url_meta = self._get_url_meta_string(url)
            if url_meta:
                self.connection.notice(event.target, url_meta)

    def _get_url_meta_string(self, url):
        meta = ""
        response = requests.get(url)
        if url != response.url:
            meta = "%s )> " % response.url
        title = self._get_html_title(response.text)
        if title is not None:
            meta = "%s%s" % (meta, title)
            return meta
        else:
            return None

    def _get_html_title(self, document):
        """
        Parse the string representation ('document') of the web page.
        """
        parsed_doc = lxml.html.document_fromstring(document)
        title = parsed_doc.find(".//title")
        if title is not None:
            return title.text
        return None

    def add_or_update_hostmask(self, hostmask_str):
        nick, user, host = self.parse_hostmask(hostmask_str)
        hostmask_id, nick_present = self.is_nick_in_hostmask(nick, user, host)

        if hostmask_id is not None:
            if nick_present:
                print "Nickname, username and hostmask already registered."
                return hostmask_id
            else:
                print "Username and hostmask already registered; adding nick."
                return self.dbcon.add_nick(nick, user, host)
        else:
            print "Username and hostmask not registered; adding hostmask."
            return self.dbcon.add_hostmask(nick, user, host)

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

    def is_nick_in_hostmask(self, nick, user, host):
        with self.dbcon.scoped_ro_db_session() as session:
            try:
                hostmask = session.query(Hostmask).\
                            filter(Hostmask.username==user).\
                            filter(Hostmask.hostname==host).one()
            except MultipleResultsFound, e:
                print "Multiple hostmasks found for username and hostname. Should not be possible: %s" % e
                sys.exit(1)
            except NoResultFound, e:
                return None, False

            if nick in (nickname.nickname for nickname in hostmask.nickname):
                return hostmask.id, True
            else:
                return hostmask.id, False


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('server')
    parser.add_argument('channel')
    parser.add_argument('nickname')
    parser.add_argument('realname')
    parser.add_argument('-p', '--port', default=6667, type=int)
    irc.logging.add_arguments(parser)
    return parser.parse_args()

def main():

    args = get_args()
    irc.logging.setup(args)

    bot = BogBot(args.channel, args.nickname, args.realname, args.server, args.port)
    bot.start()

if __name__ == "__main__":
    main()

