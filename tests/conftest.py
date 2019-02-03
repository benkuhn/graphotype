import sys

collect_ignore = []
if sys.version_info < (3, 7):
    collect_ignore = ['py37']
