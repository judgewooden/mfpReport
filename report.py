""" Generate an xml structured report from myfitnesspal data """
# pylint: disable=expression-not-assigned
# pylint: disable=line-too-long
# pylint: disable=invalid-name

import os
from io import BytesIO

import datetime as dt
import re

from xml.dom.minidom import getDOMImplementation, Document, parseString
# import xml.etree.ElementTree as ET
from pandas import DataFrame
import pdfkit

from mfp import MFPReport

def get_dom() -> Document:
    """ configure dom """
    impl = getDOMImplementation()
    document_type = impl.createDocumentType(
        "html",
        "-//W3C//DTD XHTML 1.0 Strict//EN",
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd",
    )
    return impl.createDocument("http://www.w3.org/1999/xhtml", "html", document_type)

def daterange(start_date, end_date):
    """ return a list od dates in range """
    for day in range(int((end_date - start_date).days) + 1):
        yield start_date + dt.timedelta(day)

def unique_list(ilist):
    """ remove duplicates in a list """
    ulist = []
    [ulist.append(x) for x in ilist if x not in ulist]
    return ulist

def clean_word(description: str, mfp: MFPReport) -> str:
    """ clean words based in some rules, that i someday will document """

    if isinstance(description, str):
        description = description.lower()

        # replace parts before other processing
        for find_expression, replace_string in mfp.replace_parts_before.items():
            description = re.sub(find_expression, replace_string, description)

        # merge all spaces
        description = re.sub(r' +', ' ', description)

        # return if part is found
        for find_string, new_description in mfp.return_on.items():
            if find_string in description:
                return new_description

        # remove diplicate words
        description = ' '.join(unique_list(description.split()))

        # remove parts
        for part in mfp.remove_parts:
            description = re.sub(part, ' ', description)

        # merge all spaces
        description = re.sub(r' +', ' ', description)

        # remove unwated words
        querywords = description.split()
        resultwords  = [word for word in querywords if word.lower() not in mfp.remove_words]
        description = ' '.join(resultwords)

        # replace parts after processing
        for find_expression, replace_string in mfp.replace_parts_after.items():
            description = re.sub(find_expression, replace_string, description)

        # remove diplicate words
        description = ' '.join(unique_list(description.split()))

    return description

def html_report(mfp: MFPReport, df_data: DataFrame, start_date, end_date) -> BytesIO:
    """ Generate a pretty HTML report """

    dom = df_to_xml(mfp, df_data, start_date, end_date)

    if mfp.debug:
        # root = ET.fromstring(dom.toxml())
        xml_string = parseString(dom.toxml()).toprettyxml()
        xml_string = os.linesep.join([s for s in xml_string.splitlines() if s.strip()]) # remove the weird newline issue
        return xml_string
    return dom.toxml()

def pdf_report(mfp: MFPReport, df_data: DataFrame, end_date) -> BytesIO:
    """ Generate a PDF report """

    start_date = end_date - dt.timedelta(days=6)
    dom = df_to_xml(mfp, df_data, start_date, end_date)
    if mfp.tooltip:
        for tip in dom.getElementsByTagName('tip'):
            tip.parentNode.removeChild(tip)
    buf = pdfkit.from_string( dom.toxml(), b'',
                              css=mfp.report_css_file,
                              options=mfp.report_pdf_options )
    return BytesIO(buf)

