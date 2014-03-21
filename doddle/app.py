# -*- coding: utf-8 -*-
# Copyright (C) 2014 Oliver Ainsworth

from __future__ import (absolute_import,
                        unicode_literals, print_function, division)

import tornado.ioloop
import tornado.web

import doddle.websocket

import doddle.view


class Doddle(tornado.web.Application):

    def __init__(self, name, host):
        super(Doddle, self).__init__(default_host=host)
        self._ioloop = tornado.ioloop.IOLoop.instance()
        self.host = host
        self.name = name

    def run(self, host=None, port=5000):
        if host is None:
            host = self.host
        self.listen(port, host)
        self._ioloop.start()

    def route(self, rule, methods=["GET", "HEAD"]):

        def decorator(func):
            urlspec = doddle.view.Rule(rule, func, methods)
            self.add_handlers(self.host, [urlspec])
            return urlspec

        return decorator

    def websocket(self, rule):

        def decorator(func):
            urlspec = doddle.websocket.WebSocketService(rule, func)
            self.add_handlers(self.host, [urlspec])
            return urlspec

        return decorator

    websocket.subprotocol = doddle.websocket.Subprotocol
