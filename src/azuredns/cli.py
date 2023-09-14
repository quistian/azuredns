import re
from pprint import pprint

import click
from click import Context, argument, group, option, pass_context

from azuredns import config, util

SUPPORTED_SRCS = ["bc-yaml", "local", "yaml", "bc", "bam", "bluecat"]


def validate_fqdn(ctx, param, value):
    if value == "rights":
        return validate_value(ctx, param, value)
    else:
        pattern = "[\w]+(\.[\w]+)+"
        if not re.match(pattern, value):
            raise click.BadParameter("Value must be in the form: hobo.utoronto.ca")
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
fqdn = argument(
    "fqdn",
    type=click.STRING,
    #    required=True,
    #    callback=validate_fqdn,
)

value = argument(
    "value",
    type=click.STRING,
    default="defVAL",
    callback=validate_value,
)

SUPPORTED_RR_TYPES = ["A", "TXT", "defRR"]
rr_type = argument(
    "rr_type",
    type=click.Choice(SUPPORTED_RR_TYPES),
    default="defRR",
)

# @run commands: add, delete, list, modify, view,


@run.command()
@pass_context
@fqdn
def hrids(ctx, fqdn):
    ids = util.get_hr_nums()
    print(ids)
    print(fqdn)


# list subcommand
@run.command()
@pass_context
@value
@option(
    "-s",
    "--src",
    "source",
    default="yaml",
    type=click.STRING,
    help="Where the data is to come from",
)
@option(
    "-n",
    "--name",
    default="all.azure.resources",
    type=click.STRING,
    help="A Specific Zone, rather than all",
)
def list(ctx, value, source, name):
    if config.Debug:
        print(f"value: {value} src: {source} name: {name}")
    if value == "zone" or value == "resource":
        if source == "yaml":
            print("fetching yaml")
            zone = util.get_yaml_zone(name)
            pprint(zone)
        elif source == "bc" or source == "bluecat":
            zone = util.get_bc_azure_zone(name)
            pprint(zone)
    if value == "zones":
        zones = util.gen_azure_zones()
        for zone in zones:
            print(zone)
    if value == "leafs" or value == "leaves":
        leafs = util.gen_leaf_zones()
        for leaf in leafs:
            print(leaf)
    if value == "tlds":
        tlds = util.get_tlds(util.gen_azure_zones())
        for tld in tlds:
            print(tld)


@run.command()
@value
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

# there are 4 end points: bc -> bc-yaml -> yaml -> azure


def sync(ctx, value, source, destination):
    if config.Debug:
        print(f"zone: {value}")
        print(f"src: {source}")
        print(f"dst: {destination}")
    if source == "bc" and destination == "bc-yaml":
        data = util.get_bc_azure_zone(value)
        for leaf_zone in data:
            yamlf = f"{config.Root}/bc-zones/{leaf_zone}.yaml"
            util.update_yaml_zone_file(yamlf, data[leaf_zone])
    elif source == "bc-yaml" and destination == "yaml":
        (qa_norm_yaml, prod_norm_yaml) = util.normalize(value)
        yamlf = f"{config.Root}/qa-zones/{value}.yaml"
        util.update_yaml_zone_file(yamlf, qa_norm_yaml)
        yamlf = f"{config.Root}/prod-zones/{value}.yaml"
        util.update_yaml_zone_file(yamlf, prod_norm_yaml)
    return
    yaml_zone = dict()
    bc_zone = dict()
    #    yaml_zone = util.get_yaml_zone(value)
    if bc_zone == yaml_zone:
        print("no need to sync, zones are the same")
    else:
        print("syncing from BC to YAML")
        util.update_yaml_zone_file(value, bc_zone)


@run.command()
@pass_context
@fqdn
@rr_type
@value
def view(ctx, fqdn, rr_type, value):
    """View a RR or entity"""
    if ctx.obj["DEBUG"]:
        click.echo(f"    fqdn: {fqdn} rr_type: {rr_type} value: {value}\n")

    if rr_type == "defRR":
        util.view_RR(fqdn)
    elif value == "defVAL":
        util.view_rr(fqdn, rr_type)
    else:
        utile.view_rr(fqdn, rr_type, value)


if __name__ == "__run__":
    run()
