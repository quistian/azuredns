#!/usr/bin/env python

import json
import os
import random
import re
import sys
import time
import traceback
from os.path import exists
from pprint import pprint

import psycopg2
import requests
import yaml
from bs4 import BeautifulSoup, NavigableString, Tag
from dotenv import load_dotenv
from progressbar import ETA, Bar, Counter, ProgressBar, SimpleProgress
from yaml.loader import SafeLoader

from azuredns import api, config

Debug = True
Debug = False

ThreeDigits = "[0-9][0-9][0-9]"

""" Higher level functions interacting with the BC API """

# ent: [{'id': 2865570, 'name': 'privatelink', 'type': 'Zone', 'properties': {'absoluteName': 'privatelink.openai.azure.com'}}]


def caller():
    return traceback.extract_stack()[-2][2]


# prints out zone names using recursion
def recurse(eid):
    ents = api.get_entities(eid, api.Z_Type)
    if len(ents):  # subzones exist
        hname = ents[0]["name"]
        fqdn = ents[0]["properties"]["absoluteName"]
        toks = fqdn.split(".")
        zone = ".".join(toks[1:])
        if re.match(ThreeDigits, hname):
            print(f"{zone}")
            return zone
        else:
            for ent in ents:
                recurse(ent["id"])

def recurse_2_leafs(eid):
    ents = api.get_entities(eid, api.Z_Type)
    if len(ents):
        for ent in ents:
            recurse_2_leafs(ent["id"])
    else:
        ent = api.get_entity_by_id(eid)
        print(ent["properties"]["absoluteName"])


"""
The following use the API primitive export_entities to get at the leaf zones
and the level above

The Zone entity looks like:

{'name': '574', 'id': 2865801, 'type': 'Zone', 'properties': {'dynamicUpdate': False, 'deployable': False, 'absoluteName': '574.scm.privatelink.azurewebsites.net'}}
{'name': 'ca', 'id': 2910936, 'type': 'Zone', 'properties': {'dynamicUpdate': False, 'deployable': False, 'absoluteName': 'ca'}}
{'name': 'org', 'id': 2910937, 'type': 'Zone', 'properties': {'dynamicUpdate': False, 'deployable': False, 'absoluteName': 'org'}}

"""


def gen_bc_leaf_zones():
    leafs = []
    entities_iterator = api.export_entities()
    for ent in entities_iterator:
        if re.match(ThreeDigits, ent["name"]):
            leafs.append(ent["properties"]["absoluteName"])
    return leafs


def gen_bc_azure_zones():
    azurezones = []
    for leaf in gen_bc_leaf_zones():
        toks = leaf.split(".")
        toks.pop(0)
        azone = ".".join(toks)
        if azone not in azurezones:
            azurezones.append(azone)
    return azurezones


# returns a pointer to the list of subzones if a given zone has subzones, i.e.
# is not a leaf, else False
def has_subzones(zone):
    ent = api.get_zones_by_hint(zone)
    if config.Debug:
        print(f"\n{__name__}:", caller())
        print(f"{zone} {ent}")
    sub_ents = api.get_entities(ent[0]["id"], api.Z_Type)
    if len(sub_ents):
        if config.Debug:
            for ent in sub_ents:
                print(ent)
        return sub_ents
    else:
        return False


# returns true is zone is a leaf zone, that is the zone which only has A records and no subzones
def is_leaf(zone):
    if not has_subzones(zone):
        return True
    else:
        return False


# Merges BC leaf zones into a combined BC equivalent of the Azure zone
def merge(zone):
    merged_yaml = dict()
    leaf_dir = f"{config.Root}/leaf-zones"
    dst_yamlf = f"{config.Root}/merged-zones/{zone}.yaml"
    ids = get_active_hrids()
    bc_leaf_files = os.listdir(leaf_dir)
    for leaf_file in bc_leaf_files:
        toks = leaf_file.split(".")
        leaf = toks[0]
        resource = ".".join(toks[1:-1])
        if leaf in ids and zone == resource:
            data = get_yaml_file(f"{leaf_dir}/{leaf_file}")
            for hname, value in data.items():
                num = hname[1:4]
                if num == leaf:
                    merged_yaml[hname] = value
    if config.Debug:
        print(f"Leaves -> Merged: {zone}")
        print(merged_yaml)
    if len(merged_yaml):
        update_yaml_zone_file(dst_yamlf, merged_yaml)
    return