def df_to_xml(mfp: MFPReport, df_data: DataFrame, start_date, end_date) -> Document:
    """ make xml report from dataframe """

    df_xml = df_data[~((df_data.index < start_date) | (df_data.index > end_date))].copy()

    df_xml['entry'] = df_xml['description'].apply(clean_word, mfp=mfp)
    max_rows_per_meal = df_xml.groupby(['date', 'type'])['entry'].count().groupby(level=1).max()

    # show all meals from the csv data even if missing in the configuration
    meals_list = [x for x in df_xml.type.unique().tolist() if not x.startswith('total-')]
    all_meals_list = list(mfp.meals.keys())
    all_meals_list.extend(x for x in meals_list if x not in all_meals_list)

    # show all the totals unless a configuration is found then only show those totals
    if mfp.totals:
        totals_list = []
        for key in list(mfp.totals.keys()):
            value = mfp.totals[key]
            if isinstance(value, dict):
                if value.get('show', False):
                    totals_list.append(key)
    else:
        totals_list = [x for x in df_xml.type.unique().tolist() if x.startswith('total-')]


    dom = get_dom()
    html = dom.documentElement
    head = html.appendChild(dom.createElement("head"))
    if len(mfp.report_css_file) > 0:
        css = dom.createElement("link")
        css.setAttribute('rel', 'stylesheet')
        css.setAttribute('href', str(mfp.report_css_file))
        head.appendChild(css)

    body = html.appendChild(dom.createElement("body"))
    table = dom.createElement("table")
    table.setAttribute('class', 'tg')
    body.appendChild(table)
    thead = table.appendChild(dom.createElement("thead"))
    table.appendChild(thead)

    tr = dom.createElement("tr")
    thead.appendChild(tr)
    th = dom.createElement("th")
    tr.appendChild(th)
    for date in daterange(start_date, end_date):
        th = dom.createElement("th")
        th.setAttribute('colspan', '2')
        th.setAttribute('class', 'header')
        th.appendChild(dom.createTextNode(date.strftime("%A %-d %b")))
        tr.appendChild(th)

    tbody = table.appendChild(dom.createElement("tbody"))
    table.appendChild(tbody)

    for meal in all_meals_list:
        meal_name = meal
        meal_class = ''

        if meal in mfp.meals.keys():
            value = mfp.meals[meal]
            if isinstance(value, dict):
                if not value.get('show', True):
                    continue
                meal_name = value.get('name', meal_name)
                meal_class = value.get('class', meal_class)
        if len(meal_class) > 0:
            meal_class += ' '

        tr = dom.createElement("tr")
        td = dom.createElement("td")

        if meal in max_rows_per_meal.keys():
            meals_rows = max_rows_per_meal[meal]
            td.setAttribute('rowspan', str(meals_rows))
        else:
            meals_rows = 1
            td.setAttribute('rowspan', str(1))

        td.setAttribute('class', 'meal')
        td.appendChild(dom.createTextNode(meal_name))
        tr.appendChild(td)

        for row in range(0, meals_rows):

            for date in daterange(start_date, end_date):
                df_target = df_xml[(df_xml.index == date) & (df_xml.type == meal)]
                answer = df_target[['entry',
                                    'calories',
                                    'description',
                                    'details']].itertuples(index=False, name=None)
                list_answer = list(answer)

                if row >= len(list_answer):
                    entry = calorie = description = details = ""
                else:
                    entry, calorie, description, details = list_answer[row]

                td = dom.createElement("td")
                td.setAttribute('class', meal_class + meal + ' entry description')
                td.appendChild(dom.createTextNode(str(entry)))
                if mfp.tooltip and len(description) > 0:
                    tip = dom.createElement("tip")
                    tip.appendChild(dom.createTextNode(str(description)))
                    td.appendChild(tip)
                tr.appendChild(td)

                td = dom.createElement("td")
                td.setAttribute('class', meal_class + meal + ' entry calorie')
                td.appendChild(dom.createTextNode(str(calorie)))
                if mfp.tooltip and len(details) > 0:
                    tip = dom.createElement("tip")
                    details = details.replace("'", '')
                    details = re.sub(r'[{}]', ' ', details)
                    for nutrition in details.split(","):
                        tip.appendChild(dom.createTextNode(f"{nutrition}"))
                        tip.appendChild(dom.createElement("br"))
                    td.appendChild(tip)
                tr.appendChild(td)

            tbody.appendChild(tr)
            tr = dom.createElement("tr")

        tr = dom.createElement("tr")
        td = dom.createElement("td")
        td.setAttribute('class', 'meal')
        tr.appendChild(td)

        for date in daterange(start_date, end_date):
            key = "total-" + meal
            result = df_xml[(df_xml.index == date) & (df_xml.type == key)]
            if len(result) == 0:
                tot = 0
            else:
                tot = result['calories'].values[0]

            td = dom.createElement("td")
            td.setAttribute('class', meal_class + meal + ' total description')
            tr.appendChild(td)

            td = dom.createElement("td")
            td.setAttribute('class', meal_class + meal + ' total calorie')
            td.appendChild(dom.createTextNode(str(tot)))
            tr.appendChild(td)

        tbody.appendChild(tr)
        tr = dom.createElement("tr")

    tr = dom.createElement("tr")
    td = dom.createElement("td")

    if len(totals_list) > 0:
        td.setAttribute('rowspan', str(len(totals_list)))
        td.setAttribute('class', 'meal')
        tr.appendChild(td)

        for key in totals_list:
            total_name = key
            total_class = 'black'
            if key in list(mfp.totals.keys()):
                value = mfp.totals[key]
                if isinstance(value, dict):
                    total_name = value.get('name', total_name)
                    total_class = value.get('class', total_class)
            if len(total_class) > 0:
                total_class += ' '

            for date in daterange(start_date, end_date):
                result = df_xml[(df_xml.index == date) & (df_xml.type == key)]
                if len(result) == 0:
                    total_value = 0
                else:
                    total_value = result['calories'].values[0]

                td = dom.createElement("td")
                td.setAttribute('class', total_class + key + ' result description')
                td.appendChild(dom.createTextNode(str(total_name)))
                tr.appendChild(td)

                td = dom.createElement("td")
                td.setAttribute('class', total_class + key + ' result calorie')
                td.appendChild(dom.createTextNode(str(total_value)))
                tr.appendChild(td)

            tbody.appendChild(tr)
            tr = dom.createElement("tr")

    return dom
