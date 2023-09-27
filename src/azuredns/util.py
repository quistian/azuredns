#!/usr/bin/env python

import json
import os
import random
import re
import sys
import time
from os.path import exists
from pprint import pprint

import psycopg2
import yaml
from dotenv import load_dotenv
from progressbar import ETA, Bar, Counter, ProgressBar, SimpleProgress
from yaml.loader import SafeLoader

from azuredns import api, config

Debug = True
Debug = False

""" Higher level functions interacting with the BC API """

def has_subzones(zone):
# ent: [{'id': 2865570, 'name': 'privatelink', 'type': 'Zone', 'properties': {'absoluteName': 'privatelink.openai.azure.com'}}]
    zone_ent = api.get_zones_by_hint(zone)
    zone_ent_id = zone_ent[0]['id']
    sub_ents = api.get_entities(zone_ent_id, api.Z_Type)
    if len(sub_ents):
        return True
    else:
        return False

def is_leaf(zone):
    return not has_subzones(zone)

# Normalize and merges BC data and returns a yaml/json structure for each of QA and PROD

def normalize(zone):
    qa_yaml = dict()
    prod_yaml = dict()
    bc_dir = f"{config.Root}/bc-zones"
    dst_yamlf = f"{config.Root}/qa-yaml/{zone}.yaml"
    prod_pattern = "[qds]301ams.*"
    ids = get_active_hrids()
    bc_files = os.listdir(bc_dir)
    for file in bc_files:
        toks = file.split(".")
        leaf = toks[0]
        resource = ".".join(toks[1:-1])
        if leaf in ids and zone == resource:
            data = get_yaml_file(f"{bc_dir}/{file}")
            for name in data:
                if Debug:
                    print
                    print(name)
                lc_name = name.lower()
                ip = data[name]["values"][0]
                t1 = lc_name[0]
                num = lc_name[1:4]
                octets = ip.split(".")
                subnet = ".".join(octets[:2])
                if num == leaf:
                    if t1 in "qds" and subnet == "10.141":
                        qa_yaml[lc_name] = data[name]
                    elif (
                        t1 in "np" or re.match(prod_pattern, lc_name)
                    ) and subnet == "10.140":
                        prod_yaml[lc_name] = data[name]
                    else:
                        print(
                            f"Record in {file} Hostname: {name} and {data[name]} is not compliant"
                        )
                else:
                    print(
                        f"Hostname: {name} does not match HRIS number {leaf} from {file}"
                    )
    return (qa_yaml, prod_yaml)

# Return local yaml zone data as json

def get_yaml_file(fname):
    with open(fname, "r") as fd:
        data = yaml.load(fd, Loader=SafeLoader)
    return data

#
# returns all defined HRID numbers
#

def get_hr_nums():
    hrids = []

    home_dir = os.path.expanduser("~")
    load_dotenv(f"{home_dir}/.psqlrc")
    host = os.environ.get("PGHOST")
    db = os.environ.get("PGDATABASE")
    uname = os.environ.get("PGUSER")
    pw = os.environ.get("PGPASSWORD")

    conn = psycopg2.connect(host=host, dbname=db, user=uname, password=pw)
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM orgs")
        for rec in cur:
            (i, nm, org, hrid) = rec
            if hrid is not None:
                hid = int(hrid)
                if hid < 1000 and hid not in hrids:
                    hrids.append(hid)
        return hrids
    except psycopg2.Error as e:
        print(f"Database error: {e.pgerror}")

#    conn = psycopg2.conn(dbname='obm', user='eng_ro_api', password='w7NDGTzm')

def get_azure_zones():
    fname = f"{config.Path}/azure-resource-names.json"
    with open(fname) as fd:
        azones = json.load(fd)
    return azones

def get_active_hrids():
    leafs = []
    fname = f"{config.Path}/hrids.json"
    with open(fname, "r") as fd:
        hrids = json.load(fd)
    for h in hrids:
        leafs.append(f"{h:03}")
    return leafs

# get all leaf_zones for active Azure HRIDS

def get_leaf_zones():
    leafs = []
    hrids = get_active_hrids()
    resources = get_azure_zones()
    for r in resources:
        for h in hrids:
            leafs.append(f"{h:03}.{r}")
    return leafs

# returns the Zone Entity ID for a given Zone

