import re
from pprint import pprint
from os.path import exists

import click
from click import Context, argument, group, option, pass_context

from azuredns import config, util, api

SUPPORTED_SRCS = ["bc-yaml", "local", "yaml", "bc", "bam", "bluecat"]


def validate_fqdn(ctx, param, value):
    if value == "rights":
        return validate_value(ctx, param, value)
    else:
        pattern = "[\w]+(\.[\w]+)+"
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
@pass_context
def run(ctx: Context, silent, verbose):
    """CLI interface to both BAM and Azure DNS"""
    ctx.obj = dict()
    ctx.obj["SILENT"] = silent
    ctx.obj["DEBUG"] = verbose
    config.Silent = silent
    config.Debug = verbose

    if verbose:
        click.echo(f"action: {ctx.invoked_subcommand}")
    util.dns_init()

# common options to share between subcommands
# the zone or leaf to act upon
fqdn = argument(
    "fqdn",
    type=click.STRING,
    default='bozo.the.clown.ca',
    required=True,
    callback=validate_fqdn,
)

addr = argument(
    "addr",
    type=click.STRING,
    default="10.141.141.141",
    callback=validate_ip,
)

value = argument(
    "value",
    type=click.STRING,
    default="zones",
)

# @run commands: add, delete, list, modify, view,

@run.command()
@pass_context
@fqdn
@addr
def test(ctx, fqdn, addr):
    print(fqdn, addr)
    rrs = util.get_merged_bc_azure_zone(fqdn)
    for rr,val in rrs.items():
        print(rr, val)
    return
    util.get_cname_rrs()

@run.command()
@pass_context
@fqdn
@addr
def hrids(ctx, fqdn, addr):
    ids = util.get_hr_nums()
    print(ids)
    print(fqdn, addr)

# list subcommand

@run.command()
@pass_context
@fqdn
@option(
    "-t",
    "--target",
    "target",
    default="test-yaml",
    type=click.STRING,
    help="Where the data is to come from or to",
)

def list(ctx, target, fqdn):
    if config.Debug:
        print(f"fqdn: {fqdn} target: {target}")
    if target == "bc" or target == "bluecat":
        if util.is_leaf(fqdn):
            rrs = util.get_leaf_bc_azure_zone(fqdn)
            print(rrs)
        else:
            data = util.get_merged_bc_azure_zone(fqdn)
            print(f'Merged content of {fqdn}')
            zdata = util.fmt(fqdn, data)
            for leaf_fqdn in zdata:
                print(leaf_fqdn, zdata[leaf_fqdn]) 
    elif target == "bc-yaml":
        toks = fqdn.split(".")
        hrids = util.get_active_hrids()
        if toks[0] not in hrids:
            print("All BC Yaml files are leaf zones starting with one of:")
            print(hrids)
            return
        fname = f'{config.Root}/bc-zones/{fqdn}.yaml'
        if exists(fname):
            data = util.get_yaml_file(fname)
            print(f'Local BC Yaml for: {fqdn}')
            pprint(data)
    elif target == "qa-yaml":
        fname = f'{config.Root}/qa-zones/{fqdn}.yaml'
        if exists(fname):
            data = util.get_yaml_file(fname)
            print(f'Local QA Yaml for: {fqdn}')
            pprint(data)
        else:
            print(f'No QA exists yet for zone: {fqdn}')
    elif target == 'prod-yaml' or target == 'prd-yaml':
        fname = f'{config.Root}/prod-zones/{fqdn}.yaml'
        if exists(fname):
            data = util.get_yaml_file(fname)
            print(f'Local PROD Yaml for: {fqdn}')
            pprint(data)
        else:
            print(f'No PROD data for {fqdn} exists')
    elif target == 'test-yaml' and fqdn == 'azure.zones':
        for azone in util.get_azure_zones():
            print(azone)

@run.command()
@pass_context
@value
@option(
    "-t",
    "--target",
    "target",
    default="prod-yaml",
    type=click.STRING,
    help="Where the data is to come from or to",
)
def zones(ctx, target, value):
    if value == "zones":
        zones = util.get_azure_zones()
        for zone in zones:
            print(zone)
    elif value == "leafs" or value == "leaves":
        leafs = util.get_leaf_zones()
        for leaf in leafs:
            print(leaf)
    elif value == "tlds":
        tlds = util.get_tlds(util.get_azure_zones())
        for tld in tlds:
            print(tld)

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
        print(f"zone: {fqdn}")
        print(f"src: {source}")
        print(f"dst: {destination}")
    if source == "bc" and destination == "bc-yaml":
        leafs = util.get_leaf_names(fqdn)
        for leaf in leafs:
            leaf_zone = f'{leaf}.{fqdn}'
            rrs = util.get_leaf_bc_azure_zone(leaf_zone)
            yamlf = f"{config.Root}/bc-zones/{leaf_zone}.yaml"
            util.update_yaml_zone_file(yamlf, rrs)
    elif source == "bc-yaml" and destination == "yaml":
        (qa_norm_yaml, prod_norm_yaml) = util.normalize(fqdn)
        if config.Debug:
            print(f'Zone: {fqdn}')
            print('QA YAML')
            print(qa_norm_yaml)
            print('PRD YAML')
            print(prod_norm_yaml)
        if len(qa_norm_yaml):
            yamlf = f"{config.Root}/qa-zones/{fqdn}.yaml"
            util.update_yaml_zone_file(yamlf, qa_norm_yaml)
        else:
            print(f'No QA A records yet for {value}')
        if len(prod_norm_yaml):
            yamlf = f"{config.Root}/prod-zones/{fqdn}.yaml"
            util.update_yaml_zone_file(yamlf, prod_norm_yaml)
        else:
            print(f'No Prod A records yet for {fqdn}')
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
@fqdn
@addr
def add(ctx, fqdn, addr):
    """Add an Azure A record"""
    if ctx.obj["DEBUG"]:
        click.echo(f"    fqdn: {fqdn} value: {addr}\n")
    util.add_A_rr(fqdn, addr)

@run.command()
@pass_context
@fqdn
@addr
def delete(ctx, fqdn, addr):
    """Delete an Azure A record"""
    if ctx.obj["DEBUG"]:
        click.echo(f"    fqdn: {fqdn} value: {addr}\n")
    util.del_A_rr(fqdn, addr)

@run.command()
@pass_context
@option(
    "-d",
    "--deploy",
    "deployable",
    is_flag=True,
    help="Set to make the zone is to be deployable"
)
@fqdn
def modify(ctx, deployable, fqdn):
    if deployable:
        props = api.Z_Props_Deployable
    else:
        props = api.Z_Props_Not_Deployable
    util.modify_zone(fqdn, props)

if __name__ == "__run__":
    run()
