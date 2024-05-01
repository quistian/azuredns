import re

from os.path import exists
from pprint import pprint

import click
from click import Choice, Context, argument, group, option, pass_context

from azuredns import api, config, util

SUPPORTED_SRCS = ["bc-yaml", "local", "yaml", "bc", "bam", "bluecat"]
SUPPORTED_OBJS = ['zone', 'domain', 'rr', 'RR']
SUPPORTED_RR_TYPES = ['A', 'AAAA', 'TXT']

def validate_fqdn(ctx, param, value):
    if value == "rights":
        return validate_value(ctx, param, value)
    else:
        pattern = "[\w\-]+(\.[\w\-]+)+"
        if not re.match(pattern, value):
            raise click.BadParameter("Value must be in the form: hobo.utoronto.ca")
        return value


def validate_ip(ctx, param, value):
    if value == "rights":
        return validate_value(ctx, param, value)
    else:
        pattern = "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]"
        if not re.match(pattern, value):
            raise click.BadParameter("Value must be in the form: 1.2.3.4")
        return value


def validate_value(ctx, param, value):
    return value


@group()
@option(
    "-s",
    "--silent",
    is_flag=True,
    help="Minimize the output from commands. Silence is golden",
)
@option(
    "-v",
    "--verbose",
    "--debug",
    "-d",
    "verbose",
    is_flag=True,
    help="Show what is going on for debugging purposes",
)
@option(
        "-w",
        "--switch",
        "--flip",
        "flip",
        is_flag=True,
        help="Use the mirrored BAM flip",
)
@pass_context
def run(ctx: Context, silent, verbose, flip):
    """CLI interface to both BAM and Azure DNS"""
    ctx.obj = dict()
    ctx.obj["SILENT"] = silent
    ctx.obj["DEBUG"] = verbose
    config.Silent = silent
    config.Debug = verbose
    config.Flip = flip

    if verbose:
        click.echo(f"action: {ctx.invoked_subcommand}")
    util.dns_init(flip)

# common options to share between subcommands
# the zone or leaf to act upon

fqdn = argument(
    "fqdn",
    type=click.STRING,
    default="bozo.the.clown.ca",
    required=True,
    callback=validate_fqdn,
)

addr = argument(
    "addr",
    type=click.STRING,
    default="10.141.141.141",
    callback=validate_ip,
)

# generic string
value = argument(
    "value",
    type=click.STRING,
    default="zones",
)

dnsobj = argument(
        'dnsobj',
        type=click.STRING,
        required=True,
        default="A",
)

# @run commands: add, delete, list, modify, view,

@run.command()
@pass_context
@fqdn
@addr
def test(ctx, fqdn, addr):
    print(fqdn, addr)
    rrs = util.get_merged_bc_azure_zone(fqdn)
    for rr, val in rrs.items():
        print(rr, val)
    return
    util.get_cname_rrs()

@run.command()
@pass_context
@argument(
    "source",
    type=click.STRING,
    default="json",
)
def priv_pub_names(ctx, source):
    """ Generate current Azure Private to Public DNS mapping from Source: json, http soup """
    mapping = util.gen_azure_priv_pub_json(source)
    for key in mapping:
        print(f'{key},{mapping[key]}')

@run.command()
@pass_context
def hrids(ctx):
    ids = util.get_hrid_nums()
    for idx in ids:
        print(idx)

# list subcommand

