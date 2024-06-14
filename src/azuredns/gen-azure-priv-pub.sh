#!/bin/sh

# Generates Azure Private to Public DNS name mapping in json format

# cat private-endpoint-dns.md |

URL="https://raw.githubusercontent.com/MicrosoftDocs/azure-docs/main/articles/private-link/private-endpoint-dns.md"

curl --silent $URL | tee priv-pub-azure.md |
grep '^>|' | grep privatelink |
grep -v '\.cn ' |
grep -v 'usgovcloudapi' |
sed -e 's/ //g' |
sed -e 's:<sup>1</sup>::g' |
sort | uniq | tee temp.tmp |
awk -F\| '
{
    if ( $0 !~ /<.*br.*>/ ) {
        printf "    \"%s\": \"%s\",\n", $4, $5
    } else {
        n = split($4,a,"<.*br.*>")
        m = split($5,b,"<.*br.*>")
        for (i=1; i<=n; i++) {
            if (i > m ) {
                pub = b[m]
            } else {
                pub = b[i]
            }
            printf "    \"%s\": \"%s\",\n", a[i], pub
        }
    }
}
' | sort | uniq |
sed -e 's/{regionName}/canadacentral/g' -e 's/{regionCode}/canadacentral/g' |
awk '
BEGIN { print "{" }
{ print }
END { print "}" }
'

exit 

#
# Echo deal with <br/>
#
#cat private-endpoint-dns.md |
#grep '^>|' | grep privatelink |
#grep -v '\.cn ' | grep -v '\.us ' | grep -v 'usgovcloud' |
#grep '</*br/*>'
# egrep -v 'blob|table|vault|queue|web' 
