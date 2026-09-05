"""python -m mutate4py 入口:env 只带 repo_root 与展示用命令名。"""

import os
import sys

from . import cli


def run(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    env = {"repo_root": os.getcwd(), "command": "python -m mutate4py"}
    return int(cli.main(args, env) or 0)


if __name__ == "__main__":
    sys.exit(run())
