""" various commands to generate custom reports """
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-module-docstring
# pylint: disable=line-too-long
# pylint: disable=unused-argument
# pylint: disable=unspecified-encoding
# pylint: disable=no-member
# pylint: disable=redefined-builtin

from pathlib import Path
import argparse
import logging
import locale

import datetime as dt
from typing import Dict, Callable
from typing_extensions import TypedDict

from dateutil.parser import parse as dateparse
from PyPDF2 import PdfReader, PdfWriter
from rich import print

from graph import weight_graph, calorie_graph, year_nutrients_heatmap, year_stats_heatmap
from report import pdf_report, html_report

from mfp import MFPReport
mfp = MFPReport()

class CommandDefinition(TypedDict):
    function: Callable
    description: str

COMMANDS: Dict[str, CommandDefinition] = {}

logger = logging.getLogger(__name__)

def get_command_list():
    command_lines = []
    for name, info in COMMANDS.items():
        message = f"{name}: {info['description']}"
        command_lines.append(message)
    prolog = "available commands:\n"
    return prolog + "\n".join(["  " + cmd for cmd in command_lines])


def command(desc, name=None):

    def decorator(func):
        main_name = name if name else func.__name__
        command_details: CommandDefinition = {
            "function": func,
            "description": desc,
        }

        COMMANDS[main_name] = command_details
        return func

    return decorator


def load_config(configfile):
    if Path(configfile).is_file():
        mfp.read_config(configfile)
    locale.setlocale(locale.LC_TIME, mfp.locale)


def check_and_rename(file_path: Path, file_name: str, file_ext: str=None, unique: bool=False) -> Path:
    """ create path, check if file exist and rename if needed """
    if file_ext is None or len(file_ext) == 0:
        file_end = ""
    else:
        file_end = f".{file_ext}"
    if file_path is None:
        file_path = ""
    else:
        Path(file_path).mkdir(parents=True, exist_ok=True)
    answer = Path(file_path, f"{file_name}{file_end}")
    if not unique:
        return answer
    for loop in range(100):
        if not Path(answer).is_file():
            return answer
        answer = Path(file_path, f"{file_name}_{loop+1}{file_end}")
    raise ValueError("Checked 100 times, could not find a unique filename")


def add_page(writer, buffer):
    """ resize a pdf page and add to writer """
    pdf = PdfReader(buffer)
    for page in pdf.pages:
        # page = pdf.pages[]
        page.scale_to(mfp.landscape_width * 72, mfp.landscape_height * 72)
        page.compress_content_streams()
        writer.add_page(page)


@command(
    """Create a json file containing the configuration"""
)
def config(args, *extra, **kwargs):
    filename = check_and_rename(mfp.output_directory, "config", "json", unique=True)
    mfp.save_config(filename=filename)
    print(f"Save {filename}")


@command(
    """Create a combined pdf report going back (x) weeks, from (x) date
            default: week = 1, date = today
            e.g. combined 4 2021-12-31"""
)
def combined(args, *extra, **kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "weeks",
        nargs="?",
        default=1,
        type=int,
        help="The number of weeks to go back.",
    )
    parser.add_argument(
        "date",
        nargs="?",
        default=None,
        type=lambda datestr: dateparse(datestr).date(),
        help="The date for which to display information.",
    )
    args = parser.parse_args(extra)

    print("Running combined report with", args)

    print("Getting latest data")
    mfp.to_csv()

    df_data = mfp.load_df()
    df_mfp = mfp.pivot_df(df_data)
    df_body = mfp.load_weight_df()

    if args.date is None:
        end_date = max([df_data.index.max(), df_body.index.max()])
    else:
        end_date = dt.datetime( year=args.date.year,
                                month=args.date.month,
                                day=args.date.day )
    year = end_date.year
    start_date = max(df_data.index.min() + dt.timedelta(3), end_date - dt.timedelta(days=365))

    writer = PdfWriter()
    print('Preparing weight graph')
    add_page(writer, weight_graph(mfp, df_body, start_date, end_date))
    print('Preparing calorie graph')
    add_page(writer, calorie_graph(mfp, df_mfp, df_body, start_date, end_date))

    end_date = df_data.index.max()
    for looper in range(args.weeks):
        next_date = end_date - dt.timedelta(days=looper * 7)
        print('Preparing report for', next_date)
        add_page(writer, pdf_report(mfp, df_data=df_data, end_date=next_date))

    print(f"Preparing stats heatmap: {year}")
    add_page(writer, year_stats_heatmap(mfp, df_mfp, year))
    print(f"Preparing nutrition heatmap: {year}")
    add_page(writer, year_nutrients_heatmap(mfp, df_mfp, year))

    filename = check_and_rename(mfp.output_directory, "combined", "pdf", unique=False)
    with open(filename, 'wb') as output:
        writer.write(output)
    print("Save:", filename)