def get_zone_id(zone):
    Iterative = False
    if not Iterative:
        return zone_exists(zone)
    else:
        toks = zone.split(".")
        toks.reverse()
        pid = config.ViewId
        for tok in toks:
            ents = api.get_entities(pid, Z_Type, 0, 999)
            if config.Debug:
                print(f'\nSubdomain: {tok}\n Child Entities')
                pprint(ents)
            cid = pid
            for ent in ents:
                if ent["name"] == tok:
                    cid = ent["id"]
                    break
            pid = cid
        return pid

def print_leaf_zones():
    leaves = get_leaf_zones()
    for leaf in leaves:
        print(leaf)

def create_leaf_zones():
    leafs = get_leaf_zones()
    cnt = len(leafs)
    pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=cnt).start()
    for i in range(cnt):
        add_zone_if_new(leafs[i])
        pbar.update(i + 1)
    pbar.finish()

def create_test_A_records():
    for zone in get_leaf_zones():
        subnet = "10.141"
        b1 = random.randrange(1, 254, 1)
        b2 = random.randrange(1, 254, 1)
        ip = f"{subnet}.{b1}.{b2}"
        hris_num = zone.split(".")[0]
        hname = f"n{hris_num}_test"
        fqdn = f"{hname}.{zone}"
        add_A_RR(fqdn, ip)

def get_tlds(zones):
    tlds = []
    for z in zones:
        tks = z.split(".")
        if tks[-1] not in tlds:
            tlds.append(tks[-1])
    return tlds

def create_azure_zones():
    azones = get_azure_zones()
    cnt = len(azones)
    pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=cnt).start()
    for i in range(cnt):
        azone = azones[i]
        add_zone_if_new(azone)
        pbar.update(i + 1)
    pbar.finish()

# create a Zone if it does not exist in a recursive way

def create_zone_in_an_iterative_manner(zone):
    toks = zone.split(".")
    toks.reverse()
    pid = config.ViewId
    for tok in toks:
        ents = api.get_entities(pid, Z_Type, 0, 999)
        if Debug:
            pprint(ents)
        cid = pid
        for ent in ents:
            if ent["name"] == tok:
                cid = ent["id"]
                break
        if cid == pid:
            apient = api.APIEntity(name=tok, type=Z_Type, properties=Z_Props)
            cid = api.add_entity(pid, apient)
            e = api.get_entity_by_id(cid)
            if Debug:
                print(f"Created zone {tok} with entity properties: {e}")
        pid = cid


# create cnamne inclusion file for unbound

def get_cname_rrs():
    for zone in get_azure_zones():
        rrs = get_bc_azure_zone(zone)
        for hname in rrs:
            lname = hname.lower()
            priv_fqdn = f'{lname}.{zone}'
            toks = priv_fqdn.split(".")
            toks.pop(1)
            if toks[0] == 'vaultcore':
                toks[0] = 'vault'
            pub_fqdn = ".".join(toks)
            ip = rrs[hname]['values'][0]
            print(f'local-data: "{pub_fqdn}. CNAME {priv_fqdn}."')

# gets a BC Azure zone, with all its associated HRIS leaf sub zone RRs
# data able to be converted to json or yaml
# return the merged data

def get_merged_bc_azure_zone(zone):
    zone_rrs = dict()
    if has_subzones(zone):
        data = api.get_zones_by_hint(zone)
# ent: [{'id': 2865570, 'name': 'privatelink', 'type': 'Zone', 'properties': {'absoluteName': 'privatelink.openai.azure.com'}}]
        if config.Debug:
            print(f"\nzone: {zone}\nent: {data}")
        pid = data[0]["id"]
        leaf_zone_ents = api.get_entities(pid, api.Z_Type)
        if config.Debug:
            print(f"\nsubzones of {zone}:")
            print(f"entities: {leaf_zone_ents}")
        if len(leaf_zone_ents):
            if config.Debug:
                print(f"There are {len(leaf_zone_ents)} Leaf zones of {zone}:")
                print(leaf_zone_ents)
            for ent in leaf_zone_ents:
                leaf_pid = ent["id"]
                leaf_fqdn = ent["properties"]["absoluteName"]
                rrs = get_leaf_zone_rrs(leaf_pid)
                if len(rrs):
                    for nm in rrs:
                        zone_rrs[nm] = rrs[nm]

    else:
        print(f'Can not merge the leaf zone: {zone}')
    return zone_rrs

def get_leaf_bc_azure_zone(zone):
    rrs = dict()
    if is_leaf(zone):
        data = api.get_zones_by_hint(zone)
        rrs = get_leaf_zone_rrs(data[0]['id'])
    else:
        print(f'{zone} is not a leaf zone')
    return rrs

