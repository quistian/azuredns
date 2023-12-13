#!/bin/sh

TMP_CHANGED_ZONES=/tmp/azure-changed-zones.$$
LOG="./bc-current-scan.log"
LOGDIR="./logs"
TSTAMP_START=`date +"%Y-%m-%dT%H-%M-%S"`
TSTAMP=$TSTAMP_START
CHANGED="./zone-changes/changed-${TSTAMP}"
OUT=/tmp/changed-zones.$$
ENV=/tmp/env_vars.$$

echo $TSTAMP_START > $LOG

# check to see if the AZURE ENV variables have been loaded yet
# Can also use .azureexportrc
printenv | grep AZURE_ > $ENV
if [ ! $? ]; then
    echo "Azure Vars are being loaded" >> $LOG
    . $HOME/.azureexportrc
fi
printenv | grep BAM_ > $ENV
if [ ! $? ]; then
    echo "BlueCat Vars are being loaded" >> $LOG
    . $HOME/.bamrc
fi
printenv | grep POWERDNS > $ENV
if [ ! $? ]; then
    echo "PowerDNS Vars are being loaded" >> $LOG
    . $HOME/.pdnsrc
fi
rm -f $ENV

echo "Scanning BC zones for changes" | tee -a $LOG

# relatively slow process ~ 2 minutes
# used to find out which records in which zones have changed since the last
# sweep
octodns-sync --quiet --log-stream-stdout --config-file config/bc2pdns.yml --doit | tee -a $LOG
# pdns to yaml is much faster than bc to yaml

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
        gen-unbound-zone-data.sh $z | tee -a $LOG
    #   echo "QA Yaml to Azure QA"
    #   octodns-sync --quiet --log-stream-stdout --config-file config/prod2azure.yaml $z. >> $LOG
    done
    #   doas -u ansible ansible-playbook -K -v -t vars,unbound-data -l dns1,dns4,dns5 ~ansible/systems/dns.yaml | tee -a $LOG
fi

TSTAMP_STOP=`date +"%Y-%m-%dT%H-%M-%S"`
echo $TSTAMP_STOP >> $LOG

TSTF="scan_${TSTAMP_START}_${TSTAMP_STOP}.log"
cp $LOG $TSTF
mv $TSTF $LOGDIR

rm -f $ENV
rm -f $OUT
rm -f $TMP_PRIV_ZONES
