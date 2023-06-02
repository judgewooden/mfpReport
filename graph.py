""" plot graphs based on mfp extracted data """
# pylint: disable=logging-fstring-interpolation
# pylint: disable=line-too-long

from io import BytesIO

import logging
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib as mpl
import calplot

import pandas as pd
import numpy as np

from pandas import DataFrame
from dateutil.parser import parse as dateparse
from dateutil.relativedelta import relativedelta

from mfp import MFPReport

logger = logging.getLogger(__name__)


def year_stats_heatmap(mfp: MFPReport, df_mfp: DataFrame, year: int) -> BytesIO:
    """ plot heatmap of categories from mfp """

    df_mfp = df_mfp[((df_mfp.index.year == year))].copy()

    figure, axis = plt.subplots(4, 1, figsize=(mfp.landscape_width, mfp.landscape_height))
    figure.suptitle(f"{mfp.tr('annual review')} {year} {mfp.tr('goals')}")

    if mfp.alcohol in df_mfp:
        calplot.yearplot(data = df_mfp[mfp.alcohol],
                        cmap = 'Blues',
                        year=year,
                        dayticks=True,
                        dropzero=True,
                        daylabels=mfp.daylabels,
                        monthlabels=mfp.monthlabels,
                        ax=axis[0]
                        )
        axis[0].set_title(mfp.tr('alcohol use'))
    else:
        logger.warning(f"{mfp.alcohol} not in dataset (is alcohol set correctly?).")

    if 'food_only' in df_mfp:
        calplot.yearplot(data =  df_mfp['food_only'],
                        cmap = 'YlOrRd',
                        year=year,
                        dayticks=True,
                        dropzero=True,
                        daylabels=mfp.daylabels,
                        monthlabels=mfp.monthlabels,
                        ax=axis[1]
                        )
        axis[1].set_title(mfp.tr('food'))
    else:
        logger.warning("'food_only' not in dataset (is alcohol set correctly?).")

    calplot.yearplot(data = df_mfp['exercise'] * -1,
                     cmap = 'Greens',
                     year=year,
                     dayticks=True,
                     dropzero=True,
                     daylabels=mfp.daylabels,
                     monthlabels=mfp.monthlabels,
                     ax=axis[2]
                    )
    axis[2].set_title(mfp.tr('exercise'))

    def calc_bmr(row):
        if row["calories"] == 0:
            return 0
        else:
            return row['bmr']
    df_mfp['bmr_calc'] = df_mfp.apply(calc_bmr, axis=1)
    calplot.yearplot(data = df_mfp['bmr_calc'],
                     cmap = 'RdYlBu',
                     year=year,
                     dayticks=True,
                     dropzero=True,
                     daylabels=mfp.daylabels,
                     monthlabels=mfp.monthlabels,
                     ax=axis[3]
                    )
    axis[3].set_title(mfp.tr('under/over daily calorie goal'))

    buf = BytesIO()
    figure.savefig(buf, format='pdf', bbox_inches='tight')
    return buf

def year_nutrients_heatmap(mfp: MFPReport, df_mfp: DataFrame, year: int) -> BytesIO:
    """ plot heatmap of food groups from mfp """

    df_mfp = df_mfp[((df_mfp.index.year == year))].copy()

    figure, axis = plt.subplots(4,1, figsize=(mfp.landscape_width,mfp.landscape_height))
    figure.suptitle(f"{mfp.tr('annual review')} {year} {mfp.tr('nutrients')}")

    calplot.yearplot(data = df_mfp['carbohydrates'],
                     cmap = 'bwr',
                    #  cmap = 'Wistia',
                     year=year,
                     dayticks=True,
                     dropzero=True,
                     daylabels=mfp.daylabels,
                     monthlabels=mfp.monthlabels,
                     ax=axis[0]
                    )
    axis[0].set_title(f"{mfp.tr('carbohydrates')} {mfp.tr('average')}={df_mfp['carbohydrates'].mean():.0f}g {mfp.tr('(blue/white/red)')}")

    calplot.yearplot(data = df_mfp['protein'],
                     cmap = 'bwr',
                    #  cmap = 'cool',
                     year=year,
                     dayticks=True,
                     dropzero=True,
                     daylabels=mfp.daylabels,
                     monthlabels=mfp.monthlabels,
                     ax=axis[1]
                    )
    axis[1].set_title(f"{mfp.tr('protein')} {mfp.tr('average')}={df_mfp['protein'].mean():.0f}g {mfp.tr('(blue/white/red)')}")

    calplot.yearplot(data = df_mfp['fat'],
                     cmap = 'bwr',
                    #  cmap = 'Reds',
                     year=year,
                     dayticks=True,
                     dropzero=True,
                     daylabels=mfp.daylabels,
                     monthlabels=mfp.monthlabels,
                     ax=axis[2]
                    )
    axis[2].set_title(f"{mfp.tr('fats')} {mfp.tr('average')}={df_mfp['fat'].mean():.0f}g {mfp.tr('(blue/white/red)')}")

    calplot.yearplot(data =  df_mfp['sugar'],
                     cmap = 'bwr',
                    #  cmap = 'PuRd',
                     year=year,
                     dayticks=True,
                     dropzero=True,
                     daylabels=mfp.daylabels,
                     monthlabels=mfp.monthlabels,
                     ax=axis[3]
                    )
    axis[3].set_title(f"{mfp.tr('sugar')} {mfp.tr('average')}={df_mfp['sugar'].mean():.0f}g {mfp.tr('(blue/white/red)')}")

    buf = BytesIO()
    figure.savefig(buf, format='pdf', bbox_inches='tight')
    return buf

