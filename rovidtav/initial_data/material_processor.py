# -*- coding: utf-8 -*-

import re
import sys
import xlrd
import json
import codecs


def _clean(text):
    cleaned = re.sub('\s+', ' ', text)
    cleaned = cleaned.replace(' ,', ',').strip()
    starts_small = re.search('^[a-z]', cleaned)
    return cleaned.capitalize() if starts_small else cleaned


if __name__ == '__main__':

    # =====================================================================
    # It runs through the first sheet in the excel workbook.
    # Everything that does not have an sn and has a name is considered
    # a category. If there's an empty row, that'll reset the categories.
    # Two or more categories under each other will be nested
    # =====================================================================

    if len(sys.argv) != 2:
        print u'A fájlnevet paraméterben meg kell adni'
        sys.exit(1)

    workbook = xlrd.open_workbook(sys.argv[1])
    worksheet = workbook.sheet_by_index(0)
    data = []
    sns = set()
    cat = []
    new_cat = []
    for row in xrange(5, worksheet.nrows-5):

        sn = worksheet.cell_value(row, 1)
        name = _clean(worksheet.cell_value(row, 3))

        # Filter groups
        if not sn:
            if worksheet.cell_value(row, 0):
                continue

            if not name:
                cat = []
                new_cat = []
                continue

            new_cat.append(name)
            continue

        if new_cat:
            if len(new_cat) < len(cat):
                offset = len(cat) - len(new_cat)
                for i in range(len(new_cat)):
                    cat[offset+i] = new_cat[i]

            elif len(new_cat) >= len(cat):
                cat = new_cat
                new_cat = []

            new_cat = []
            print ' | '.join(cat)

        group_map = {
            1: 'MT',
            3: 'R',
        }

        item = {}
        item['sn'] = int(sn)
        item['name'] = name
        item['unit'] = worksheet.cell_value(row, 4).lower()
        item['price'] = worksheet.cell_value(row, 6) or 0
        item['category'] = ' | '.join(cat)

        group = group_map.get(worksheet.cell_value(row, 9))
        item['comes_from'] = group

        if not item['category']:
            print u'!!! KATEGORIA NELKULI ELEM: ' + unicode(name)
            continue

        if sn not in sns:
            sns.add(sn)
            data.append(item)
        else:
            print u'!!! DUPLIKALT SN: ' + unicode(item)

    with codecs.open('anyag.json', 'w', 'utf-8') as f:
        f.write(json.dumps(data))
