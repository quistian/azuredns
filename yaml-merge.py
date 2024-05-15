#!/usr/bin/env python

import os
import sys
import glob
import yaml

PathIn = '/home/russ/src/Azure/az-dns/leaf-zones'
PathOut = '/home/russ/src/Azure/az-dns/merged-zones'
Zones = ['privatelink.azurewebsites.net.', 'privatelink.vaultcore.azure.net.', 'privatelink.file.core.windows.net.']

def ls_matching(name):
    rrs = dict()

    flist = glob.glob(f'{PathIn}/*.{name}yaml')
    for fname in flist:
        with open(fname, 'r') as fd:
            data = yaml.safe_load(fd)
            rrs = rrs | data
    with open(f'{PathOut}/{name}yaml', 'w') as fd:
        yaml.dump(rrs, fd)

def main():
    dot = '.'

    n = len(sys.argv)
    pname = sys.argv[0]
    if n > 1:
        zone = sys.argv[1]
        toks = zone.split(dot)
        if toks[0] != 'privatelink':
            print(f'input private zone: {zone} is not legal')
            exit()
        elif toks[-1] == '':
            pass
        else:
            toks[-1] = toks[-1] + dot
            zone = dot.join(toks)
    else:
        print("Syntax: {pname} private.zone.")
        exit()
    print(f'Merging: {zone}')
    ls_matching(zone)

if __name__ == '__main__':
    main()