@run.command()
@pass_context
@fqdn
@option(
    "-t",
    "--target",
    "target",
    default="bc",
    type=click.STRING,
    help="Source of contents of a leaf or merged zone, e.g. azure, yaml, bc",
)
def list(ctx, target, fqdn):
    """ List the contents of a leaf or merged zone """
    if config.Debug:
        print(f"fqdn: {fqdn} target: {target}")
    if target == "bc" or target == "bluecat":
        if util.is_leaf(fqdn):
            rrs = util.get_leaf_bc_azure_zone(fqdn)
            pprint(rrs)
        else:
            data = util.get_merged_bc_azure_zone(fqdn)
            print(f"Merged content of {fqdn}")
            zdata = util.fmt(fqdn, data)
            for leaf_fqdn in zdata:
                print(leaf_fqdn, zdata[leaf_fqdn])
    elif target == "leaf":
        toks = fqdn.split(".")
        hrids = util.get_active_hrids()
        if toks[0] not in hrids:
            print("All BC Yaml files are leaf zones starting with one of:")
            print(hrids)
            return
        fname = f"{config.Root}/zones/{fqdn}.yaml"
        if exists(fname):
            data = util.get_yaml_file(fname)
            print(f"Local BC Yaml for: {fqdn}")
            pprint(data)
    elif target == "qa-yaml":
        fname = f"{config.Root}/qa-zones/{fqdn}.yaml"
        if exists(fname):
            data = util.get_yaml_file(fname)
            print(f"Local QA Yaml for: {fqdn}")
            pprint(data)
        else:
            print(f"No QA exists yet for zone: {fqdn}")
    elif target == "prod-yaml" or target == "prd-yaml":
        fname = f"{config.Root}/prod-zones/{fqdn}.yaml"
        if exists(fname):
            data = util.get_yaml_file(fname)
            print(f"Local PROD Yaml for: {fqdn}")
            pprint(data)
        else:
            print(f"No PROD data for {fqdn} exists")
    elif target == "test-yaml" and fqdn == "azure.zones":
        for azone in util.get_azure_private_zones():
            print(azone)
    elif target == "cnames":
        util.gen_cname_rrs(fqdn)

@run.command()
@pass_context
@value
@option(
    "-t",
    "--target",
    "target",
    default="bc",
    type=click.STRING,
    help="Where the azure/resources zones list is from: bc, file, http etc.",
)
def zones(ctx, target, value):
    bc_args = ["bc", "bluecat"]
    leaf_args = ["leaf", "leaves", "leafs"]
    priv_args = ["priv", "private", "prv"]
    recurse_args = ["recurse", "bc-recurse", "bc-recursion"]
    zones = []

    if config.Debug:
        print(f"target: {target} value: {value}")

    if value == "tlds":
        if target in bc_args:
            zones = util.gen_tlds()
    elif value == "azure":
        zones = util.get_azure_private_zones("azure")
    elif target == "file" or target == "f":
        if value in priv_args:
            zones = util.get_azure_private_zones("file")
    elif target in bc_args:
        if value in leaf_args:
            zones = util.gen_bc_leaf_zones()
        if value in priv_args:
            zones = util.gen_bc_azure_zones()
    elif target in recurse_args:
        if value in leaf_args:
            util.recurse_2_leafs(config.ViewId)
        if value in priv_args:
            util.recurse(config.ViewId)
    for zone in zones:
        print(zone)

@run.command()
@fqdn
@pass_context
@option(
    "-s",
    "--src",
    "source",
    default="bc",
    type=click.STRING,
    help="Where the data is to come from",
)
@option(
    "-d",
    "--dst",
    "--dest",
    "destination",
    default="yaml",
    type=click.STRING,
    help="Where the data is to go to",
)

# there are 4 end points: bc -> bc-yaml -> yaml (qa + prod) -> azure


def sync(ctx, fqdn, source, destination):
    if config.Debug:
        print(f"zone: {fqdn} src: {source} dst: {destination}")
    if source == "bc" and destination == "leaf":
        leafs = util.get_leaf_names(fqdn)
        for leaf in leafs:
            leaf_zone = f"{leaf}.{fqdn}"
            rrs = util.get_leaf_bc_azure_zone(leaf_zone)
            yamlf = f"{config.Root}/leaf-zones/{leaf_zone}.yaml"
            util.update_yaml_zone_file(yamlf, rrs)
    elif source == "leaf" and destination == "merged":
        util.merge(fqdn)
    elif source == "merged" and destination == "normalized":
        util.canonical(fqdn)
    elif source == "yaml" and destination == "yaml":
        (qa_norm_yaml, prod_norm_yaml) = util.normalize(fqdn)
        if config.Debug:
            print(f"Zone: {fqdn}")
            print("QA YAML")
            print(qa_norm_yaml)
            print("PRD YAML")
            print(prod_norm_yaml)
        if len(qa_norm_yaml):
            yamlf = f"{config.Root}/qa-zones/{fqdn}.yaml"
            util.update_yaml_zone_file(yamlf, qa_norm_yaml)
        else:
            print(f"No QA A records yet for {value}")
        if len(prod_norm_yaml):
            yamlf = f"{config.Root}/prod-zones/{fqdn}.yaml"
            util.update_yaml_zone_file(yamlf, prod_norm_yaml)
        else:
            print(f"No Prod A records yet for {fqdn}")
    return
    yaml_zone = dict()
    bc_zone = dict()
    #    yaml_zone = util.get_yaml_zone(fqdn)
    if bc_zone == yaml_zone:
        print("no need to sync, zones are the same")
    else:
        print("syncing from BC to YAML")
        util.update_yaml_zone_file(fqdn, bc_zone)


