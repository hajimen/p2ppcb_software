import sys
import os
import pathlib

import adsk.fusion as af

CURRENT_DIR = pathlib.Path(os.path.dirname(__file__)).parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

from reimport import reimport

reimport(['f360_common'])

from f360_common import catch_exception, get_context


@catch_exception
def run(context):
    con = get_context()

    def _rec(occ: af.Occurrence):
        for b in occ.component.bRepBodies:
            b = b.createForAssemblyContext(occ)
            b.copyToComponent(con.comp)
        for o in occ.component.occurrences:
            _rec(o.createForAssemblyContext(occ))

    for o in con.comp.occurrences:
        _rec(o)

    for o in list(con.comp.occurrences):
        o.deleteMe()