@command(
    """Create a yearly report showing all data for year (x)
          default: year = curren
          e.g. yearly 2021"""
)
def yearly(args, *extra, **kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "year",
        nargs="?",
        default=dt.date.today().year,
        type=int,
        help="The year of the report"
    )
    args = parser.parse_args(extra)

    print("Running yearly report with", args)

    df_data = mfp.load_df()
    df_mfp = mfp.pivot_df(df_data)
    df_body = mfp.load_weight_df()

    start_date = dt.datetime( year=args.year, month=1, day=1 )
    end_date = dt.datetime( year=args.year, month=12, day=31 )

    writer = PdfWriter()
    print('Preparing weight graph')
    add_page(writer, weight_graph(mfp, df_body, start_date, end_date))
    print('Preparing calorie graph')
    add_page(writer, calorie_graph(mfp, df_mfp, df_body, start_date, end_date))

    print(f"Preparing stats heatmap: {args.year}")
    add_page(writer, year_stats_heatmap(mfp, df_mfp, args.year))
    print(f"Preparing nutrition heatmap: {args.year}")
    add_page(writer, year_nutrients_heatmap(mfp, df_mfp, args.year))

    filename = check_and_rename(mfp.output_directory, f"year_{args.year}", "pdf", unique=False)
    with open(filename, 'wb') as output:
        writer.write(output)
    print("Save:", filename)

@command(
    """Create a food pdf report going back (x) weeks, from (x) date
          default: week = 2, date = today
          e.g. report 3 2021-12-31"""
)
def report(args, *extra, **kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "weeks",
        nargs="?",
        default=2,
        type=int,
        help="The number of weeks to go back.",
    )
    parser.add_argument(
        "date",
        nargs="?",
        default=None,
        type=lambda datestr: dateparse(datestr).date(),
        help="The date for which to display information.",
    )
    args = parser.parse_args(extra)

    print("Running food report with", args)
    if args.weeks < 1:
        print("nothing to do")
        return

    print("Getting latest data")
    mfp.to_csv()

    df_data = mfp.load_df()

    if args.date is None:
        end_date = df_data.index.max()
    else:
        end_date = dt.datetime( year=args.date.year,
                                month=args.date.month,
                                day=args.date.day )

    writer = PdfWriter()

    for looper in range(args.weeks):
        next_date = end_date - dt.timedelta(days=looper * 7)
        print('Preparing report for', next_date)
        add_page(writer, pdf_report(mfp, df_data=df_data, end_date=next_date))

    filename = check_and_rename(mfp.output_directory, "report", "pdf", unique=False)
    with open(filename, 'wb') as output:
        writer.write(output)
    print("Save:", filename)


@command(
    """Create a food html report going back (x) days, from (x) date
        default: days = 7, date = today
        e.g. html 14 2021-12-31"""
)
def html(args, *extra, **kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "days",
        nargs="?",
        default=7,
        type=int,
        help="The number of days to go back.",
    )
    parser.add_argument(
        "date",
        nargs="?",
        default=None,
        type=lambda datestr: dateparse(datestr).date(),
        help="The date for which to display information.",
    )
    args = parser.parse_args(extra)

    print("Running html report with", args)
    if args.days < 1:
        print("nothing to do")
        return

    print("Getting latest data")
    mfp.to_csv()

    df_data = mfp.load_df()

    if args.date is None:
        end_date = df_data.index.max()
    else:
        end_date = dt.datetime( year=args.date.year,
                                month=args.date.month,
                                day=args.date.day )
    start_date = end_date - dt.timedelta(days=args.days)

    xml_string = html_report(mfp, df_data=df_data, start_date=start_date, end_date=end_date)
    filename = check_and_rename(mfp.output_directory, "report", "html", unique=False)

    with open(filename, 'w', encoding=locale.getpreferredencoding()) as output:
        output.write(xml_string)
    print("Save:", filename)

