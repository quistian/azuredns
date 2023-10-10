#!/usr/bin/env python

RootId = 0
ConfId = 0
ViewId = 0

Conf = "Test"
View = "Azure"

Silent = True
Debug = True

Path = "/tmp"
Root = "/tmp"

Azure_Zone_Files = [
    "ccPrivateDNSZones-parameters.json",
    "cePrivateDNSZones-parameters.json",
    "corePrivateDNSZones-parameters.json",
]

Azure_Resource_URL = 'https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-dns'