def weight_graph(mfp: MFPReport, df_body: DataFrame, start_date, end_date) -> BytesIO:
    """ generate a pdf chart of weight versus maximum trends """

    if mfp.dieet_start is None:
        plan_date = start_date
    else:
        plan_date = dateparse(mfp.dieet_start).date()
        plan_date = dt.datetime( year=plan_date.year,
                                 month=plan_date.month,
                                 day=plan_date.day )

    df_hamster = df_body[['bodyweight']].loc[(df_body.index >= plan_date)].head(1).copy()
    if len(df_hamster) != 1:
        raise Exception("The date the dieet started requires a weigh measure in the weight file")
    df_hamster.rename({'bodyweight': 'hamster'}, axis=1, inplace=True)

    start_weight = df_hamster['hamster'].iloc[0]
    months_since = ((end_date.year - plan_date.year) * 12) + ((end_date.month - plan_date.month) + 1)
    future_date = plan_date + relativedelta(months=months_since)
    df_hamster.loc[future_date] = {'hamster':start_weight - months_since}

    df_calc = pd.concat([df_hamster, df_body], axis=1)
    # df_calc = df_calc[~(df_calc.index < start_date)]
    df_calc['hamster'] = df_calc['hamster'].interpolate(method ='time', limit_direction ='forward')
    df_calc.index = pd.DatetimeIndex(df_calc.index)
    idx = pd.date_range(df_calc.index[0].value, df_calc.index[-1].value)
    df_calc = df_calc.reindex(idx)

    legend_list = []
    figure, axis = plt.subplots(figsize=(mfp.landscape_width,mfp.landscape_height))
    axis.yaxis.tick_right()
    axis.yaxis.set_label_position("right")

    xline = np.linspace( df_calc.index[1].value, df_calc.index[-1].value, len( df_calc.index) * 100)
    tline = pd.to_datetime(xline)

    df_calc['hamster'] = df_calc['hamster'].interpolate(method ='time',
                                               limit_direction ='forward')
    legend_list.append(mfp.tr('assessment line healthy weight loss'))
    hamster_onder = np.interp(tline, df_calc.index,  df_calc['hamster'] )
    axis.plot(tline, hamster_onder, color='green', linewidth=1.5)

    legend_list.append(mfp.tr('assessment line deterioration'))
    hamster_top = np.interp(tline, df_calc.index,  df_calc['hamster'] + 2)
    axis.plot(tline, hamster_top, color='orange', linewidth=0.5)

    df_calc['weight_time'] = df_calc['bodyweight'].interpolate(method ='time',
                                                  limit_direction ='backward')
    df_calc.dropna(axis=0, inplace=True, subset=['weight_time'])

    xline = np.linspace( df_calc.index[1].value, df_calc.index[-1].value, len( df_calc.index) * 100)
    tline = pd.to_datetime(xline)

    # legend_list.append('weight_time')
    # weight_time = np.interp(t, df_calc.index,  df_calc['weight_time'])
    # axis.plot(t, weight_time)

    legend_list.append(mfp.tr('body weight'))
    df_calc['weight_poly'] = df_calc['bodyweight'].interpolate(method='akima', order=5)
    # df_calc['weight_poly'] = df_calc['weight'].interpolate(method='linear', order=5)
    weight_poly = np.interp(tline, df_calc.index,  df_calc['weight_poly'])
    axis.plot(tline, weight_poly, color='steelblue', linewidth=2)

    legend_list.append(mfp.tr('measurement'))
    axis.plot(df_calc.index, df_calc['bodyweight'], 'o', markersize=5, color='steelblue', mfc='white')

    axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    plt.title(mfp.tr('weight progression chart'))

    legend_list.append(mfp.tr('lose weight too fast'))
    hamster_onder = np.interp(tline, df_calc.index,  df_calc['hamster'] )
    axis.fill_between(tline, hamster_onder, weight_poly,
                  where=weight_poly<hamster_onder, facecolor='lightblue', alpha=1)

    legend_list.append(mfp.tr('relapse period'))
    hamster_top = np.interp(tline, df_calc.index,  df_calc['hamster'] + 2)
    axis.fill_between(tline, hamster_top, weight_poly,
                      where=weight_poly>hamster_top, facecolor='darksalmon', alpha=1)

    axis.yaxis.set_major_formatter(mpl.ticker.StrMethodFormatter("{x:.1f}")) #{x:,.0f}'))

    plt.minorticks_on()
    axis.tick_params(axis='x', which='minor', bottom=False)
    axis.grid(visible=True, axis='y', which='minor', color='black', linewidth=0.1)
    axis.grid(visible=True, axis='y', which='major', color='black', linewidth=0.4)
    axis.grid(visible=True, axis='x', which='major', color='black', linewidth=0.2)

    axis.legend(legend_list, loc='upper right', fontsize=8)
    axis.margins(x=0)

    axis.yaxis.set_tick_params(labelsize=6)
    axis.xaxis.set_tick_params(labelsize=8)

    df_calc = df_calc[~((df_calc.index < start_date) | (df_calc.index > end_date))]
    axis.set_ylim([ round( (df_calc.bodyweight.min() - 4) / 2) * 2 , round( (df_calc.bodyweight.max() + 4 ) / 2) * 2])
    axis.set_xlim([ start_date, end_date])

    axis.text(axis.get_xlim()[-1] - 2, axis.get_ylim()[0] + 0.2, df_calc.index[-1].strftime("%A, %d %b %Y"),
            ha="right", backgroundcolor='1.', fontsize=5)

    buf = BytesIO()
    figure.savefig(buf, format='pdf', bbox_inches='tight')
    return buf


