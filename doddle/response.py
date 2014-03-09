# -*- coding: utf-8 -*-
# Copyright (C) 2014 Oliver Ainsworth

from __future__ import (absolute_import,
                        unicode_literals, print_function, division)

import tornado.httputil


class Response(object):

    def __init__(self, content, status_code=200, headers={}):
        self.status_code = status_code
        # Set headers first so we can append 'chartset' to Content-Type
        # if we're encoding Unicode
        self.headers = headers
        self.content = content

    @property
    def status_code(self):
        return self._status_code

    @status_code.setter
    def status_code(self, status_code):
        self._status_code = int(status_code)

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, headers):
        self._headers = tornado.httputil.HTTPHeaders(headers)

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, content):
        if isinstance(content, bytes):
            self._content = content
        else:
            # Assume Unicode
            self._content = content.encode("utf-8")
            if "content-type" in self.headers:
                self.headers["content-type"] += "; charset=utf-8"
