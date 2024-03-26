#!/usr/bin/env python

"""

Beginning of a Python Library to interact witn the BC Integrity v2 API

"""

import json
import os
import sys
from pprint import pprint

import psycopg2
import yaml
from bluecat_libraries.address_manager.apiv2 import Client, MediaType
from bluecat_libraries.address_manager.apiv2 import BAMV2ErrorResponse
from dotenv import load_dotenv
from yaml.loader import SafeLoader

from azuredns import config

# local configuration constants, variables and initial values


Z_Props_Not_Deployable = {
    "deployable": "false",
    "dynamicUpdate": "false",
}

Z_Props_Deployable = {
    "deployable": "true",
    "dynamicUpdate": "false",
}

from azuredns import config

"""

{'details': 'Missing parameter types, supported types:[HostRecord, '
            'HINFORecord, DHCP6Range, Configuration, Zone, IP4Address, '
            'IP6Address, AliasRecord, IP4Network, View, NAPTRRecord, '
            'IP6Network, TXTRecord, MACAddress, ExternalHostRecord, '
            'DHCP4Range, MXRecord, IP4Block, SRVRecord, GenericRecord, '
            'IP6Block]',
 'hint': '"selectCriteria":{"selector":"search", "types":"Configuration, View, '
         '...","keyword":"*"}',
 'issue': 'Missing required parameter'}

select_criteria is a dictionary:
{
    "selector": "search",
    "startEntityID": int,
    "children_only": True,
    "types": "Configuration,View,Zone",
    "keyword": "*"
}
"""


def import_entities():
    Clnt.import_entities()

def get_system_info():
    return Clnt.get_system_info()


# get the parent entity of a given entity


def get_parent(eid):
    return Clnt.get_parent(eid)


"""
Adds and Entity Object
Returns the Id of the new entity

Parameters:
    parent_id (int): The parent ID of the object to be created
    entity (APIEntity): The entity to add, structured as such

    e.g.
        props = {
               "comments": "A solo A Resource Record",
               "type": "A"
               "rdata": "128.100.166.120",
        }
        entity = APIEntity(name='bozo', type='GenericRecord', properties=props)

"""


def add_entity(pid, ent):
    new_ent_id = Clnt.add_entity(parent_id=pid, entity=ent)
    return new_ent_id


# Returns None


def delete_entity(eid):
    Clnt.delete_entity(eid)


# Returns None


def delete_entity_with_optipons(eid):
    Clnt.delete_entity_with_optipons(eid)


"""

Gets a list of entities for a given parent object

Parameters:
    parent_id (int):
    type (str): the type of object to return
    start (int, optional); where on the list to begin
    count (int, optional): the maximum child objects to return, default is 10
    include_ha (bool, optional) include HA info from server. default is True

Returns a list of entities

"""


def get_entities(pid, typ, start=0, count=999):
    ents = Clnt.get_entities(pid, typ, start, count)
    return ents


def get_entities_by_name(pid, nm, typ):
    return Clnt.get_entities_by_name(pid, nm, typ)


def get_entities_by_name_using_options(pid, nm, typ):
    return Clnt.get_entities_by_name_using_options(pid, nm, typ)


def get_entity_by_id(pid):
    return Clnt.get_entity_by_id(pid)


def get_entity_by_name(pid, nm, typ):
    return Clnt.get_entity_by_name(pid, nm, typ)


"""
Updates an existing entity
returns None

Use:
    ent = Clnt.get_entity_by_id(ent_id)
    ent['name'] = 'bozo.quist.ca'
    ent['properites']['comment'] = 'New name'
    Clnt.update_entity(ent)

"""


def update_entity(ent):
    Clnt.update_entity(ent)


"""
Only applies to SRV MX records etc.
"""


def update_entity_with_options(ent, opts):
    Clnt.update_entity_with_options(ent, opts)


"""
Adds a generic using an absolute name.

type: string, one of:
    A, A6, AAAA, AFSDB, APL, CAA, CERT, DHCID, DNAME,
    DNSKEY, DS, ISDN, KEY, KX, LOC, MB, MG, MINFO, MR, NS, NSAP, PX, RP,
    RT, SINK, SSHFP, TLSA, WKS, TXT, and X25.

rdata: data of the resource in BIND format

ttl: optional int

properties: option, dictionary
including comments and user-defined fields


returns the id of the new RR

"""


def add_generic_record(viewid, fqdn, typ, rdata):
    return Clnt.add_generic_record(viewid, fqdn, typ, rdata)


