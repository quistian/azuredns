#!/usr/bin/env python

import io

In = 'private-endpoint-dns.md'
Tab = '    '

Sep1 = ' </br> '
Sep2 = ' <br/> '
Sep3 = '</br> '
Sep4 = '<br/> '
Sep5 = '<br/>'
Sep6 = '</br>'

Sep7 = '<sup>1</sup>'

Seps1 = [Sep1, Sep2, Sep3, Sep4, Sep5, Sep6]
Seps2 = [Sep7]

Regions = ['canadacentral', 'canadaeast']

def main():
    with open(In) as fd:
        lines = fd.read().splitlines()
    print('{')
    for line in lines:
        if '>| ' in line and 'privatelink' in line:
            toks = line.split('|')
            n = len(toks)
            (priv, pub) = toks[-3:-1]
            if 'privatelink' not in priv:
                (priv, pub) = toks[-2:]
            if "cn " in priv or "us " in priv or 'usgov' in priv:
                continue
            if '/br' not in priv and 'br/' not in priv: 
                if 'regionName' in priv:
                    for region in Regions:
                        prnew = priv.replace('{regionName}', region)
                        pubnew = pub.replace('{regionName}', region)
                        print(f'{Tab}"{prnew.strip()}":  "{pubnew.strip()}",')
                else:
                    print(f'{Tab}"{priv.strip()}":  "{pub.strip()}",')
            else:
                for Sep in Seps1:
                    priv = priv.replace(Sep, " ")
                    pub = pub.replace(Sep, " ")
                for Sep in Seps2:
                    priv = priv.replace(Sep, "")
                    pub = pub.replace(Sep, "")
                privtoks = priv.strip().split(" ")
                pubtoks = pub.strip().split(" ")
                for pr, pb in zip(privtoks, pubtoks):
                    if 'regionName' in pr:
                        for region in Regions:
                            prnew = pr.replace('{regionName}', region)
                            pubnew = pb.replace('{regionName}', region)
                            print(f'{Tab}"{prnew.strip()}":  "{pubnew.strip()}",')
                    else:
                        print(f'{Tab}"{pr.strip()}":  "{pb.strip()}",')
    print('}')

if __name__ == '__main__':
    main()
