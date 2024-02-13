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
if [ -z "${POWERDNS_API_KEY}" ]; then
    echo "PowerDNS Vars are being loaded" >> $LOG
    . $HOME/.pdnsrc
fi

echo $TSTAMP_START > $LOG
echo "Scanning BC zones for changes" | tee -a $LOG

# relatively slow process ~ 2 minutes
# used to find out which records in which zones have changed since the last
# sweep
octodns-sync --log-stream-stdout --config-file config/bc2pdns.yml --doit | tee -a $LOG
# octodns-sync --log-stream-stdout --config-file config/bc2pdns.yml 234.privatelink.openai.azure.com. --doit | tee -a $LOG
# pdns to yaml is much faster than bc to yaml
#
#
#
exit

if ! grep -s 'No changes were planned' $LOG; then
    cat $LOG | sed -n 's/^\* [0-9][0-9][0-9]\.//p' | sort | uniq > $TMP_CHANGED_ZONES
    cat $TMP_CHANGED_ZONES

#       Old method for moving RRs:
#       azurecli sync -s leaf -d merged $z | tee -a $LOG
#       azurecli sync -s merged -d normalized $z | tee -a $LOG

    for zdot in `cat $TMP_CHANGED_ZONES`
    do
        z=`echo $zdot | sed 's/\.$//'`
        echo "processing $z" | tee -a $LOG
        # move data from powerdns -> merge it -> local yaml directory
        echo "PowerDNS to merged Yaml"
        octodns-sync --quiet --log-stream-stdout --config-file config/pdns2yaml.yml $zdot --doit | tee -a $LOG
        echo "merged to QA Yaml"
        octodns-sync --quiet --log-stream-stdout --config-file config/merged2qa.yaml $zdot --doit | tee -a $LOG
        echo "merged to PROD Yaml"
        octodns-sync --quiet --log-stream-stdout --config-file config/merged2prod.yaml $zdot --doit | tee -a $LOG
        echo "QA Yaml to Azure QA"
        octodns-sync --quiet --log-stream-stdout --config-file config/qa2azure.yaml $zdot --force --doit | tee -a $LOG
        sh -x gen-unbound-zone-data.sh $z | tee -a $LOG
    #   echo "QA Yaml to Azure QA"
    #   octodns-sync --quiet --log-stream-stdout --config-file config/prod2azure.yaml $z. >> $LOG
    done
    doas -u ansible ansible-playbook -v -t vars,unbound-data -l dns1,dns4,dns5 ~ansible/systems/unbound.yaml | tee -a $LOG
fi

TSTAMP_STOP=`date +"%Y-%m-%dT%H-%M-%S"`
echo $TSTAMP_STOP >> $LOG

TSTF="scan_${TSTAMP_START}_${TSTAMP_STOP}.log"
cp $LOG $LOGDIR/$TSTF

rm -f $TMP_CHANGED_ZONES
