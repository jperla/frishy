#!/usr/bin/env python
from __future__ import absolute_import

import os
import urllib
import datetime

import couchdb

import webify
from webify.templates.helpers import html
from webify.controllers import webargs

app = webify.defaults.app()

@app.controller(path='/')
def index(req):
    yield u'Hello, world!'

@app.controller()
@webargs.add(webargs.RemainingUrl())
@webargs.add(webargs.SettingsArgParser('updates_db'))
@webargs.add(webargs.SettingsArgParser('users_db'))
def profile(req, remaining, updates_db=None, users_db=None):
    name, id, _ = remaining.split(u'/', 2)
    updates = updates_db.view('_design/updates/_view/updates_by_profile',
                              startkey=[id], endkey=[id, {}], include_docs=True)
    yield html.h1(name.replace('_', ' '))
    for u in updates:
        yield u[u'value']
        yield u' <b style="font-size:smaller;">'
        yield webify.templates.helpers.time.fuzzy_time_diff(datetime.datetime.fromtimestamp(u.doc['date']))
        yield u' ago'
        yield u'</b>'
        yield u'<br />'

    friends = users_db.view('_design/users/_view/friends',
                            startkey=[id], endkey=[id, {}], include_docs=True)
    yield html.h2(u'Friends')
    for f in friends:
        if f[u'key'][1] == 1:
            yield html.a(profile.url(f.doc[u'name'].replace(' ', '_') + u'/' + f.doc.id + u'/'), f.doc[u'name'])
            yield u'<br />'


    

    
    

# Middleware
from webify.middleware import install_middleware, EvalException, SettingsMiddleware

# Server
from webify.http import server
if __name__ == '__main__':
    mail_server = webify.email.LocalMailServer()
    users_db = couchdb.client.Database('htp://localhost:5984/frishy-users')
    updates_db = couchdb.client.Database('htp://localhost:5984/frishy-updates')
    settings = {
                'mail_server': mail_server,
                'users_db': users_db,
                'updates_db': updates_db,
               }

    wrapped_app = install_middleware(app, [
                                            SettingsMiddleware(settings),
                                            EvalException,
                                          ])

    print 'Loading server...'
    server.serve(wrapped_app, host='127.0.0.1', port=8085, reload=True)

