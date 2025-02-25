"""Code that actually runs the table generation"""

import sys
sys.dont_write_bytecode = True
import table_gen

TITLE_PL = 'EPL: The race for European Competitions   '
FILE_PL = 'PL Europe Race'
lines_pl = [
    [4, "Above __ points guarantees UCL", '#00004b'],
    [5, "Above __ points guarantees UEL", '#ff6900'],
    [18,"Above __ points for safety", '#e21a23']
]
# CONF: [6, "Above __ points guarantees CON", '#00be14'],
# can only guarantee CONF some time after League Cup Final

TITLE_ELC = 'Championship: The race for Promotion   '
FILE_ELC = 'Championship Promotion Race'
lines_elc = [
    [2, "Above __ points guarantees automatic promotion", '#52d577'],
    [6, "Above __ points guarantees playoffs", '#d6bf25'],
    [21,"Above __ points for safety", '#e21a23']
]

# table_gen.generate_table('ELC', lines_elc, TITLE_ELC, FILE_ELC, pos_one=1, pos_two=24)
table_gen.generate_table('PL', lines_pl, TITLE_PL, FILE_PL, pos_one=1, pos_two=20)
