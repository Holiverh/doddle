# -*- coding: utf-8 -*-
# Copyright (C) 2014 Oliver Ainsworth

from __future__ import (absolute_import,
                        unicode_literals, print_function, division)


class Response(object):

    def __init__(self, content, status_code=200, headers={}):
        self.status_code = int(status_code)
        self.headers = headers
        if isinstance(content, bytes):
            self.content = content
        else:
            # Assume Unicode
            self.content = content.encode("utf-8")
            if "content-type" in headers:
                headers["content-type"] += "; charset=utf-8"