# Normalizes merged BC data and returns a yaml/json structure for each of QA and PROD
def canonical(zone):
    qa_yaml = dict()
    prod_yaml = dict()
    normal_yaml = dict()
    merged_yamlf = f"{config.Root}/merged-zones/{zone}.yaml"
    normal_yamlf = f"{config.Root}/merged-zones/{zone}.yaml"
    qa_yamlf = f"{config.Root}/qa-zones/{zone}.yaml"
    prod_yamlf = f"{config.Root}/prod-zones/{zone}.yaml"
    prod_pattern = "[qds]301ams.*"
    data = get_yaml_file(merged_yamlf)
    for hname, value in data.items():
        lc_hname = hname.lower()
        ip = value["values"][0]
        t1 = lc_hname[0]
        num = lc_hname[1:4]
        octets = ip.split(".")
        subnet = ".".join(octets[:2])
        if (t1 in "np" or re.match(prod_pattern, lc_hname)) and subnet == "10.140":
            normal_yaml[lc_hname] = value
            prod_yaml[lc_hname] = value
        elif t1 in "qds" and subnet == "10.141":
            normal_yaml[lc_hname] = value
            qa_yaml[lc_hname] = value
        else:
            print(
                f"Record in {merged_yamlf} Hostname: {hname} and {value} is not compliant"
            )
    if config.Debug:
        print(f"Merged -> Normalized: {zone}")
        print(normal_yaml)
    if len(normal_yaml):
        update_yaml_zone_file(normal_yamlf, normal_yaml)
    if len(qa_yaml):
        update_yaml_zone_file(qa_yamlf, qa_yaml)
    if len(prod_yaml):
        update_yaml_zone_file(prod_yamlf, prod_yaml)
    return


# Normalize and merges BC data and returns a yaml/json structure for each of QA and PROD
def normalize(zone):
    qa_yaml = dict()
    prod_yaml = dict()
    bc_dir = f"{config.Root}/leaf-zones"
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
            for name, value in data.items():
                if Debug:
                    print
                    print(name)
                lc_name = name.lower()
                ip = value["values"][0]
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


# conn = psycopg2.conn(dbname='obm', user='eng_ro_api', password='w7NDGTzm')
# Returns all defined HRID numbers as per the current NetDisco postgres DB
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


# Gets a list of Azure Private Resource Names from a local file, bc, yaml
def get_azure_private_zones(src="file"):
    azones = list()
    if src == "file":
        fname = f"{config.Path}/azure-resource-names.json"
        with open(fname) as fd:
            azones = json.load(fd)
    elif src == "bc":
        azones = get_bc_private_zones_by_recursion()
    elif src == "azure":
        azure_dir = f"{config.Root}/azure-qa-zones"
        yaml_files = os.listdir(azure_dir)
        for yfile in yaml_files:
            zone = ".".join(yfile.split(".")[:-1])
            azones.append(zone)
    return azones


"""
    priv_zones = []
    fname = f"{config.Path}/azure-priv-pub.json"
    for key in azones.keys():
        if '}' not in key:
            priv_zones.append(key)
    return priv_zones
"""


def get_bc_private_zones_by_recursion():
    recurse(config.ViewId)


def get_bc_leaf_zones_by_recursion():
    recurse_2_leafs(config.ViewId)


def get_active_hrids():
    leafs = []
    fname = f"{config.Path}/hrids.json"
    with open(fname, "r") as fd:
        hrids = json.load(fd)
    for h in hrids:
        leafs.append(f"{h:03}")
    return leafs


# get all leaf_zones for active Azure HRIDS


def gen_leaf_zones_from_dbfile():
    leafs = []
    hrids = get_active_hrids()
    resources = get_azure_private_zones()
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
            ents = api.get_entities(pid, api.Z_Type, 0, 999)
            if config.Debug:
                print(f"\nSubdomain: {tok}\n Child Entities")
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


def gen_tlds():
    tlds = []
    ents = api.get_entities(config.ViewId, api.Z_Type)
    for ent in ents:
        tlds.append(ent["name"])
    return tlds


def create_azure_zones():
    azones = get_azure_private_zones()
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
        ents = api.get_entities(pid, api.Z_Type)
        if Debug:
            pprint(ents)
        cid = pid
        for ent in ents:
            if ent["name"] == tok:
                cid = ent["id"]
                break
        if cid == pid:
            apient = api.APIEntity(
                name=tok, type=Z_Type, properties=api.Z_Props_Not_Deployable
            )
            cid = api.add_entity(pid, apient)
            e = api.get_entity_by_id(cid)
            if Debug:
                print(f"Created zone {tok} with entity properties: {e}")
        pid = cid

# create cname inclusion file for unbound on a per zone basis

