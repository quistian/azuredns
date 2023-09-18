#!/usr/bin/env python

'''
Octo-DNS Multiplexer
'''

from octodns.cmds.args import ArgumentParser
from octodns.manager import Manager

def main():

    parser = ArgumentParser(description=__doc__.split('\n')[1])

    conf = './config/static.yaml'
    manager = Manager(conf)
    manager.sync(eligible_zones=['privatelink.openai.azure.com.'])

if __name__ == '__main__':
    main()
