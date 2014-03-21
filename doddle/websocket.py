# -*- coding: utf-8 -*-
# Copyright (C) 2014 Oliver Ainsworth

from __future__ import (absolute_import,
                        unicode_literals, print_function, division)

import tornado.web
import tornado.websocket


class WebSocketService(tornado.web.URLSpec):

    def __init__(self, rule, message_handler):
        self.message_handler = message_handler
        self.open_handler = None
        self.close_handler = None
        super(WebSocketService, self).__init__(rule,
                                               WebSocketHandler,
                                               {"service": self})

    def open(self, func):
        self.open_handler = func
        return self

    def close(self, func):
        self.close_handler = func
        return self


class WebSocketHandler(tornado.websocket.WebSocketHandler):

    def initialize(self, service):
        self.service = service

    def open(self):
        if self.service.open_handler is not None:
            for message in self.service.open_handler():
                self.write_message(message)

    def on_message(self, message):
        print(type(message), message)
        for response in self.service.message_handler(message):
            print("response: " + response)
            self.write_message(response)

    def on_close(self):
        if self.service.close_handler is not None:
            self.service.close_handler()


class Subprotocol(object):

    def __init__(self, message_handler):
        self._name = message_handler.__name__
        self._message_handler = message_handler
        self._open_handler = None
        self._close_handler = None
        setattr(self.__class__, self._name, self)

    def __call__(self, rule_or_func):
        if hasattr(rule_or_func, "__call__"):
            function = rule_or_func
            setattr(self, function.__name__, function)
        else:
            rule = rule_or_func
            service = WebSocketService(rule, self._message_handler)
            service.open(self._open_handler)
            service.close(self._close_handler)
            return service
