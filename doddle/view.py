# -*- coding: utf-8 -*-
# Copyright (C) 2014 Oliver Ainsworth

from __future__ import (absolute_import,
                        unicode_literals, print_function, division)

import re

import tornado.httputil
import tornado.web

import doddle.response


class Rule(tornado.web.URLSpec):

    def __init__(self, rule, view_func, methods):
        self.converters = {}
        url_spec = ""
        start = 0
        for char in "\\.^$+?[]{}|()<>":
            rule = rule.replace(char, "\\" + char)
        for match in BaseConverter.re_rule_variable.finditer(rule):
            type_ = BaseConverter.converters.get(match.group("type"),
                                                 StringConverter)()
            identifier = match.group("identifier")
            self.converters[identifier] = type_
            url_spec += rule[start:match.start()]
            start = match.end()
            regex = type_.regex
            url_spec += "(?P<" + identifier + ">" + regex + ")"
        url_spec += rule[start:]
        kwargs = {
            "rule": self,
            "view_func": view_func,
            "methods": methods,
        }
        super(Rule, self).__init__(url_spec, View, kwargs, view_func.__name__)

    def to_python(self, identifier, value):
        return self.converters[identifier].to_python(value)


class BaseConverter(object):

    name = None

    class __metaclass__(type):

        converters = {}

        def __new__(meta, name, bases, attrs):
            if "name" not in attrs:
                raise AttributeError("Converter must have a 'name' attribute")
            if attrs["name"] in meta.converters:
                raise KeyError("Converter with name '{}' "
                               "already exists".format(attrs["name"]))
            attrs["converters"] = meta.converters
            cls = type.__new__(meta, name, bases, attrs)
            if attrs["name"] is not None:
                meta.converters[attrs["name"]] = cls
            return cls

        @property
        def re_rule_variable(cls):
            names = "|".join(cls.converters.iterkeys())
            return re.compile(r"<(?:(?P<type>" + names +
                               "):)?(?P<identifier>[A-Za-z_][A-Za-z0-9_]+)>")


class StringConverter(BaseConverter):

    name = "str"
    regex = r"[^/]+"

    def to_python(self, value):
        return unicode(value)


class IntegerConverter(BaseConverter):

    name = "int"
    regex = r"-?\d+"

    def to_python(self, value):
        return int(value)


class FloatConverter(BaseConverter):

    name = "float"
    regex = r"(\d+\.\d+|\d+|\.\d+|\d+\.)s"

    def to_python(self, value):
        return float(value)


class PathConverter(BaseConverter):

    name = "path"
    regex = r"[A-Za-z0-9\-._~!$&'()*+,;=:@/]+"

    def to_python(self, value):
        return unicode(value)


class View(tornado.web.RequestHandler):

    def initialize(self, rule, view_func, methods):
        self.rule = rule
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
        elif isinstance(view_response, tuple):
            content, status_or_headers, headers = \
                view_response + (None,) * (3 - len(view_response))
            if content is None:
                raise TypeError("View function returned None")
            if isinstance(status_or_headers,
                          (dict, tornado.httputil.HTTPHeaders)):
                headers = status_or_headers
                status_or_headers = None
            if status_or_headers is not None:
                # TODO: differentiate between status codes and reasons
                response.status_code = status_or_headers
            if headers:
                response.headers.update(headers)
            response.content = content
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
        for identifier in kwargs:
            kwargs[identifier] = self.rule.to_python(identifier,
                                                     kwargs[identifier])
        print(kwargs)
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