"""
add a zone at the top level
returns (int) the Id of the new zone

entity_id (int):
    The object ID of the parent object to which the zone is being added.
    For top-level domains, the parent object is a DNS view.
    For sub- zones, the parent object is a top-level domain or DNS zone.

absolute_name (str):
    The FQDN of the zone with no trailing dot.

properties (dict, optional):
    template - An optional network template association.
    deployable - A boolean value. Set to true to make the zone deployable. The default value is false.

These properties are supported by Address Manager v9.4.0:

    dynamicUpdate - A boolean value.
        If set to true, any resource records that are added, updated, or deleted
        within the zone will be selectively deployed to the associated primary DNS/DHCP Server of that zone.
        The default value is false.
    moveDottedResourceRecords - A boolean value.
        If set to false, existing dotted-name resource records matching the new subdomain will not be moved into the new subdomain.
        The default value is true.
"""


def add_zone(zone):
    try:
        ent_id = Clnt.add_zone(
            entity_id=config.ViewId,
            absolute_name=zone,
            properties=Z_Props_Not_Deployable,
        )
        return ent_id
    except ErrorResponse as e:
        print(f"Error tryong to add zone {zone}: {e.message}")


"""
Gets a list of accessible zones of child objects for a given container_id value.
Returns a list of zone entities

container_id (int):
    The object ID of the container object.
    It can be the object ID of any object in the parent object hierarchy.
    The highest parent object is the configuration level.

options (dict_:
    A dictionary containing search options. It includes the following keys:
        hint: A string specifying the start of a zone name.
        overrideType: A string specifying the overriding of the zone. Must be a BAM Object value.
        accessRight: A string specifying the access right for the zone. Must be a BAM Access right value.

start (int, optional):
    Indicates where in the list of objects to start returning objects.
    The list begins at an index of 0. The default value is 0.

count (int, optional):
    Indicates the maximum number of child objects that this method will return.
    The maximum value is 10. The default value is 10.

"""

# zone properties
# {'id': 100919, 'name': 'ca', 'type': 'Zone', 'properties': {'deployable': 'false', 'dynamicUpdate': 'false', 'absoluteName': 'ca'}}


def bam_v2_init():
    unix_ver = os.uname().sysname
    if unix_ver == "Linux":
        ca_bundle = "/etc/ssl/certs/USERTrust_RSA_Certification_Authority.pem"
    elif unix_ver == "OpenBSD":
        ca_bundle = "/etc/ssl/Sectigo-AAA-chain.pem"
    else:
        ca_bundle = "/etc/group"

    home_dir = os.path.expanduser("~")
    load_dotenv(f"{home_dir}/.bamrc")
    #    load_dotenv(f"{home_dir}/.psqlrc")
    #    load_dotenv(f"{home_dir}/.azurerc")
    url = os.environ.get("BAM_APIv2_URL")
    uname = os.environ.get("BAM_USER")
    pw = os.environ.get("BAM_PW")
    url = 'https://proteus-dev.its.utoronto.ca/api/v2/'

    with Client(url, verify=False) as client:
        client.login(uname, pw)
    #    version = client.bam_version()
        try:
            resp = client.http_get("/configurations")
            pprint(resp)
            confs = resp["data"]
            for conf in confs:
                print(conf)
        except BAMV2ErrorResponse as exc:
            print(exc.message)
            print(exc.status)
            print(exc.reason)
            print(exc.code)
        client.logout()

"""
When the record is to be added:
        props = {
               "comments": "A solo A Resource Record",
               "type": "A",
               "rdata": "128.100.166.120",
        }
        entity = APIEntity(name='bozo', type='GenericRecord', properties=props)

       GenericRecord entity data structure:
       {
           'id': 163642,
           'name': 'a',
           'type': 'GenericRecord',
           'properties':
                {
                    'comments': 'A solo A Resource Record',
                    'absoluteName': 'a.b.c.d',
                    'type': 'A',
                    'rdata': '1.2.3.4'
                }
        }
"""


def apientity(hname, ip):
    props = {
        "comments": "An Azure Private DNS A record",
        "type": "A",
        "rdata": ip,
    }
    return APIEntity(name=hname, type="GenericRecord", properties=props)


"""
Looking for the following data structure to write out to the octodns yaml file
{
    '': { 'type': 'A', 'values': ['1.2.3.4', '1.2.3.5'] },
    '*': { 'type': 'CNAME', 'value': 'www.example.com.' },
    'www': {'type': 'A', 'values': ['1.2.3.4', '1.2.3.5'] },
    'www.sub': {'type': 'A', 'values': ['1.2.3.6', '1.2.3.7'] }
}
"""

def main():
    bam_v2_init()

if __name__ == '__main__':
    main()
