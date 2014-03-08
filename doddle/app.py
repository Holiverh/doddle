# -*- coding: utf-8 -*-
# Copyright (C) 2014 Oliver Ainsworth

from __future__ import (absolute_import,
                        unicode_literals, print_function, division)

import re

import tornado.ioloop
import tornado.web

import doddle.view


RE_RULE_VARIABLE = re.compile(r"<(int|float|path):([A-Za-z_][A-Za-z0-9_]+)>")


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
            urlspec = tornado.web.URLSpec(
                rewrite_rule(rule),
                doddle.view.View,
                {
                    "view_func": func,
                    "methods": methods,
                }
            )
            self.add_handlers(self.host, [urlspec])
            return urlspec

        return decorator