def calorie_graph(mfp: MFPReport, df_mfp: DataFrame, df_body: DataFrame, start_date, end_date) -> BytesIO:
    """ generate a pdf chart of weight loss and gain """

    birthday = dateparse(mfp.birthday).date()
    birthday = dt.datetime(
        year=birthday.year,
        month=birthday.month,
        day=birthday.day,
    )
    height = float(mfp.height)

    df_calc = pd.concat([df_mfp, df_body], axis=1)
    df_calc['age'] = (df_calc.index - birthday).days/365
    df_calc['bodyweight'] = df_calc['bodyweight'].interpolate(method ='time', limit_direction ='forward')
    if mfp.gender == 'male':
        based_on = mfp.tr('male')
        df_calc['bmr_harris_benedict'] = 88.362 + (13.397*df_calc['bodyweight']) + (4.799*height) - (5.677*df_calc['age'])
        df_calc['bmr_mifflin_st_jeor'] = (10*df_calc['bodyweight']) + (6.25*height) - (5*df_calc['age']) + 5
        df_calc['bmr_katch_mcardle'] = 370 + (21.6 * ((0.407*df_calc['bodyweight']) + (0.267*height) - 19.2))
    else:
        based_on = mfp.tr('female')
        df_calc['bmr_harris_benedict'] = 447.593 + (9.247*df_calc['bodyweight']) + (3.098*height) - (4.330*df_calc['age'])
        df_calc['bmr_mifflin_st_jeor'] = (10*df_calc['bodyweight']) + (6.25*height) - (5*df_calc['age']) - 161
        df_calc['bmr_katch_mcardle'] = 370 + (21.6 * ((0.252*df_calc['bodyweight']) + (0.473*height) - 48.3))
    if 'fat_percentage' in df_calc:
        df_calc['fat_percentage'] = df_calc['fat_percentage'].interpolate(method ='time', limit_direction ='forward')
        df_calc['bmr_katch_mcardle'] = 370 + (21.6 * ( df_calc['bodyweight'] * ( 1 - df_calc['fat_percentage'] )))

    # df_calc['tdee_sedentary'] = (df_calc[mfp.formula] * mfp.multiplier) - df_calc['calories'] - df_calc['exercise']
    # df_calc['tdee_sedentary'] = (df_calc[mfp.formula] * mfp.multiplier) - df_calc['netcalories']
    def calc_tdee(row):
        if row["calories"] == 0:
            return 0
        else:
            return (row[mfp.formula] * mfp.multiplier) - row['netcalories']
    df_calc['tdee_sedentary'] = df_calc.apply(calc_tdee, axis=1)

    # df_calc['tdee_sedentary'] = df_calc.loc[df_calc['calories'] == 0]['calories']
    df_calc['tdee_sedentary_ma7'] = df_calc['tdee_sedentary'].rolling(window=7, center=True).mean()
    df_calc.dropna(inplace=True, subset=['tdee_sedentary_ma7'])
    df_calc = df_calc[~((df_calc.index < start_date) | (df_calc.index > end_date))]

    figure, axis = plt.subplots(figsize=(mfp.landscape_width,mfp.landscape_height))
    axis.yaxis.tick_right()
    axis.yaxis.set_label_position("right")

    # make the graphs
    legend_list = []
    bmr_legend = []
    bmr_legend.append(f"{mfp.tr('TDEE is')} {int(df_calc[mfp.formula][-1] * mfp.multiplier)}")
    bmr_legend.append(f"BMR Harris-Benedict, {based_on} formula: {int(df_calc['bmr_harris_benedict'][-1])}")
    bmr_legend.append(f"BMR Mifflin St Jeor, {based_on} formula: {int(df_calc['bmr_mifflin_st_jeor'][-1])}")
    if mfp.formula == 'bmr_katch_mcardle' and 'fat_percentage' in df_calc:
        based_on = mfp.tr('lean body mass')
    bmr_legend.append(f"BMR Katch–McArdle, {based_on} formula: {int(df_calc['bmr_katch_mcardle'][-1])}")
    bmr_legend.append(f"{mfp.tr('Multiplier')} x{mfp.multiplier}")
    bmr_legend.append(f"{mfp.tr('Equation used')} {mfp.formula}")

    xline = np.linspace( df_calc.index[0].value, df_calc.index[-1].value, len( df_calc.index) * 100)
    tline = pd.to_datetime(xline)
    tdee_sedentary_ma7 = np.interp(tline, df_calc.index,  df_calc['tdee_sedentary_ma7'])
    # print(df_calc['bmr'].head(20))
    bmr = np.interp(tline, df_calc.index,  df_calc['bmr'])

    # bodyweight = np.interp(t, df_gewicht.index,  df_gewicht['bodyweight'])
    legend_list.append(mfp.tr('average weekly calorie expenditure'))
    axis.plot(tline, tdee_sedentary_ma7, color='steelblue', linewidth=1)
    axis.yaxis.set_tick_params(labelsize=6)
    axis.xaxis.set_tick_params(labelsize=8)

    legend_list.append(mfp.tr('weight loss'))
    axis.fill_between(tline, tdee_sedentary_ma7, where=tdee_sedentary_ma7>0, facecolor='springgreen',alpha=0.5)
    legend_list.append(mfp.tr('weight gain'))
    axis.fill_between(tline, tdee_sedentary_ma7, where=tdee_sedentary_ma7<0, facecolor='lightsteelblue', alpha=0.5)
    if mfp.slip_up is not None:
        legend_list.append(mfp.tr('slip up'))
        axis.fill_between(tline, tdee_sedentary_ma7, bmr, where=bmr<mfp.slip_up, interpolate=True, facecolor='tomato', alpha=0.2)
    axis.margins(x=0)
    axis.grid()

    # legend_list.append('dagelijkse indicator')
    # axis.plot(t, mfp_goal_ma7, linestyle='dotted', color='black', linewidth=0.1)
    # axis.plot(t, bmr, linestyle='dotted', color='black', linewidth=0.1)

    for item in mfp.scatter:
        value = mfp.scatter[item]
        if value.get('show', True):
            # df_item = df_calc[abs(df_calc[item]) > int(value.get('max', 250))]
            df_item = df_mfp[abs(df_mfp[item]) > int(value.get('max', 250))]
            legend_list.append(value.get('name', item))
            axis.plot(df_item.index, df_item[item] * -1, 'o', markersize=1.2, color=value.get('color', 'any'))

    axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    axis.yaxis.set_major_formatter(mpl.ticker.StrMethodFormatter("{x:.0f}")) #{x:,.0f}'))
    # axis.yaxis.set_major_formatter(mpl.ticker.StrMethodFormatter("{x:0f}}")) #{x:,.0f}'))

    axis.set_ylim([-4000, 2000])
    axis.set_xlim([ start_date, end_date])

    axis.legend(legend_list, loc='upper right', fontsize=8)
    plt.title(mfp.tr('calorie balance chart'))
    axis.text(axis.get_xlim()[0] + 2, axis.get_ylim()[0] + 85,
            "\n".join(["  " + bmr for bmr in bmr_legend]),
            backgroundcolor='1.', fontsize=6)
    axis.text(axis.get_xlim()[-1] - 2, axis.get_ylim()[0] + 85,
            df_calc.index[-1].strftime('%A, %d %b %Y'),
            ha="right", backgroundcolor='1.', fontsize=5)

    buf = BytesIO()
    figure.savefig(buf, format='pdf', bbox_inches='tight')
    return buf
