""" manage exported myfitnesspal csv data """
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=logging-fstring-interpolation

import json
import locale
import logging

from typing import Dict

import csv
import datetime as dt
import pandas as pd
from pandas import DataFrame

import myfitnesspal

logger = logging.getLogger(__name__)


class MFPReport:
    """ One place for variables """

    def __init__(self):
        """ Hard coded values """

        self.debug = True
        self.locale = "en_US.UTF-8"
        self.mfp_csv_file: str = "myfitnesspal_data.csv"
        self.weight_csv_file: str = "boditrax.csv"
            # contains at least two colums ['date', 'bodyweight']
            # if 'fatmass' present than fat_percentage will be calculated
            # 'bodyweight' in kg
        self.alcohol: str = 'party'
            # track all your alcohol consuption into a seperate meal
            # by specifying that meal here, the reports can filter it out
        self.birthday: str = "1970-01-01"    # YYYY-MM-DD
        self.height: int = 175               # in cm
        self.gender: str = "male"            # 'male' else 'female'
        self.dieet_start: str = "2021-01-01" # YYYY-MM-DD
        self.formula: str = 'bmr_katch_mcardle'
            # valid options : 'bmr_harris_benedict'
            #                 'bmr_mifflin_st_jeor'
            #                 'bmr_katch_mcardle'
        self.multiplier: float = 1.2
            # if using a smartwatch to track activity use 1.2 (sedentary)
            # else use multiplier from https://tdeecalculator.net/

        self.slip_up: int = -200
        self.output_directory: str = "output"
        self.landscape_width: float = 11          # in inches
        self.landscape_height: float = 8.5          # in inches
        self.report_pdf_options: dict = {
            'page-size': 'Letter',
            'orientation': 'landscape',
            'encoding': "UTF-8",
            'dpi': '80',
            'custom-header': [
                ('Accept-Encodinglocale', 'gzip')
            ],
            'enable-local-file-access': True
        }

        # graph.py change the headers and other stuff
        self.rename: dict = {}
        # incl this method: https://www.parool.nl/nieuws/want-to-lose-weight-show-your-hypothalamus-who-s-in-charge~be666c71/
        self.hamster: bool = False

        # graph.py used for the heatmaps
        self.daylabels: list = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        self.monthlabels: list = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                                  'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

        # graph.py customize the calorie chart
        self.scatter: dict = {
            # 'snacks': {                      # scatter
            #    'name': 'in between meals',   # show this in legend
            #    'color': 'red',               # Add color for styling
            #    'max': 500,                   # only plot if larger than max
            #    'show': False                 # supress/show this in output
            # },
            'snacks': {
                'name': 'snacks',
                'color': 'red',
                'max': 50,
                'show': True
            },
            'adjusted': {
                'name': 'smartwatch',
                'color': 'black',
                'max': 5,
                'show': False
            },
            'fitness': {
                'name': 'sport',
                'color': 'green',
                'max': 10,
                'show': True
            }
        }

        # used by report.py for scrubbing the mfp desciption and make it nice
        self.report_css_file: str = "report.css"
        self.tooltip: bool = True             # For HTML output only
        self.replace_parts_before: dict = {}
        self.return_on: dict = {}
        self.remove_parts: list = []
        self.remove_words: list = []
        self.replace_parts_after: dict = {}
        self.meals: dict = {}
            # list of meals to print
            # 'lunch' : {
            #   'name' : 'afternoon meal',     # pritn this as name in output
            #   'show' : False,                # supress/show this in output
            #   'class' : "css-class",         # Add this class for styling
            # }
        self.totals: dict = {}
            # list of totals to show (show all if empty)
            # 'total-calories': {               # match this total from csv input
            #    'name': 'calories intake',     # print this as name in output
            #    'class': 'red',                # Add this class for styling
            #    'show': True                   # supress/show this in output
            #  }


    def tr(self, sentence):
        """ rename sentence to config value """
        if sentence in self.rename:
            return self.rename[sentence]
        return sentence

    def read_config(self, configfile: str):
        """ Load configuration from a file """
        with open(configfile, encoding='utf-8') as file:
            for key, value in json.loads(file.read()).items():
                setattr(self, key, value)

    def save_config(self, filename: str):
        """ Save configuration from a file """
        conf_items = {k: v for k, v in vars(self).items() if isinstance(v, (int, float, str, list, dict))}
        with open(filename, "w", encoding='utf-8') as file:
            json.dump(conf_items, file, sort_keys=False, indent=2)
        print(f"config saved to: {filename}")

    def load_weight_df(self) -> DataFrame:
        """ load csv weight into DataFrame """
        df_body = pd.read_csv(self.weight_csv_file)
        df_body['date'] = pd.to_datetime(df_body['date'])
        df_body.date = df_body.date.apply(lambda x: dt.datetime(x.year, x.month, x.day))
        df_body.set_index('date', inplace=True)
        df_body.dropna(axis=1, inplace=True)
        if 'fatmass' in df_body:
            df_body['fat_percentage'] = df_body['fatmass'] / df_body['bodyweight']
        else:
            logger.warning("'fatmass' not in dataset, 'fat_percentage' can not be calculated.")
        return df_body

    def load_df(self) -> DataFrame:
        """ load csv into dataframe """
        df_data = pd.read_csv(self.mfp_csv_file)
        df_data['date'] = pd.to_datetime(df_data['date'])
        df_data.set_index('date', inplace=True)
        return df_data

    def pivot_df(self, df_data: DataFrame) -> DataFrame:
        """ load pivot totals into dataframe """
        df_mfp = df_data[df_data.type.str.startswith('total-')].copy()
        df_mfp.rename({'calories': 'value'}, axis=1, inplace=True)
        df_mfp.rename({'type': 'category'}, axis=1, inplace=True)
        df_mfp.drop(['details', 'description'], axis=1, inplace=True)
        df_mfp['category'] = df_mfp['category'].str.replace("total-", "")
        df_mfp = df_mfp.pivot(columns='category', values='value' )
        # TODO make sure this is what you want to do
        df_mfp.fillna(0)
        return df_mfp

    def to_csv(self, start_date=None) -> None:
        """ extract from myfitnesspal to csv """

        try:
            with open(self.mfp_csv_file, 'r', encoding=locale.getpreferredencoding()) as file:
                last_line = file.readlines()[-1].split(",")[0]
                start_date = dt.datetime.strptime(last_line, '%Y-%m-%d').date()
                start_date += dt.timedelta(days=1)
            file = open(self.mfp_csv_file, 'a', newline='', encoding=locale.getpreferredencoding())
            writer = csv.writer(file)
        except FileNotFoundError:
            file = open(self.mfp_csv_file, 'w', newline='', encoding=locale.getpreferredencoding())
            writer = csv.writer(file)
            row = ["date", "type", "description", "calories", "details"]
            writer.writerow(row)
        except ValueError:
            print("WARNING: Last  of existing CSV file does not contain a valid date")
            file = open(self.mfp_csv_file, 'a', newline='', encoding=locale.getpreferredencoding())
            writer = csv.writer(file)

        days = int((dt.date.today() - start_date).days)
        if days == 0:
            return

        warn = True
        client = myfitnesspal.Client()

        for looper in range( days ):
            date = start_date + dt.timedelta(looper)
            print(f"Request: {date}")
            day = client.get_date(date)

            totals: Dict[str, float] = {}
            for meal in day.meals:
                name = meal.name.title().lower()
                total = 0
                for entry in meal.get_as_list():
                    calories = entry['nutrition_information']['calories']
                    row = [ date,
                            name,
                            entry['name'],
                            int(calories),
                            entry['nutrition_information'] ]
                    writer.writerow(row)
                    total += calories

                totals[name] = total

            total_adjusted = 0
            total_fitness = 0
            for exercise in day.exercises:
                name = exercise.name.title().lower()
                if name == "cardiovascular":
                    for entry in exercise.get_as_list():
                        calories = entry['nutrition_information']['calories burned'] * -1
                        row = [ date,
                                "exercise",
                                entry['name'],
                                int(calories),
                                entry['nutrition_information'] ]
                        writer.writerow(row)

                        if "adjustment" in entry['name'].lower():
                            total_adjusted += calories
                        else:
                            total_fitness += calories
            totals['fitness'] = total_fitness
            totals['adjusted'] = total_adjusted
            totals['exercise'] = total_fitness + total_adjusted

            for key, value in day.totals.items():
                totals[key] = value

            if 'calories' not in totals:
                totals['calories'] = 0
            totals['goal'] = day.goals['calories']
            totals['netcalories'] = totals['calories'] + totals['exercise']
            totals['bmr'] = totals['goal'] - totals['calories']

            if self.alcohol in totals:
                totals['food_only'] = totals['calories'] - totals[self.alcohol]
            elif warn:
                logger.warning(f"'{self.alcohol}' is not in the dataset. Is 'alcohol' set correctly?")
                warn = False

            for key, value in totals.items():
                row = [ date, 'total-' + key, None, int(value) ]
                writer.writerow(row)

        file.close()
