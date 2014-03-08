# -*- coding: utf-8 -*-
# Copyright (C) 2014 Oliver Ainsworth

from __future__ import (absolute_import,
                        unicode_literals, print_function, division)

import collections
import re

import tornado.ioloop
import tornado.web


RE_RULE_VARIABLE = re.compile(r"<(int|float|path):([A-Za-z_][A-Za-z0-9_]+)>")
HTTP_METHODS = [
    "OPTIONS",
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
]


def rewrite_rule(rule):
    # TODO: plain string variables
    new_rule = ""
    start = 0
    for match in RE_RULE_VARIABLE.finditer(rule):
        type_ = match.groups()[0]
        name = match.groups()[1]
        new_rule += rule[start:match.start()]
        start = match.end()
        if type_ == "int":
            regex = r"\d+"
        elif type_ == "float":
            regex = r"(\d+\.\d+|\d+|\.\d+|\d+\.)"
        elif type_ == "path":
            # TODO: investigate how Tornado deals with escaped characters
            #       and deal with them if they're not handled at the Tornado
            #       level
            regex = r"[A-Za-z0-9\-._~!$&'()*+,;=:@/]+"
        new_rule += "(?P<{}>{})".format(name, regex)
    return new_rule


class View(tornado.web.RequestHandler):

    def initialize(self, view_func):
        self.view_func = view_func

    def get(self, **kwargs):
        body = b""
        status_code = 200
        headers = {
            "Content-Type": "text/html",
        }
        raw_response = self.view_func(**kwargs)
        if isinstance(raw_response, bytes):
            body = raw_response
        elif isinstance(raw_response, unicode):
            headers["Content-Type"] += "; charset=UTF-8"
            body = raw_response.encode("utf8")
        elif isinstance(raw_response, collections.Sequence):
            # TODO: Do it properly
            # TODO: Handle Unicode bodies
            if len(raw_response) == 2:
                # (body, headers)
                body, headers = raw_response
            elif len(raw_response) == 3:
                # (body, status_code, headers)
                body, status_code, headers = raw_response
            else:
                raise TypeError("View function returned sequence but it "
                                "wasn't in the form (body, headers) or"
                                "(body, status, headers)")
        #elif hasattr(raw_response, "__call__"):
            ## WSGI function
            #pass
        else:
            raise TypeError("View function didn't return a response")
        self.set_status(status_code)
        for header, value in headers.iteritems():
            self.set_header(header, value)
        self.write(body)
        self.finish()


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
        for method in methods:
            if method.upper() not in HTTP_METHODS:
                raise ValueError("Unknown HTTP method '{}'".format(method))

        def decorator(func):
            urlspec = tornado.web.URLSpec(
                rewrite_rule(rule),
                View,
                {"view_func": func}
            )
            self.add_handlers(self.host, [urlspec])
            return urlspec

        return decorator

