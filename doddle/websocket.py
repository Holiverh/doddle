# -*- coding: utf-8 -*-
# Copyright (C) 2014 Oliver Ainsworth

from __future__ import (absolute_import,
                        unicode_literals, print_function, division)

import contextlib
import functools

import tornado.web
import tornado.websocket


class ServiceProtocol(object):

    def __init__(self, name):
        self.protocol = Subprotocol.protocols[name]
        self.name = name
        self.async_functions = {}

    def __call__(self, function):
        self.async_functions[function.__name__] = function

        @functools.wraps(function)
        def sanity(*args, **kwargs):
            raise Exception("Can't call {} without scope".format(function))

        return sanity


class Subprotocol(object):

    protocols = {}

    @classmethod
    def decorator(cls, message_handler):
        return cls(message_handler.__name__, message_handler=message_handler)

    def __init__(self, name,
                 message_handler=None, open_handler=None, close_handler=None):
        if name in self.protocols:
            raise NameError("Subprotocol '{}' already exists".format(name))
        self.name = name
        self.message_handler = message_handler
        self.open_handler = open_handler
        self.close_handler = close_handler
        self.async_functions = {}
        self.protocols[self.name] = self

    def open(self, function):
        self.open_handler = function
        return self

    def close(self, function):
        self.close_handler = function
        return self

    def __call__(self, function):
        self.async_functions[function.__name__] = function

        @functools.wraps(function)
        def sanity(*args, **kwargs):
            raise Exception("Can't call {} without scope".format(function))

        return sanity


class ServiceSpec(tornado.web.URLSpec):

    def __init__(self, rule, protocols=None,
                 message_handler=None, open_handler=None, close_handler=None):
        self.protocols = {proto:
                          ServiceProtocol(proto) for proto in protocols or []}
        self.message_handler = message_handler
        self.open_handler = open_handler
        self.close_handler = close_handler
        self.async_functions = {}
        super(ServiceSpec, self).__init__(rule, Service, {"service": self})

    def __getattr__(self, name):
        try:
            return self.protocols[name]
        except KeyError:
            raise AttributeError(
                "Service does not support protocol '{}'".format(name))

    def open(self, function):
        self.open_handler = function
        return self

    def close(self, function):
        self.close_handler = function
        return self

    def __call__(self, function):
        self.async_functions[function.__name__] = function

        @functools.wraps(function)
        def sanity(*args, **kwargs):
            raise Exception("Can't call {} without scope".format(function))

        return sanity

    def scope(self, protocol=None):
        if not protocol:
            return self.async_functions
        else:
            # Include functions defined on the protocol it self
            scope = self.protocols[protocol].protocol.async_functions.copy()
            # Include ServiceProtocol overrides
            scope.update(self.protocols[protocol].async_functions)
            return scope

    def resolve_on_message(self, protocol=None):
        if not protocol:
            return self.message_handler
        else:
            return self.protocols[protocol].protocol.message_handler

    def resolve_on_open(self, protocol=None):
        if not protocol:
            return self.open_handler
        else:
            return self.protocols[protocol].protocol.open_handler

    def resolve_on_close(self, protocol=None):
        if not protocol:
            return self.close_handler
        else:
            return self.protocols[protocol].protocol.close_handler


class Service(tornado.websocket.WebSocketHandler):

    def initialize(self, service):
        self.service = service
        self._resolve_handlers()

    @property
    def _scope(self):
        return self._function_scope

    @_scope.setter
    def _scope(self, scope):
        self._function_scope = {}
        for name, function in scope.iteritems():
            self._function_scope[name] = self._make_async(function)

    def _resolve_handlers(self, protocol=None):
        # When initially called by initialize the scope will not be bound to
        # a protocol, however, when the a subprotocol has been selected
        # the scope must use those bound to the protocol.
        self._scope = self.service.scope(protocol)
        from pprint import pprint
        self.on_message = self._make_async(
            self.service.resolve_on_message(protocol))
        self.open = self._make_async(self.service.resolve_on_open(protocol))
        self.on_close = self._make_async(
            self.service.resolve_on_close(protocol))

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
            function = lambda *args, **kwargs: []

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

    def select_subprotocol(self, subprotocols):
        for protocol in subprotocols:
            if protocol in self.service.protocols:
                self._resolve_handlers(protocol)
                return protocol
