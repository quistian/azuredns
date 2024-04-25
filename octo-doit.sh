#!/bin/sh

LEAF_CHANGED_ZONES=/tmp/leaf-changed-zones.$$
CHANGED_ZONES=/tmp/azure-changed-zones.$$

LOG="./bc-current-scan.log"
LOGDIR="./logs"
LAST_CHANGED=$LOGDIR/last_changed.log
SNAPSHOT=$LOGDIR/snapshot.log
LAST_RRs=$LOGDIR/last_rrs.log

TSTAMP_START=`date +"%Y-%m-%dT%H-%M-%S"`
TSTAMP=$TSTAMP_START

# Load in the appropriate environment variables for octodns modules
#
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
azurecli dump "." | tr '[A-Z]' '[a-z]' | sort | tee $SNAPSHOT >> $LOG
date >> $LOG
cat $LAST_CHANGED | grep '~10.14' | tr '[A-Z]' '[a-z]' | sort | uniq > $LAST_RRs

#
# Format of diff file:
# 1189c1189
# < q237_new.237.privatelink.openai.azure.com~10.141.11.22
# ---
# > q237_gnu.237.privatelink.openai.azure.com~10.141.221.112

if ! cmp -s $SNAPSHOT $LAST_RRs; then
    diff $SNAPSHOT $LAST_RRs |
    grep '~' |
    tr [A-Z] [a-z] | sort | uniq -u |
    cut -d' ' -f2 | cut -d~ -f1 |
    awk '{
        n = split($1, a, ".")
        i = 2
        j = a[i++]
        while (i <= n ) {
            j = j "." a[i++]
        }
        print j "."
    }' | sort | uniq > $LEAF_CHANGED_ZONES

# 237.privatelink.openai.azure.com.
# 278.privatelink.openai.azure.com.

    for leaf in `cat $LEAF_CHANGED_ZONES`
    do
        zdot=`echo $leaf | awk '{print(substr($0, index($0,".")+1))}'`
        echo $zdot >> $CHANGED_ZONES
        echo "processing $leaf" | tee -a $LOG
        echo "syncing BC auth to  BC v2" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/bcv1_to_bcv2.yml $leaf --doit | tee -a $LOG
    done

    for zdot in `cat $CHANGED_ZONES | sort | uniq`
    do
        echo "processing $zdot" | tee -a $LOG
        echo "syncing BC v2 and merging leaf zones to local Yaml" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/bcv2_merge_to_yaml.yml $zdot --doit | tee -a $LOG
        echo "syncing merged Yaml to QA Yaml" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/merged2qa.yaml $zdot --doit | tee -a $LOG
        echo "syncing merged Yaml  to PROD Yaml" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/merged2prod.yaml $zdot --doit | tee -a $LOG
        echo "syncing QA Yaml to Azure QA Tennant" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/qa2azure.yaml $zdot --force --doit | tee -a $LOG
        echo "syncing Prod Yaml to Azure Prod Tennant" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/prod2azure.yaml $zdot --doit >> $LOG
        zone=`echo $zdot | sed -e 's/.$//'`
        echo "generating unbound data for local pub to priv CNAMEs for zone $zone" | tee -a $LOG
        sh -x gen-unbound-zone-data.sh $zone | tee -a $LOG
    done

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
