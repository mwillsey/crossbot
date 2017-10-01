#!/usr/bin/env python3

import sys

from crossbot import Crossbot, Request

if __name__ == "__main__":

    client  = Crossbot()
    request = Request(' '.join(sys.argv[1:]))
    client.handle_request(request)
