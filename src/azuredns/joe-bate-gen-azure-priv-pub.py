#!/usr/bin/env python3

import requests
import bs4
import json

URL = 'https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-dns#azure-services-dns-zone-configuration'
req = requests.get(URL)
req.status_code
soup = bs4.BeautifulSoup(req.text, 'html.parser')

def get_priv_pub_json():
    dns_zones = []
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        for row in rows[2:]:
            cells = row.find_all('td')
            resource_type = cells[0].text.strip()
            sub_resource = cells[1].text.strip().split("  ")
            private_dns_zones = cells[2].text.strip().split("  ")
            public_dns_zones = cells[3].text.strip().split("  ")
            dns_zones.append({ "resource_type": resource_type, "sub_resource": sub_resource, "private_dns_zones": private_dns_zones, "public_dns_zones": public_dns_zones })
    print(json.dumps(dns_zones, indent=4))

def main():
    get_priv_pub_json()

if __name__ == '__main__':
    main()
