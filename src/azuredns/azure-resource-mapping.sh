#!/bin/sh

AzureResourceURL='https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-dns'

echo "$AzureResourceURL"
exit
curl "$AzureResourceURL" |
sed -e '1,/^<tbody>/d' -e '/^<.tbody>/