def gen_cname_rrs(zone):
    with open(f"{config.Path}/azure-priv-pub.json") as fd:
        priv_pub = json.load(fd)
    if zone in priv_pub.keys():
        yamlf = f"{config.Root}/merged-zones/{zone}.yaml"
        if exists(yamlf):
            pub_zone = priv_pub[zone]
            data = get_yaml_file(yamlf)
            for hname in data:
                print(f'local-data: "{hname}.{pub_zone}. CNAME {hname}.{zone}."')
        else:
            print(f"# {yamlf} does not yet exist")
    else:
        print(f"# no corresponding pub name for priv zone: {zone}")


def get_cname_rrs():
    with open(f"{config.Path}/azure-priv-pub.json") as fd:
        priv_pub = json.load(fd)
    for zone in get_azure_private_zones():
        rrs = get_bc_azure_zone(zone)
        for hname, value in rrs.items():
            lname = hname.lower()
            priv_fqdn = f"{lname}.{zone}"
            toks = priv_fqdn.split(".")
            toks.pop(1)
            if toks[0] == "vaultcore":
                toks[0] = "vault"
            pub_fqdn = ".".join(toks)
            ip = value["values"][0]
            print(f'local-data: "{pub_fqdn}. CNAME {priv_fqdn}."')


# gets a BC Azure zone, with all its associated HRIS leaf sub zone RRs
# data able to be converted to json or yaml
# return the merged data


# ent: [{'id': 2865570, 'name': 'privatelink', 'type': 'Zone', 'properties': {'absoluteName': 'privatelink.openai.azure.com'}}]
def get_merged_bc_azure_zone(zone):
    zone_rrs = dict()
    ents = has_subzones(zone)
    if ents:
        if config.Debug:
            print()
            print(f"There are {len(ents)} Leaf zones of {zone}:")
            print(f"subzones of {zone}:")
            print(f"entities: {ents}")
        for ent in ents:
            leaf_pid = ent["id"]
            leaf_fqdn = ent["properties"]["absoluteName"]
            rrs = get_leaf_zone_rrs(leaf_pid)
            if len(rrs):
                if zone_rrs:
                    zone_rrs.update(rrs)
                else:
                    zone_rrs = rrs
    else:
        print(f"Can not merge the leaf zone: {zone}")
    return zone_rrs


def get_leaf_bc_azure_zone(zone):
    rrs = dict()
    if is_leaf(zone):
        data = api.get_zones_by_hint(zone)
        rrs = get_leaf_zone_rrs(data[0]["id"])
    else:
        print(f"{zone} is not a leaf zone")
    return rrs


def get_leaf_names(zone):
    subzones = list()
    if has_subzones(zone):
        data = api.get_zones_by_hint(zone)
        ents = api.get_entities(data[0]["id"], api.Z_Type)
        for ent in ents:
            subzones.append(ent["name"])
    else:
        print(f"{zone} has no leaf or subzones")
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
    canonical_fqdn = canonicalize(fqdn)
    if config.Debug:
        print(f'add_A_rr: fqdn: {fqdn}, ip: {ip}, canonical fqdn: {canonical_fqdn}')
    ent_id = api.add_generic_record(config.ViewId, canonical_fqdn, "A", ip)
    return ent_id


def canonicalize(fqdn):
    toks = fqdn.split(".")
    hname = toks[0].lower()
    toks[0] = hname
    nums = hname[1:4]
    if toks[1] == "privatelink":
        toks.insert(1, nums)
    return ".".join(toks)


def long_form_add_A_rr(fqdn, ip):
    toks = fqdn.split(".")
    host = toks.pop(0)
    zone = ".".join(toks)
    if not legit_hostname(host):
        print(f"{host} is not an Azure qualified host name")
    elif zone not in get_azure_private_zones():
        print(f"{zone} is not an Azure resource/zone name")
    else:
        hrnum = host[1:4]
        leaf_zone = f"{hrnum}.{zone}"
        if zone_exists(leaf_zone):
            rrs = get_leaf_bc_azure_zone(leaf_zone)
            if host in rrs.keys():
                print(f"{fqdn} already has an A record")
            else:
                a_rr_entity = api.apientity(host, ip)
                zid = get_zone_id(leaf_zone)
                eid = api.add_entity(zid, a_rr_entity)
                print(f"Added A record for {fqdn} at {leaf_zone} with value {ip}")
        else:
            print(f"Leaf zone: {leaf_zone} does not yet exist")


# Input does not include the leaf zone in the format
# Deletes a specific A record from BC leaf zone
# e.g q301_test.privatelink.openai.azure.com
# Will delete q301_test.301.privatelink.openai.azure.com if it exists

