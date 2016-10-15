# -*- coding: utf-8 -*-

import re
import sys
import xlrd
import json
import codecs


def _clean(text):
    cleaned = re.sub('\s+', ' ', text)
    cleaned = cleaned.replace(' ,', ',').strip('"').strip()
    starts_small = re.search('^[a-z]', cleaned)
    return cleaned.capitalize() if starts_small else cleaned


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print u'A fájlnevet paraméterben meg kell adni'
        sys.exit(1)

    workbook = xlrd.open_workbook(sys.argv[1])
    worksheet = workbook.sheet_by_index(0)
    data = []
    for row in xrange(1, worksheet.nrows):

        if worksheet.cell_value(row, 4) != 0:
            # Torolt munka
            continue

        # A fejlec igy nezzen ki:
        # mNev  mTetelSzam  mTetelAr  mDef  Torolt  csop_anyag_ar  kiadott_ar

        item = {
            'name': _clean(worksheet.cell_value(row, 0)),
            'art_number': worksheet.cell_value(row, 1),
            'remark': _clean(worksheet.cell_value(row, 3)),
            'art_price': worksheet.cell_value(row, 2),
            'bulk_price': worksheet.cell_value(row, 5),
            'given_price': worksheet.cell_value(row, 6),
        }

        data.append(item)

    with codecs.open('munka.json', 'w', 'utf-8') as f:
        f.write(json.dumps(data))
