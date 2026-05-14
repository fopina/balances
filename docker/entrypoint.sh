#!/bin/sh

# temporary until all are migrated to modules
if [ -e /${BALANCE_ENTRY}/main.py ]; then
    exec python -u /${BALANCE_ENTRY}/main.py "$@"
else
    exec python -u /${BALANCE_ENTRY} "$@"
fi