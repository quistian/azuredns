#!/bin/sh

for i in *.yaml
do
    SRC=$i
    DST="../old-merged-zones/$i"
    echo processing $SRC
    if [ -f "$DST" ]; then
        diff $SRC $DST
    else
        echo "$DST does not exist"
    fi
    echo
done
