#!/bin/sh

# azurecli zones bc > bc-zones

TMP=/tmp/unbound-local-zone-data.$$
UNBOUND_DIR=/home/ansible/systems/files/unbound
LOCAL_DATA_DIR="$UNBOUND_DIR/local-zone-data"

for z in "$*"
do
    echo $z
    DST="$LOCAL_DATA_DIR/$z"
    test -f $DST || touch $DST
    azurecli list -t cnames $z  > $DST
done

cd $LOCAL_DATA_DIR
cat *.io *.com *.net *.ms  > $UNBOUND_DIR/local-zone-data.conf

#if [ "${CHANGED_DATA+1}" ]; then
#    cat $LOCAL_DATA_DIR/* > $UNBOUND_DIR/zone-data.conf
#fi