@command(
    """Extract MyFitnessPal data since (x) date into csv
       default: (last date from existing .csv, use (x) date for new files)
       e.g. csv 2021-12-31"""
)
def csv(args, *extra, **kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "date",
        nargs="?",
        default=None,
        type=lambda datestr: dateparse(datestr).date(),
        help="The date for which to display information.",
    )
    args = parser.parse_args(extra)

    print("Running export to csv using", args)

    # if args.date is None:
    #     start_date = None
    # else:
    #     start_date = dt.datetime( year=args.date.year,
    #                             month=args.date.month,
    #                             day=args.date.day )

    if len(mfp.mfp_csv_file) < 1:
        raise ValueError("mfp_csv_file not specified")
    if Path(mfp.mfp_csv_file).is_file():
        mfp.to_csv(start_date=None)
    else:
        if args.date is None:
            print("Specify a date to create csv and extract history")
            return
        mfp.to_csv(start_date=args.date)

# @command(
#     "Format data for a given date.",
# )
# def week(args, *extra, **kwargs):
#     parser = argparse.ArgumentParser()
#     parser.add_argument(
#         "date",
#         nargs="?",
#         default=None,
#         type=lambda datestr: dateparse(datestr).date(),
#         help="The date for which to display information.",
#     )
#     args = parser.parse_args(extra)

#     print(__name__, args)
#     writer = PdfWriter()

#     # df_data = mfp.load_df()
#     # df_mfp = mfp.pivot_df(df_data)
#     # df_body = mfp.load_weight_df()

#     # if args.date is None:
#     #     end_date = df_data.index.max()
#     # else:
#     #     end_date = dt.datetime(
#     #         year=args.date.year,
#     #         month=args.date.month,
#     #         day=args.date.day,
#     #     )
#     # if mgp.birthday is None:
#     #     end_date = dt.datetime(
#     #         year=args.date.year,
#     #         month=args.date.month,
#     #         day=args.date.day,
#     #     )

#     # else:
#     # start_date = mfp.birthday

#     add_page(writer, weight_graph(mfp, df_body))
#     add_page(writer, calorie_graph(mfp, df_mfp, df_body))

#     end_date = None
#     if end_date is None:
#         end_date = df_data.index.max()
#     else:
#         end_date = dt.datetime(
#             year=end_date.year,
#             month=end_date.month,
#             day=end_date.day,
#         )

#     weeks = 6
#     for looper in range(weeks):
#         next_date = end_date - dt.timedelta(days=looper * 7)
#         print('creating report for ', next_date)
#         add_page(writer, weekly_report(cnf, df_data, end_date=next_date))

#     add_page(writer, year_review(cnf, df_mfp))

#     with open(cnf.combined_output_pdf_file, 'wb') as output:
#         writer.write(output)
#     # day = client.get_date(args.date)

#     # date_str = args.date.strftime("%Y-%m-%d")
#     # print(f"[blue]{date_str}[/blue]")
#     # for meal in day.meals:
#     #     print(f"[bold]{meal.name.title()}[/bold]")
#     #     for entry in meal.entries:
#     #         print(f"* {entry.name}")
#     #         print(
#     #             f"  [italic bright_black]{entry.nutrition_information}"
#     #             f"[/italic bright_black]"
#     #         )
#     #     print("")

#     # print("[bold]Totals[/bold]")
#     # for key, value in day.totals.items():
#     #     print(
#     #         "{key}: {value}".format(
#     #             key=key.title(),
#     #             value=value,
#     #         )
#     #     )
#     # print(f"Water: {day.water}")
#     # if day.notes:
#     #     print(f"[italic]{day.notes}[/italic]")
