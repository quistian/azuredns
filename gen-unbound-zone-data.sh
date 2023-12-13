#!/bin/sh

# azurecli zones bc > bc-zones

TMP=/tmp/unbound-local-zone-data.$$

for z in "$*"
do
    echo $z
    DST=/home/ansible/systems/files/unbound/local-zone-data/$z
    test -f $DST || touch $DST
    azurecli list -t cnames $z  > $TMP
    if ! cmp -s $TMP $DST; then
        mv $TMP $DST
        cd /home/ansible/systems/files/unbound
        cat local-zone-data/* > local-zone-data.conf
    fi
done

rm -f $TMP