# RR entity format
"""
{
    'id': 2866128,
    'name': 'Q277_test',
    'type': 'GenericRecord',
    'properties': {
        'comments': 'A solo A Resource Record',
        'absoluteName': 'Q277_test.277.privatelink.gremlin.cosmos.azure.com',
        'type': 'A',
        'rdata': '10.141.239.118'
    }
}
"""

#       if (t1 in "np" or re.match(prod_pattern, lc_hname)) and subnet == "10.140":


def del_A_rr(fqdn, ip):
    """
    Accepts both forms of fqdn:
    hname.hrid.azure_resource_zone and
    hname.azure_resource_zone
    Does not care at the present time about the value of the IP address
    """
    if config.Debug:
        print(f"To delete: {fqdn}: {ip}")
    toks = fqdn.split(".")
    host = toks.pop(0)
    if not legit_hostname(host):
        print(f"{host} is not an Azure qualified host name")
        return False
    elif toks[0] in get_active_hrids():
        hrid = toks.pop(0)
    else:
        hrid = host[1:4]
    zone = ".".join(toks)
    leaf_zone = f"{hrid}.{zone}"

    if zone not in get_azure_private_zones():
        print(f"{zone} is not an Azure resource/zone name")
        return False
    else:
        zid = zone_exists(leaf_zone)
        if zid:
            rr_ents = api.get_entities(zid, api.RR_Type)
            found = False
            for rr_ent in rr_ents:
                if config.Debug:
                    print(rr_ent)
                if host.lower() == rr_ent["name"].lower():
                    found = True
                    api.delete_entity(rr_ent["id"])
                    print(f"Deleted A record {fqdn} which was in {leaf_zone}")
                    break
            if not found:
                print(f"No A RRs in zone: {leaf_zone} with name: {host}")
        else:
            print(f"No leaf zone: {leaf_zone} corresponds to {fqdn}")


"""
Modify a given A record

When the record is to be added or modified
    props = {
           "comments": "A solo A Resource Record",
           "type": "A",
           "rdata": "128.100.166.120",
    }
    entity = APIEntity(name='bozo', type='GenericRecord', properties=props)
   GenericRecord entity data structure
   Use when doing mods
   {'id': 163642, 'name': 'a', 'type': 'GenericRecord', 'properties': {'comments': 'A solo A Resource Record', 'absoluteName': 'a.b.c.d', 'type': 'A', 'rdata': '1.2.3.4'}}
"""

def mod_A_rr(fqdn, ip):
    """Modify a given Leaf Zone A record. Accept leaf and non leaf form"""
    if config.Debug:
        print(f"To modify: {fqdn}: {ip}")
    toks = fqdn.split(".")
    host = toks.pop(0)
    if not legit_hostname(host):
        print(f"{host} is not an Azure qualified host name")
        return False
    hr_ids = get_active_hrids()
    if toks[0] in hr_ids:
        hrid = toks.pop(0)
    else:
        hrid = host[1:4]
    zone = ".".join(toks)
    leaf_zone = f"{hrid}.{zone}"
    if config.Debug:
        print(f"leaf: {leaf_zone} zone: {zone}")
    if zone not in get_azure_private_zones():
        print(f"{zone} is not an Azure resource/zone name")
        return False
    else:
        zid = zone_exists(leaf_zone)
        if zid:
            rr_ents = api.get_entities(zid, api.RR_Type)
            found = False
            for rr_ent in rr_ents:
                if host.lower() == rr_ent["name"].lower():
                    found = True
                    if config.Debug:
                        print(f"matching rr entity: {rr_ent}")
                    rr_id = rr_ent["id"]
                    rr_ent["properties"]["rdata"] = ip
                    api.update_entity(rr_ent)
                    print(
                        f"Updated A record {fqdn} with addr {ip} which was in {leaf_zone}"
                    )
                    if config.Debug:
                        rr_new = api.get_entity_by_id(rr_id)
                        print(f"new rr entity: {rr_new}")
                    break
            if not found:
                print(f"No A RRs in zone: {leaf_zone} with name: {host}")
        else:
            print(f"No leaf zone: {leaf_zone} corresponds to {fqdn}")


def fqdn_exists(fqdn):
    toks = fqdn.split(".")
    host = toks.pop(0)
    zone = ".".join(toks)
    if is_zone(fqdn):
        return True


# output RRs in a form easily adapted to opencli arguments
# takes yaml format as input


def fmt(zone, data):
    fdata = dict()
    for hname, value in data.items():
        hris_num = hname[1:4]
        fqdn = f"{hname}.{hris_num}.{zone}"
        ip = value["values"][0]
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


