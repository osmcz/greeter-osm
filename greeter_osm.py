#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
based on greeter_osmsk.py 0.7
 skript, ktory sleduje newusers rss feed a ked objavi
 novacika editujuceho slovensko, posle mu uvitaciu spravu
"""

import argparse
import configparser
import getpass
import logging
import os
import urllib.parse

import bs4
import mechanize
import requests

#pylint: disable=no-member,unsupported-assignment-operation
#pylint: disable=invalid-name

RSSURL = 'https://resultmaps.neis-one.org/newestosmcountryfeed.php?c={}'
CONFIG = 'greeter-osm.conf'

parser = argparse.ArgumentParser(description='send OSM welcome message to '
                                 'a user with the first changeset '
                                 'made in a region')
parser.add_argument('-c', '--config',
                    metavar='config',
                    help='config file',
                    nargs=1,
                    dest='config')
parser.add_argument('-d', '--debug',
                    help='debug mode',
                    action='store_true',
                    dest='debug')
parser.add_argument('-l', '--logfile',
                    metavar='logfile',
                    help='log to file (implies -d)',
                    nargs=1,
                    dest='logfile',
                    type=str)
parser.add_argument('-n', '--no-send',
                    help='do NOT send the actual message',
                    action='store_true',
                    dest='nosend')
parser.add_argument('-u', '--user',
                    metavar='user',
                    help='send message to USER',
                    nargs=1,
                    dest='user',
                    type=str)
options = parser.parse_args()

if options.logfile:
    logging.basicConfig(level=logging.DEBUG, filename=options.logfile[0])
    logging.getLogger("requests").setLevel(logging.INFO)
elif options.debug:
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.INFO)

if options.config:
    CONFIG = options.config


def osm_auth(username, password):
    """ Login to OSM.org and returns megchanize.Browser. """
    logging.debug('Authenticating..')
    br = mechanize.Browser()
    br.set_handle_robots(False)
    br.addheaders = [('User-agent', 'https://github.com/osmcz/greeter-osm')]

    br.open("https://www.openstreetmap.org/login/")
    br.select_form(id="login_form")
    br["username"] = username
    br["password"] = password
    br.submit()

    return br


def osm_send(browser, subject, message, to):
    """ Sends message using mechanize.Browser to user in OSM """
    logging.debug('Sending %s : %s \n to %s', subject, message, to)
    browser.open("https://www.openstreetmap.org/message/new/{}".format(to))
    browser.select_form(id="new_message")
    browser["message[title]"] = subject
    browser["message[body]"] = message
    browser.submit()


config = configparser.RawConfigParser()
config.read(CONFIG, encoding="utf8")

senderlogin = config.get('Auth', 'username')
if not senderlogin:
    senderlogin = input("Username: ")

senderpass = config.get('Auth', 'password')
if not senderpass:
    senderpass = getpass.getpass("Password: ")

browser = osm_auth(senderlogin, senderpass)
rssurl = RSSURL.format(urllib.parse.quote(config.get('main', 'region')))

if not options.user:
    r = requests.get(rssurl)
    r.raise_for_status()
    if r.status_code != 200:
        raise Exception('Error getting %s' % rssurl)
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    userurls = [x.get_text() for x in soup.find_all('id')]
    userurls.reverse()
    statusfile = config.get('Files', 'statusfile')
    logging.debug('Status file: %s', statusfile)

    try:
        lastsent = open(statusfile, encoding='utf-8').read().strip()
    except IOError:
        lastsent = ''

    try:
        ind = userurls.index(lastsent)
    except ValueError:
        ind = 0

    logging.debug('we left off at %s', lastsent)
else:
    userurls = ['xxx/%s' % options.user[0]]
    ind = -1

subject = config.get('Messages', 'subject')
mainmessage = config.get('Messages', 'mainmessage')
nosourcemessage = config.get('Messages', 'nosourcemessage')
nocommentmessage = config.get('Messages', 'nocommentmessage')
ideditormessage = config.get('Messages', 'ideditormessage')

for user in userurls[ind+1:]:
    rcpt = user.split('/')[-1]
    rcpt_quoted = urllib.parse.quote(rcpt)

    message = mainmessage.replace('%', ' ').replace('<nick>', rcpt)

    r = requests.get('https://openstreetmap.org/user/%s/history' % rcpt_quoted)
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    changeset = soup.findAll('a')[0]['href']

    logging.debug("Last changeset id: %s", changeset)

    r = requests.get('https://openstreetmap.org/api/0.6%s' % changeset)
    soup = bs4.BeautifulSoup(r.text, 'html.parser')

    tags = {k['k']: k['v'] for k in soup.findAll('tag')}
    logging.debug('changeset tags: %s', tags)

    if not tags.get('source'):
        logging.debug('no source tag used for changeset')
        # only add text if user is not using iD
        if 'iD' not in tags.get('created_by'):
            message += '\n\n' + nosourcemessage

    if not tags.get('comment'):
        logging.debug('no comment tag used for changeset')
        message += '\n\n' + nocommentmessage

    if 'iD' in tags.get('created_by'):
        logging.debug('iD editor detected')
        message += '\n\n' + ideditormessage

    logging.debug('sending message to user %s', rcpt)
    if not options.nosend:
        osm_send(browser, subject, message, rcpt_quoted)
    else:
        logging.debug('NOT sending (because you said so) the message to user %s', rcpt)
    if not options.user:
        with open(statusfile, 'w', encoding='utf-8') as f:
            f.write(user)
