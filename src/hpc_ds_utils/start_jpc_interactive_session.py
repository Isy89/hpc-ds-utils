#!/usr/bin/env python3
# coding=utf-8
import sys

import cmd2

from .jlab_connector import *

PARSER = get_parser()


class JlabInteractiveConnector(cmd2.Cmd):
    def __init__(self):
        super().__init__(include_ipy=True)
        self.intro = PARSER.print_help()

    @cmd2.with_argparser(PARSER)
    def do_jpc(self, args: argparse.Namespace) -> None:
        """start the jpc command"""
        variables = vars(args)
        args.func(**{key: variables[key] for key in variables if key != "func" and not key.startswith("cmd2_")})


def main_jpc_interactive():
    app = JlabInteractiveConnector()
    app.cmdloop()


if __name__ == '__main__':
    sys.exit(main_jpc_interactive())
