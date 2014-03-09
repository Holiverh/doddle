# -*- coding: utf-8 -*-
# Copyright (C) 2014 Oliver Ainsworth

from __future__ import (absolute_import,
                        unicode_literals, print_function, division)

import collections

import tornado.web

import doddle.response


class View(tornado.web.RequestHandler):

    def initialize(self, view_func, methods):
        self.view_func = view_func
        self.methods = [method.upper() for method in methods]
        for method in methods:
            if method not in self.SUPPORTED_METHODS:
                raise ValueError("Unknown HTTP method '{}'".format(method))

    def make_response(self, view_response):
        response = doddle.response.Response("", 200,
                                            {"content-type": "text/html"})
        if isinstance(view_response, doddle.response.Response):
            return view_response
        if isinstance(view_response, bytes):
            response.content = view_response
        elif (isinstance(view_response, collections.Sequence)
                and not isinstance(view_response, basestring)):
            pass
        elif hasattr(view_response, "__call__"):
            # TODO: WSGI application delegate
            pass
        elif response is None:
            raise TypeError("View function returned None")
        else:
            # Slight deviation from Flask here. Flask will default to
            # treating it as a WSGI application but it seems far more
            # reasonable to try coerce the response into a string.
            response.content = unicode(view_response)
        return response

    def handle(self, **kwargs):
        if self.request.method not in self.methods:
            response = doddle.response.Response("405 Not Supported", 405)
        else:
            response = self.make_response(self.view_func(**kwargs))
        self.set_status(response.status_code)
        for header, value in response.headers.iteritems():
            self.set_header(header, value)
        if response.status_code != 204:
            self.write(response.content)
        self.finish()

    def options(self, **kwargs):
        self.handle(**kwargs)

    def get(self, **kwargs):
        self.handle(**kwargs)

    def head(self, **kwargs):
        self.handle(**kwargs)

    def post(self, **kwargs):
        self.handle(**kwargs)

    def put(self, **kwargs):
        self.handle(**kwargs)

    def delete(self, **kwargs):
        self.handle(**kwargs)

    def patch(self, **kwargs):
        self.handle(**kwargs)
