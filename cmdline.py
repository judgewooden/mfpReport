""" reports for myfitnesspal data """
# pylint: disable=broad-except
# pylint: disable=import-outside-toplevel

import argparse
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

from commands import COMMANDS, get_command_list, load_config

logger = logging.getLogger(__name__)


def main(args=None):
    """ run from command line """

    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        epilog=get_command_list(), formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", type=str, nargs=1, choices=COMMANDS.keys())
    parser.add_argument("--configfile", type=str, nargs="?", default="config.json")
    parser.add_argument("--loglevel", type=str, default="INFO")
    parser.add_argument("--traceback-locals", action="store_true")
    parser.add_argument("--debugger", action="store_true")
    args, extra = parser.parse_known_args()

    # Set up a simple console logger
    logging.basicConfig(level=args.loglevel)

    console = Console()

    load_config(args.configfile)

    if args.debugger:
        import debugpy

        console.print("[blue]Awaiting debugger connection on 0.0.0.0:5678...[/blue]")
        debugpy.listen(("0.0.0.0", 5678))
        debugpy.wait_for_client()

    logging.basicConfig(
        level=args.loglevel,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )

    try:
        if args.command[0] in COMMANDS:
            COMMANDS[args.command[0]]["function"](args, *extra)
    except Exception:
        console.print_exception(show_locals=args.traceback_locals)
        console.print(
            "[bold][red] An unexpected error occurred while processing your "
            "request; please create a bug issue at "
            "http://github.com/coddingtonbear/python-myfitnesspal/issues "
            "including the above traceback and a description of what "
            "you were trying to accomplish.[/red][/bold]"
        )

if __name__ == "__main__":
    main()
