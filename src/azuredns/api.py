#!/usr/bin/env python

import json
import os
import sys
from pprint import pprint

import psycopg2
import yaml
from bluecat_libraries.address_manager.api import Client
from bluecat_libraries.address_manager.api.models import APIEntity
from bluecat_libraries.address_manager.constants import AccessRightValues, ObjectType
from bluecat_libraries.http_client.exceptions import ErrorResponse
from dotenv import load_dotenv
from yaml.loader import SafeLoader

from azuredns import config

# local configuration constants, variables and initial values


V_Type = ObjectType.VIEW
Z_Type = ObjectType.ZONE
Cf_Type = ObjectType.CONFIGURATION
Cname_Type = ObjectType.ALIAS_RECORD
RR_Type = ObjectType.GENERIC_RECORD
Host_Type = ObjectType.HOST_RECORD
Txt_Type = ObjectType.TXT_RECORD
Srv_Type = ObjectType.SRV_RECORD
Ent_Type = ObjectType.ENTITY

Z_Props = {
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

"""


# returns an iterator, not the data itself
def export_entities(start_id):
    selection = {
        "selector": "get_entitytree",
        "types": "Zone,GenericRecord,HostRecord,SRVRecord,TXTRecord,ExternalHostRecord",
        "startEntityId": start_id,
        "keyword": "*",
    }
    ent_iterator = Clnt.export_entities(select_criteria=selection, start=0, count=55000)
    return ent_iterator


def import_entities():
    Clnt.import_entities()


def get_system_info():
    return Clnt.get_system_info()


def get_parent(eid):
    Clnt.get_parent(eid)


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


def delete_entity(eid):
    Clnt.delete_entity(eid)


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


def get_entities(pid, typ):
    ents = Clnt.get_entities(parent_id=pid, type=typ, start=0, count=100)
    return ents


def get_entities_by_name(pid, nm, typ):
    return Clnt.get_entities_by_name(pid, nm, typ)


def get_entities_by_name_using_options(pid, nm, typ):
    return Clnt.get_entities_by_name_using_options(pid, nm, typ)


def get_entity_by_id(pid):
    return Clnt.get_entity_by_id(pid)


def get_entity_by_name(pid, nm, typ):
    return Clnt.get_entity_by_name(pid, nm, typ)


def update_entity(ent):
    return Clnt.update_entity(ent)


def update_entity_with_options(ent):
    return Clnt.update_entity_with_options(ent)


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
            entity_id=config.ViewId, absolute_name=zone, properties=Z_Props
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


def get_zones_by_hint(zone):
    opts = {
        "hint": zone,
        "overrideType": Z_Type,
        "accessRight": AccessRightValues.ViewAccess,
    }
    ents = Clnt.get_zones_by_hint(
        container_id=config.ViewId, options=opts, start=0, count=10
    )
    return ents


# zone properties
# {'id': 100919, 'name': 'ca', 'type': 'Zone', 'properties': {'deployable': 'false', 'dynamicUpdate': 'false', 'absoluteName': 'ca'}}


def bam_init():
    global Clnt

    ca_bundle = "/etc/ssl/certs/USERTrust_RSA_Certification_Authority.pem"

    home_dir = os.path.expanduser("~")
    load_dotenv(f"{home_dir}/.bamrc")
    #    load_dotenv(f"{home_dir}/.psqlrc")
    #    load_dotenv(f"{home_dir}/.azurerc")

    url = os.environ.get("BAM_API_URL")
    uname = os.environ.get("BAM_USER")
    pw = os.environ.get("BAM_PW")

    try:
        Clnt = Client(url, verify=ca_bundle)
        Clnt.login(uname, pw)
        conf_ent = Clnt.get_entity_by_name(config.RootId, config.Conf, Cf_Type)
        if config.Debug:
            print()
            print(f'BAM Configuration: {conf_ent["name"]}')
            print(conf_ent)
        config.ConfId = conf_ent["id"]
        view_ent = Clnt.get_entity_by_name(config.ConfId, config.View, V_Type)
        if config.Debug:
            print()
            print(f'BAM View: {view_ent["name"]}')
            print(view_ent)
            print()
        config.ViewId = view_ent["id"]
        return config.ViewId
    except ErrorResponse as e:
        print(f"Top Level Error: {e.message}")


"""
When the record is to be added:
        props = {
               "comments": "A solo A Resource Record",
               "type": "A",
               "rdata": "128.100.166.120",
        }
        entity = APIEntity(name='bozo', type='GenericRecord', properties=props)

       GenericRecord entity data structure
       {'id': 163642, 'name': 'a', 'type': 'GenericRecord', 'properties': {'comments': 'A solo A Resource Record', 'absoluteName': 'a.b.c.d', 'type': 'A', 'rdata': '1.2.3.4'}}
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
