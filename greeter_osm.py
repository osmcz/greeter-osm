#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
greeter_osmsk.py 0.7
 skript, ktory sleduje newusers rss feed a ked objavi
 novacika editujuceho slovensko, posle mu uvitaciu spravu
"""

import argparse
import configparser
import logging
import os
import sys

import bs4
import requests

RSSURL = 'http://resultmaps.neis-one.org/newestosmcountryfeed.php?c={}'

parser = argparse.ArgumentParser(description='send OSM welcome message to '
                                 'a user with the first changeset '
                                 'made in a region')
parser.add_argument('-d',
                    help='debug mode',
                    action='store_true',
                    dest='debug')
parser.add_argument('-l',
                    metavar='logfile',
                    help='log to file (implies -d)',
                    nargs=1,
                    type=str)
parser.add_argument('-n',
                    help='do NOT send the actual message',
                    action='store_true',
                    dest='nosend')
parser.add_argument('-u',
                    metavar='user',
                    help='send message to USER',
                    nargs=1,
                    type=str)
options = parser.parse_args()

if options.l:
    logging.basicConfig(level=logging.DEBUG, filename=options.l[0])
    logging.getLogger("requests").setLevel(logging.INFO)
elif options.debug:
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.INFO)

req_cookies = {}


def osm_auth(cookies):
    logging.debug('Authenticating..')
    req_auth = requests.get('https://www.openstreetmap.org/')
    cookies = req_auth.cookies
    soup_auth = bs4.BeautifulSoup(req_auth.text, 'html.parser')
    token_auth = soup_auth.find('meta', attrs={'name': 'csrf-token'})['content']

    data = {'username': senderlogin,
            'password': senderpass,
            'authenticity_token': token_auth,
            }
    req_auth = requests.post('https://www.openstreetmap.org/login',
                      data=data, cookies=cookies)
    logging.debug('OSM cookies: %s', cookies)
    soup_auth = bs4.BeautifulSoup(req_auth.text, 'html.parser')
    token_auth = soup_auth.find('meta', attrs={'name': 'csrf-token'})['content']
    if token_auth:
        return token_auth
    else:
        raise Exception("token could not be obtained")


def osm_send(token, subject, message, rcpt, cookies):
    data = {'authenticity_token': token,
            'message[title]': subject,
            'display_name': rcpt,
            'message[body]': message,
            'commit': 'Odoslať'
            }
    req_send = requests.post('https://www.openstreetmap.org/messages',
                      data=data, cookies=cookies)
    req_send.raise_for_status()


config = configparser.RawConfigParser()
currdir = os.path.dirname(sys.argv[0])
config.read(os.path.join(currdir, '.greeterrc'))

os.chdir(currdir)

senderlogin = config.get('Auth', 'username')
senderpass = config.get('Auth', 'password')

token = osm_auth(req_cookies)
logging.debug('OSM token is %s', token)

rssurl = RSSURL.format(config.get('main', 'region'))

if not options.u:
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
    userurls = ['xxx/%s' % options.u[0]]
    ind = -1

mainmessage = config.get('Messages', 'mainmessage')
nosourcemessage = config.get('Messages', 'nosourcemessage')
nocommentmessage = config.get('Messages', 'nocommentmessage')
ideditormessage = config.get('Messages', 'ideditormessage')

for user in userurls[ind+1:]:
    rcpt = user.split('/')[-1]

    message = mainmessage.replace('%', ' ').replace('<nick>', rcpt)

    r = requests.get('http://openstreetmap.org/user/%s/history' % rcpt)
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    changeset = soup.findAll('a')[0]['href']

    logging.debug("Last changeset id: %s", changeset)

    r = requests.get('http://openstreetmap.org/api/0.6%s' % changeset)
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

    if not options.nosend:
        logging.debug('sending message to user %s', rcpt)
        osm_send(token, 'Privitanie', message, rcpt, req_cookies)
    else:
        logging.debug('NOT sending (because you said so) the message to user %s', rcpt)
    if not options.u:
        with open(statusfile, 'w', encoding='utf-8') as f:
            f.write(user)
