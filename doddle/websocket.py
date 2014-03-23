# -*- coding: utf-8 -*-
# Copyright (C) 2014 Oliver Ainsworth

from __future__ import (absolute_import,
                        unicode_literals, print_function, division)

import contextlib
import functools

import tornado.web
import tornado.websocket


class ServiceSpec(tornado.web.URLSpec):

    def __init__(self, rule, protocols=None,
                 message_handler=None, open_handler=None, close_handler=None):
        self.protocols = protocols or []
        self.message_handler = message_handler
        self.open_handler = open_handler
        self.close_handler = close_handler
        self.async_functions = set()
        super(ServiceSpec, self).__init__(rule, Service, {"service": self})

    def open(self, function):
        self.open_handler = function
        return self

    def close(self, function):
        self.close_handler = function
        return self

    def __call__(self, function):
        self.async_functions.add(function)

        @functools.wraps(function)
        def sanity(*args, **kwargs):
            raise Exception("Can't call {} without scope".format(function))

        return sanity


class Service(tornado.websocket.WebSocketHandler):

    def initialize(self, service):
        self.service = service
        self._scope = {}
        for async in self.service.async_functions:
            self._scope[async.__name__] = self._make_async(async)

    @contextlib.contextmanager
    def scope(self, function):
        old = {}
        for name, callable_ in self._scope.iteritems():
            if name in function.__globals__:
                old[name] = function.__globals__[name]
            function.__globals__[name] = callable_
        yield
        for name in self._scope:
            if name in old:
                function.__globals__[name] = old[name]
            else:
                del function.__globals__[name]

    def _make_async(self, function):
        if function is None:
            function = lambda: []

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            with self.scope(function):
                returned = function(*args, **kwargs)
                if returned is not None:
                    for message in function(*args, **kwargs):
                        if not isinstance(message, unicode):
                            raise TypeError("Message was not of type unicode")
                        try:
                            self.write_message(message)
                        except tornado.websocket.WebSocketClosedError:
                            pass

        return wrapper

    @property
    def open(self):
        return self._make_async(self.service.open_handler)

    @property
    def on_message(self):
        return self._make_async(self.service.message_handler)

    @property
    def on_close(self):
        return self._make_async(self.service.close_handler)