def get_leaf_names(zone):
    subzones = list()
    if has_subzones(zone):
        data = api.get_zones_by_hint(zone)
        ents = api.get_entities(data[0]['id'], api.Z_Type)
        for ent in ents:
            subzones.append(ent['name'])
    else:
        print(f'{zone} has no leaf or subzones')
    return subzones

# get rrs from a leaf zone in yaml format
# given the parent ID for a leaf zone

def get_leaf_zone_rrs(pid):
    rrs = dict()
    rr_ents = api.get_entities(pid, api.RR_Type)
    for rr_ent in rr_ents:
        name = rr_ent["name"]
        ip = rr_ent["properties"]["rdata"]
        rrs[name] = {"type": "A", "values": [ip]}
    return rrs

# gets the FQDNs for a given zone, for all HRID subzones under it
# returns a dictionary of { fqdn: A record IP }

def get_zone_fqdns(zone):
    rrs = dict()
    zid = get_zone_id(zone)
    leaf_ents = api.get_entities(zid, Z_type, 0, 999)
    for ent in leaf_ents:
        leaf_id = ent['id']
        rr_ents = apt.get_entities(leaf_id, api.RR_type)

def add_zone_if_new(zone):
    data = api.get_zones_by_hint(zone)
    if len(data) == 0:
        zone_id = api.add_zone(zone)
        if config.Debug:
            print(f"created zone: {zone} with id: {zone_id}")
    else:
        if config.Debug:
            print(f"DNS zone: {zone} already exists with entity properties: {data}")
        zone_id = data[0]["id"]
    return zone_id

# return entity Id if zone exists

def zone_exists(zone):
    data = api.get_zones_by_hint(zone)
    if len(data):
        return data[0]["id"]
    else:
        return False

# adds an Azure record in the proper BlueCat Location

def add_A_rr(fqdn, ip):
    toks = fqdn.split(".")
    host = toks.pop(0)
    zone = ".".join(toks)
    if not legit_hostname(host):
        print(f'{host} is not an Azure qualified host name')
    elif zone not in get_azure_zones():
        print(f'{zone} is not an Azure resource/zone name')
    else:
        hrnum = host[1:4]
        leaf_zone = f'{hrnum}.{zone}'
        if zone_exists(leaf_zone):
            rrs = get_leaf_bc_azure_zone(leaf_zone)
            if host in rrs.keys():
                print(f'{fqdn} already has an A record')
            else:
                a_rr_entity = api.apientity(host, ip)
                zid = get_zone_id(leaf_zone)
                eid = api.add_entity(zid, a_rr_entity)
                print(f'Added A record for {fqdn} at {leaf_zone} with value {ip}')
        else:
            print(f'Leaf zone: {leaf_zone} does not yet exist')

#
# input does not include the leaf zone in the format
# deletes a specific A record from BC leaf zone
# e.g q301_test.privatelink.openai.azure.com
#     will delete q301_test.301.privatelink.openai.azure.com if it exists

def del_A_rr(fqdn, ip):
    if config.Debug:
        print(f'To delete: {fqdn}')
    toks = fqdn.split(".")
    host = toks.pop(0)
    zone = ".".join(toks)
    if not legit_hostname(host):
        print(f'{host} is not an Azure qualified host name')
    elif zone not in get_azure_zones():
        print(f'{zone} is not an Azure resource/zone name')
    else:
        hrnum = host[1:4]
        leaf_zone = f'{hrnum}.{zone}'
        zid = zone_exists(leaf_zone)
        if zid:
            rr_ents = api.get_entities(zid, api.RR_Type)
            found = False
            for rr_ent in rr_ents:
                if host == rr_ent['name']:
                    found = True
                    api.delete_entity(rr_ent['id'])
                    print(f'Deleted A record {fqdn} which was in {leaf_zone}')
                    break
            if not found:
                print(f'There are no {fqdn} A records in the leaf zone: {leaf_zone}')
           
        else:
            print(f'No leaf zone: {leaf_zone} corresponds to {fqdn}')

# output RRs in a form easily adapted to opencli arguments
# takes yaml format as input

def fmt(zone, data):
    fdata = dict()
    for hname in data:
        hris_num = hname[1:4]
        fqdn = f'{hname}.{hris_num}.{zone}'
        ip = data[hname]['values'][0]
        fdata[fqdn] = ip
    return fdata

def legit_hostname(name):
    lname = name.lower()
    fchars = "qapn"
    l = len(lname)
    if l < 4:
        return False
    if lname[0] not in "qapn":
        return False
    if not lname[1:4].isnumeric:
        return False
    return True
    
