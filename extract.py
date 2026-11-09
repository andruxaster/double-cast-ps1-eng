#!/usr/bin/env python3
"""Извлекает все реплики YaruDora: Double Cast (PS1) из ваших образов в таблицу для перевода.
   python3 extract.py CD1.bin CD2.bin script_ru.xlsx"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
from common import load_scripts, iter_lines, classify
from ui_ru import NAMES, SYSTEM
from demo_ru import DEMO

def main(cd1, cd2, out):
    rows = {}; order = []; speaker = ''
    for disc, path in ((1, cd1), (2, cd2)):
        sc = load_scripts(path)
        for f, off, t in iter_lines(sc):
            kind, body, pre, suf = classify(t)
            if kind == 'skip': continue
            if kind == 'name': speaker = body; continue
            if f.endswith(('MAIN.SSC', 'STARTUP.SSC')) or body.strip('　 ') in SYSTEM: continue
            if t not in rows:
                rows[t] = dict(scene='CD%d %s' % (disc, f.split('/')[-1]), kind=kind,
                               speaker=speaker if kind == 'реплика' else '', jp=t, body=body, n=0)
                order.append(t)
            rows[t]['n'] += 1
    wb = Workbook(); ws = wb.active; ws.title = 'Реплики'
    hdr = ['id', 'сцена', 'тип', 'говорит (прибл.)', 'японский (НЕ МЕНЯТЬ)', 'русский', 'повторов', 'примечание']
    ws.append(hdr)
    for i, t in enumerate(order, 1):
        r = rows[t]
        ru = DEMO.get(r['body'], '')
        ws.append([i, r['scene'], r['kind'], NAMES.get(r['speaker'], r['speaker']), r['jp'], ru, r['n'],
                   'демо' if ru else ''])
    for c in ws[1]: c.font = Font(bold=True); c.fill = PatternFill('solid', fgColor='DDEBF7')
    for col, w in zip('ABCDEFGH', (7, 16, 13, 18, 60, 60, 9, 12)): ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2):
        row[4].alignment = row[5].alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'F2'
    ws2 = wb.create_sheet('Имена')
    ws2.append(['японский (НЕ МЕНЯТЬ)', 'русский'])
    for k, v in NAMES.items(): ws2.append([k, v])
    ws2.column_dimensions['A'].width = 28; ws2.column_dimensions['B'].width = 28
    for c in ws2[1]: c.font = Font(bold=True)
    wb.save(out)
    print('строк:', len(order), '->', out)

if __name__ == '__main__':
    main(*sys.argv[1:4])
