# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command


class Python(Command):
    description = 'Run a python interpreter'

    def __call__(self):
        try:
            from ptpython.repl import embed
            embed(globals(), None)
        except ImportError:
            try:
                from IPython import embed
                embed()
            except ImportError:
                import code
                code.interact(banner="Launching standard python repl", readfunc=None, local=globals())
