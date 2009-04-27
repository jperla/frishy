#!/usr/bin/env python
from __future__ import absolute_import

import os
import urllib

import webify
from webify.templates.helpers import html
from webify.controllers import webargs

app = webify.defaults.app()

@app.controller(path='/')
def index(req):
    yield u'Hello, world!'

# Middleware
from webify.middleware import install_middleware, EvalException, SettingsMiddleware

# Server
from webify.http import server
if __name__ == '__main__':
    mail_server = webify.email.LocalMailServer()
    settings = {
                'mail_server': mail_server
               }

    wrapped_app = install_middleware(app, [
                                            SettingsMiddleware(settings),
                                            EvalException,
                                          ])

    print 'Loading server...'
    server.serve(wrapped_app, host='127.0.0.1', port=8085, reload=True)