def delete_zone(zone):
    deleted = False
    ents = api.get_entities(config.ViewId, Z_Type)
    for ent in ents:
        zid = ent["id"]
        zname = ent["name"]
        if zname == zone:
            deleted = True
            print(f"deleting TLD: {zname}")
            api.delete_entity(zid)
    if not deleted:
        print(f"zone {zone} has already been deleted or does not exist")


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

"""

Fetch an RR entity given a type, and property

"""

def get_RRs(zone):
    zid = zone_exists(zone)
    if zid:
        ents = api.get_entities(zid, api.RR_Type)
    return ents

def old_del_A_rr(fqdn, ip):
    props = {
        "type": "A",
        "rdata": ip,
    }
    toks = fqdn.split(".")
    hname = toks[0]
    zone = ".".join(toks[1:])
    zid = zone_exists(zone)
    if zid:
        ents = api.get_entities(zid, api.RR_Type)
        for ent in ents:
            if ent["name"] == hname:
                props = ent["properties"]
                if props["type"] == "A" and props["rdata"] == ip:
                    if Debug:
                        print(f"Deleting Generic Record Entity: {ent}")
                    api.delete_entity(ent["id"])

def dump_dns_data():
    ents = api.get_entities(config.ViewId, Z_Type)
    for ent in ents:
        zid = ent["id"]
        zname = ent["name"]
        rrs = []
        for e in api.export_entities(zid):
            rrs.append(e)
        with open(f"{config.Path}/{zname}-rrs.json", "w") as rr_fd:
            json.dump(rrs, rr_fd, indent=4, sort_keys=True)


"""
Looking for the following data structure to write out to the octodns yaml file
{
    '': { 'type': 'A', 'values': ['1.2.3.4', '1.2.3.5'] },
    '*': { 'type': 'CNAME', 'value': 'www.example.com.' },
    'www': {'type': 'A', 'values': ['1.2.3.4', '1.2.3.5'] },
    'www.sub': {'type': 'A', 'values': ['1.2.3.6', '1.2.3.7'] }
}
"""


def gen_yaml():
    ydict = {}
    azone_dict = {}
    rr_dict = {}
    zones = get_leaf_zones()
    for zone in zones:
        toks = zone.split(".")
        azone = ".".join(toks[1:])
        ents = get_RRs(zone)
        for ent in ents:
            hname = ent["name"]
            props = ent["properties"]
            typ = props["type"]
            ips = ["1.1.1.1"]
            ips[0] = props["rdata"]
            rr_dict = {
                "type": typ,
                "values": ips,
            }
            if azone in ydict:
                ydict[azone][hname] = rr_dict
            else:
                ydict[azone] = {}
                ydict[azone][hname] = rr_dict
    return ydict


def update_yaml_zone_file(yamlf, rr_dict):
    if exists(yamlf):
        yaml_dict = get_yaml_file(yamlf)
        if yaml_dict == rr_dict:
            if config.Debug:
                print(f"No need to update {yamlf}, data is the same")
        else:
            print(f"Updating file: {yamlf}")
            with open(yamlf, "w") as fd:
                yaml.dump(rr_dict, fd)
    else:
        print(f"Creating new yaml zone file: {yamlf}")
        with open(yamlf, "w") as fd:
            yaml.dump(rr_dict, fd)


def gen_octodns_static_config():
    ydata = {
        "manager": {"include_meta": False, "max_workers": 2},
        "providers": {
            "config": {
                "class": "octodns.provider.yaml.YamlProvider",
                "directory": "./zones",
                "default_ttl": 3600,
                "enforce_order": True,
            },
            "azure": {
                "class": "octodns_azure.AzurePrivateProvider",
                "client_id": "env/AZURE_APPLICATION_ID",
                "key": "env/AZURE_AUTHENTICATION_KEY",
                "directory_id": "env/AZURE_DIRECTORY_ID",
                "sub_id": "env/AZURE_SUBSCRIPTION_ID",
                "resource_group": "Q9011ADCO-CC-PvDNS-RG01",
            },
        },
        "zones": {},
    }
    with open(f"{config.Path}/azure-resource-names.json") as fd:
        resources = json.load(fd)
    for zone in resources:
        ydata["zones"][f"{zone}."] = {"sources": ["config"], "targets": ["azure"]}
    ystr = yaml.dump(ydata)
    print(ystr)


def dns_init():
    view_id = api.bam_init()
    cwd = os.getcwd()
    home_dir = os.path.expanduser("~")
    config.Root = f"{home_dir}/src/azure/azuredns"
    config.Path = f"{config.Root}/src/azuredns"
