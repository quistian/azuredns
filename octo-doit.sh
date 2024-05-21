#!/bin/sh

LEAF_CHANGED_ZONES=/tmp/leaf-changed-zones.$$
CHANGED_ZONES=/tmp/azure-changed-zones.$$
TMP_CHANGED_ZONES=/tmp/tmp-changed-zones.$$

BASEDIR=/home/russ/src/Azure/az-dns
LOG="$BASEDIR/bc-current-scan.log"
LOGDIR="$BASEDIR/logs"
LAST_CHANGED=$LOGDIR/last_changed.log
SNAPSHOT=$LOGDIR/snapshot.log
LAST_RRs=$LOGDIR/last_rrs.log

TSTAMP_START=`date +"%Y-%m-%dT%H-%M-%S"`
TSTAMP=$TSTAMP_START

TMP_UNBOUND_DATA=/tmp/unbound-local-zone-data.$$
UNBOUND_DIR=/home/ansible/systems/files/unbound
UNBOUND_DATA_DIR="$UNBOUND_DIR/local-zone-data"

# process command line flags
# ARGS=$(getopt -a --options vd --long "verbose,debug" -- "$@")

optstring=":vd"
while getopts $optstring option
do
    case $option in
        d|debug) DEBUG=true ;;
        v|verbose) VERBOSE=1 ;;
        ?) echo "Invalid option: -$OPTARG Use: -d to set DEBUG or -v to set VERBOSE" >&2; exit 1 ;;
    esac
done

# Load in the appropriate environment variables for octodns modules
if [ -z "${AZURE_QA_USER_ID}"  ]; then
    echo "Azure Vars are being loaded" >> $LOG
    . $HOME/.azureexportrc
fi

if [ -z "${BAM_VIEW}" ]; then
    echo "BlueCat Vars are being loaded" >> $LOG
    . $HOME/.bamrc
fi

#if [ -z "${POWERDNS_API_KEY}" ]; then
#    echo "PowerDNS Vars are being loaded" >> $LOG
#    . $HOME/.pdnsrc
#fi

echo $TSTAMP_START > $LOG
echo "Scanning BC zones for changes" | tee -a $LOG

echo 'Current BC Zone Data' >> $LOG
echo 'with time stamps before and after the dump' >> $LOG
date >> $LOG
azurecli dump "." | tr '[A-Z]' '[a-z]' | grep -v '~cname' | sort | tee $SNAPSHOT >> $LOG
date >> $LOG
cat $LAST_CHANGED | grep '~10.14' | tr '[A-Z]' '[a-z]' | sort | uniq > $LAST_RRs

#
# Format of diff file:
#
# < global.handler.control.278.privatelink.monitor.azure.com~cname~amcs-prod-global-handler.trafficmanager.net
# < q278-eisss-cc-kv01.278.privatelink.vaultcore.azure.net~a~10.141.32.76


if ! cmp -s $SNAPSHOT $LAST_RRs; then
    diff $SNAPSHOT $LAST_RRs |
    grep '~a~' |
    sort | uniq -u |
    cut -d' ' -f2 | cut -d~ -f1 |
    awk '{
        n = split($1, a, ".")
        for (i=1; i<=n; i++) {
            if ( a[i] == "privatelink" ) {
                k = i - 1
            }
        }
        for( j=a[k++]; k <= n; k++)
            j = j "." a[k]
        print j "."
    }' | sort | uniq > $LEAF_CHANGED_ZONES

    for leaf in `cat $LEAF_CHANGED_ZONES`
    do
        zdot=`echo $leaf | awk '{print(substr($0, index($0,".")+1))}'`
        echo $zdot >> $TMP_CHANGED_ZONES
    done
    cat $TMP_CHANGED_ZONES | sort | uniq > $CHANGED_ZONES

    if [[ -n $DEBUG ]]; then
        echo "number of args $#"
        diff $SNAPSHOT $LAST_RRs
        echo 'Changed Leaf Zones'
        cat $LEAF_CHANGED_ZONES
        echo
        echo 'Changed Privatelink Zones'
        cat $CHANGED_ZONES
        exit
    fi

    for leaf in `cat $LEAF_CHANGED_ZONES`
    do
        echo "processing $leaf" | tee -a $LOG
        echo "syncing BC v1 proteus to local leaf yaml directory" | tee -a $LOG
#       octodns-sync --log-stream-stdout --config-file config/bcv1_to_bcv2.yml $leaf --doit | grep -v 'adding dynamic zone' |  tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/bcv1_to_yaml.yml $leaf --doit | grep -v 'adding dynamic zone' |  tee -a $LOG
    done

    for zdot in `cat $CHANGED_ZONES`
    do
        echo "Merging $zdot" | tee -a $LOG
        python yaml-merge.py $zdot
        echo "syncing merged Yaml to QA Azure" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/merged-qa-to-azure.yaml $zdot --doit | grep -v 'adding dynamic zone' | tee -a $LOG
        echo "syncing merged Yaml to Prod Azure" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/merged-prod-to-azure.yaml $zdot --doit | grep -v 'adding dynamic zone' | tee -a $LOG

        zone=`echo $zdot | sed -e 's/.$//'`
        DST="$UNBOUND_DATA_DIR/$zone"
        test -f $DST || touch $DST
        echo "creating pub -> pri CNAME records for $zone" | tee -a $LOG
        azurecli list -t cnames $zone  > $DST
    done

    echo "generating unbound configuration data for local pub to priv CNAMEs" | tee -a $LOG
    cd $UNBOUND_DATA_DIR
    cat *.io *.com *.net *.ms  > $UNBOUND_DIR/local-zone-data.conf

    # Restart unbound and dnsdist for any changes
    doas -u ansible ansible-playbook -t vars,unbound-data -l dns1,dns4,dns5 ~ansible/systems/unbound.yaml | tee -a $LOG
    # doas -u ansible ansible-playbook -v -t vars,dnsdist-data -l dns1,dns4,dns5 ~ansible/systems/dns.yaml | tee -a $LOG

    TSTAMP_STOP=`date +"%Y-%m-%dT%H-%M-%S"`
    echo $TSTAMP_STOP >> $LOG
    SCANF="scan_${TSTAMP_START}_${TSTAMP_STOP}.log"
    TSTF="${LOGDIR}/$SCANF"
    cp $LOG $TSTF
    rm $LAST_CHANGED
    cd $LOGDIR
    ln -s `basename $TSTF` `basename $LAST_CHANGED`
else
    echo "No Changes to be made" | tee -a $LOG
    TSTAMP_STOP=`date +"%Y-%m-%dT%H-%M-%S"`
    echo $TSTAMP_STOP >> $LOG
    SCANF="scan_${TSTAMP_START}_${TSTAMP_STOP}.log"
    TSTF="${LOGDIR}/$SCANF"
    cat $LOG | grep -v '~10.14' >  $TSTF
fi

rm -f $LEAF_CHANGED_ZONES $CHANGED_ZONES