def modify_zone(zone, props):
    zid = zone_exists(zone)
    if zid:
        ent = api.get_entity_by_id(zid)
        if config.Debug:
            print(ent)
        before = ent["properties"]["deployable"]
        after = props["deployable"]
        print(f"Before: deployable: {before}")
        print(f"After:  deployable: {after}")
        ent["properties"]["deployable"] = after
        api.update_entity(ent)
    else:
        print(f"{zone} does not exist")


def delete_zone(zone):
    deleted = False
    ents = api.get_entities(config.ViewId, api.Z_Type)
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


def dump_dns_data(zone):
    rrs = list()

    if zone == ".":
        entity_id = config.ViewId
    else:
        entity_id = get_zone_id(zone)

    select = {
        "selector": "get_entitytree",
        "startEntityId": entity_id,
        "types": "GenericRecord,HostRecord,AliasRecord,TXTRecord,MXRecord",
        "children_only": False,
    }

    for e in api.export_entities(selection=select):
        if e['type'] == 'GenericRecord':
            props = e['properties']
            if props['type'] == "A":
                print(f'{props["absoluteName"]}~{props["rdata"]}')
        rrs.append(e)
#    with open(f"{config.Path}/rrs.json", "w") as rr_fd:
#        json.dump(rrs, rr_fd, indent=4, sort_keys=True)

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
            toks = yamlf.split("/")
            fname = toks[-1]
            zone = ".".join(fname.split(".")[1:-1])
            print(f"Updating file: {fname} zone: {zone}")
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


# Generate a Azure Private -> Public JSON file, from a local html file or
# refresh from the URL.


def gen_azure_priv_pub_json(src):
    Azure_Resource_URL = (
        "https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-dns"
    )
    Fname = "azure-resource-page.html"
    JsonFile = "azure-resource-private-public-names.json"

    mappings = {
        "{dnsPrefix}": ["ca"],
        "{regionCode}": ["cnc", "cne"],
        "{regionName}": ["canadacentral", "canadaeast"],
        "{regionCode}": ["ca"],
        "{partitionId}": ["237"],
        "{instanceName}": ["UofT"],
        "{workspaceName}": ["NonProd"],
    }

    priv2pub = dict()

    if src == "http" or (
        not exists(Fname)
    ):  # get the data remotely regardless of a local file
        if config.Debug:
            print(f"Getting Azure resources via {Azure_Resource_URL}")
        page = requests.get(Azure_Resource_URL)
        if config.Debug:
            print("Raw html")
            print(page.text)
        with open(Fname, "w") as fp:
            fp.write(page.text)

    if src == "file":
        file_is_local = True

    with open(Fname) as fp:
        soup = BeautifulSoup(fp, "html.parser")

    tbody_tag = soup.tbody
    #   trs = tbodies[0].find_all('tr')
    trs = tbody_tag.find_all("tr")
    for tr in trs:
        tds = tr.find_all("td")
        priv = tds[2].contents
        pub = tds[3].contents
        if config.Debug:
            print("before:")
            print(priv)
            print(pub)
        lpriv = len(priv)
        if lpriv > 1:
            tmpl = list()
            for i in priv:
                if not isinstance(i, Tag):
                    tmpl.append(str(i).strip())
            priv = tmpl
            tmpl = list()
            for i in pub:
                if not isinstance(i, Tag):
                    tmpl.append(str(i).strip())
            pub = tmpl
        if config.Debug:
            print("after:")
            print(priv)
            print(pub)
        for priv_name, pub_name in zip(priv, pub):
            if config.Debug:
                print(f"Private name: {priv_name}")
                print(f"Public name: {pub_name}")
            for key in mappings.keys():
                if key in priv_name or key in pub_name:
                    for new in mappings[key]:
                        priv = priv_name.replace(key, new)
                        priv_name = priv
                        pub = pub_name.replace(key, new)
                        pub_name = pub
            priv2pub[priv_name] = pub_name
    # Serializing json
    json_obj = json.dumps(priv2pub, indent=4)
    return json_obj


"""
    with open(JsonFile, "w") as outfile:
        outfile.write(json_obj)
"""


# Get things going... Initialize the BAM connection and set a few variables.
def dns_init(flip):
    view_id = api.bam_init(flip)
    cwd = os.getcwd()
    home_dir = os.path.expanduser("~")
    config.Root = f"{home_dir}/src/azure/azuredns"
    config.Root = f"{home_dir}/src/Azure/az-dns"
    config.Path = f"{config.Root}/src/azuredns"
    config.ViewID = view_id
