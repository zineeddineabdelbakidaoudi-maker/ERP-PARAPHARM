import sys
from ui.main_window import MENU_ITEMS

all_modules = []
for cat, items in MENU_ITEMS.items():
    for key, icon, label in items:
        all_modules.append(f'    ("{key.upper()}", "{label}"),')

with open('modules.txt', 'w', encoding='utf-8') as f:
    f.write('ALL_MODULES = [\n')
    f.write('\n'.join(all_modules))
    f.write('\n]\n')