@run.command()
@pass_context
@option('--zone', '--domain', '-z',
    required=False,
    default='bozo.int',
    callback=validate_fqdn,
    help='The name of the zone to be added',
)
@option('--rr', '--resource-record', '-r',
    required=False,
    nargs=3,
    default=('test.bozo.int', 'A', '1.2.3.4'),
    help='DNS resource record tuple: FQDN TYPE VALUE',
)
def add(ctx, zone, rr):
    """ Add an Azure zone or RR record """
    if ctx.obj["DEBUG"]:
        click.echo(f"add arguments: zone {zone} rr {rr}\n")
    (fqdn, rr_type, val) = rr
    if zone != 'bozo.int':
        util.add_zone_if_new(zone)
    elif rr_type in ["A", "AAAA", "TXT"] and fqdn != 'test.bozo.int':
        if rr_type == "A":
            util.add_A_rr(fqdn, val)
        else:
            print(f'RR of type {rr_type} is not yet supported') 

@run.command()
@pass_context
@option('--zone', '--domain', '-z',
    required=False,
    default='bozo.int',
    callback=validate_fqdn,
    help='The name of the zone to be deleted',
)
@option('--rr', '--resource-record', '-r',
    nargs=3,
    required=False,
    default=('A', 'test.bozo.int', '1.2.3.4'),
    help='DNS resource record tuple: FQDN TYPE VALUE to be deleted',
)
def delete(ctx, zone, rr):
    """Delete an Azure Zone or Resource record"""
    if ctx.obj["DEBUG"]:
        click.echo(f"zone: {zone} rr: {rr}\n")
    (fqdn, rr_type, val) = rr
    if zone != 'bozo.int':
        util.delete_zone(zone)
    elif rr_type in ["A", "AAAA", "TXT"] and fqdn != 'test.bozo.int':
        if rr_type == "A":
            util.del_A_rr(fqdn, val)

@run.command()
@pass_context
@fqdn
@addr
def modify(ctx, fqdn, addr):
    """ Modify an Azure A record """
    if ctx.obj["DEBUG"]:
        click.echo(f"Modifying fqdn: {fqdn} value: {addr}\n")
    util.mod_A_rr(fqdn, addr)

@run.command()
@pass_context
@option(
    "-d",
    "--deploy",
    "deployable",
    is_flag=True,
    help="Set to make the zone is to be deployable",
)
@fqdn
def mod_zone(ctx, deployable, fqdn):
    if deployable:
        props = api.Z_Props_Deployable
    else:
        props = api.Z_Props_Not_Deployable
    util.modify_zone(fqdn, props)

@run.command()
@pass_context
@argument(
    "zone",
    type=click.STRING,
    default=".",
    required=True,
)
def dump(ctx,zone):
    """ Dumps all zone data starting from a given starting point """
    if ctx.obj["DEBUG"]:
        click.echo(f"Dumping {zone}")
    util.dump_dns_data(zone)

@run.command()
@pass_context
@option(
    "-d",
    "--detail",
    "--debug",
    "--verbose",
    "detail",
    is_flag=True,
    help="When set should the number of subzones or rrs under each zone", 
)
@argument(
    "obj",
    type=click.STRING,
    default="azure",
    required=True,
)
def count(ctx,obj,detail):
    """ Counts the number of Azure Private zones: [azure] Leaf zones: [leaf] Resource records: [rrs] """
    if ctx.obj["DEBUG"]:
        click.echo(f"Counting {obj}")
    objs = util.count(obj,detail)
    for obj in objs:
        if detail:
            print(obj,objs[obj])
        else:
            print(obj)
    print(len(objs))

if __name__ == "__run__":
    run()
