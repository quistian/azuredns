#!/bin/sh

TMP_CHANGED_ZONES=/tmp/azure-changed-zones.$$
LOG="./bc-current-scan.log"
LOGDIR="./logs"
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

( azurecli dump "."; azurecli --flip dump "." ) |
tr [A-Z] [a-z] | sort | uniq -u |
awk -F~ ' { print(substr($1, index($1,".")+1)) "." } ' |
uniq | tee -a $LOG

# relatively slow process ~ 2 minutes
# used to find out which records in which zones have changed since the last
# sweep
# octodns-sync --log-stream-stdout --config-file config/bcv1_to_bcv2.yml --doit | tee -a $LOG
# octodns-sync --log-stream-stdout --config-file config/bc2pdns.yml 234.privatelink.openai.azure.com. --doit | tee -a $LOG
# pdns to yaml is much faster than bc to yaml
#
#if ! grep -s 'No changes were planned' $LOG; then
#    cat $LOG | sed -n 's/^\* [0-9][0-9][0-9]\.//p' | sort | uniq > $TMP_CHANGED_ZONES

if grep -s 'privatelink' $LOG > $TMP_CHANGED_ZONES; then

#       Old method for moving RRs:
#       azurecli sync -s leaf -d merged $z | tee -a $LOG
#       azurecli sync -s merged -d normalized $z | tee -a $LOG

    for leaf in `cat $TMP_CHANGED_ZONES`
    do
        zdot=`echo $leaf | awk '{print(substr($0, index($0,".")+1))}'`
        zone=`echo $zdot | awk '{print(substr($0, 1, length($0)-1))}'`
        echo "processing $leaf and $zdot" | tee -a $LOG
        echo "BC auth to  BC v2" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/bcv1_to_bcv2.yml $leaf --doit | tee -a $LOG
        echo "BC v2 API to merged Yaml" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/bcv2_merge_to_yaml.yml $zdot --doit | tee -a $LOG
        echo "Merged Yaml to QA Yaml" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/merged2qa.yaml $zdot --doit | tee -a $LOG
        echo "Merge Yaml  to PROD Yaml" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/merged2prod.yaml $zdot --doit | tee -a $LOG
        echo "QA Yaml to Azure QA" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/qa2azure.yaml $zdot --force --doit | tee -a $LOG
        echo "Prod Yaml to Azure Prod" | tee -a $LOG
        octodns-sync --log-stream-stdout --config-file config/prod2azure.yaml $zdot --doit >> $LOG
        sh -x gen-unbound-zone-data.sh $zone | tee -a $LOG
    done

    # Restart unbound and dnsdist for any changes
    doas -u ansible ansible-playbook -t vars,unbound-data -l dns1,dns4,dns5 ~ansible/systems/unbound.yaml | tee -a $LOG
    # doas -u ansible ansible-playbook -v -t vars,dnsdist-data -l dns1,dns4,dns5 ~ansible/systems/dns.yaml | tee -a $LOG
fi

TSTAMP_STOP=`date +"%Y-%m-%dT%H-%M-%S"`
echo $TSTAMP_STOP >> $LOG

TSTF="scan_${TSTAMP_START}_${TSTAMP_STOP}.log"
cp $LOG $LOGDIR/$TSTF

rm -f $TMP_CHANGED_ZONES
