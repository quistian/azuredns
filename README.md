AzureCLI interface:  Allows one to probe various RRs from BC, Azure etc.

# First steps

$ cd ~/src/Azure/az-dns
$ . ./octo-venv/bin/activate
(octo-venv) doghaus.eis.utoronto.ca$

E.g.

commands: LIST
Lists the contents of a zone, the default being BlueCat

(octo-venv) doghaus.eis.utoronto.ca$ azurecli  list --target bc 278.privatelink.openai.azure.com
{'n278_test': {'type': 'A', 'values': ['10.140.217.168']},
 'q278-test': {'type': 'A', 'values': ['10.141.1.178']},
 'q278_cfrb': {'type': 'A', 'values': ['10.141.10.10']},
 'q278_colt45_rr': {'type': 'A', 'values': ['10.141.4.5']},
 'q278_gogo': {'type': 'A', 'values': ['10.141.114.114']},
 'q278_hugo': {'type': 'A', 'values': ['10.141.4.4']},
 'q278_rps': {'type': 'A', 'values': ['10.141.141.141']},
 'q278_summer_rain': {'type': 'A', 'values': ['10.141.100.100']},
 'q278_test_rr': {'type': 'A', 'values': ['10.141.111.222']},
 'q278_the_beast': {'type': 'A', 'values': ['10.141.6.6']},
 'q278_winter_snow': {'type': 'A', 'values': ['10.141.10.10']}}

(octo-venv) doghaus.eis.utoronto.ca$ azurecli --help
Usage: azurecli [OPTIONS] COMMAND [ARGS]...

  CLI interface to both BAM and Azure DNS

Options:
  -s, --silent                Minimize the output from commands. Silence is
                              golden
  -v, -d, --verbose, --debug  Show what is going on for debugging purposes
  --help                      Show this message and exit.

Commands:
  add       Add an Azure A record
  delete    Delete an Azure A record
  modify    Modify an Azure A record
  hrids
  dump
  list
  mod-zone
  sync
  test
  zones

HRIDS... lists all potential Department IDs

(octo-venv) doghaus.eis.utoronto.ca$ azurecli hrids
[190, 49, 218, 225, 399, 224, 235, 20, 12, 219, 256, 275, 50, 45, 18, 23, 129, 46, 66, 187, 244, 55, 280, 83, 29, 67, 63, 58, 241, 527, 74, 28, 519, 69, 276, 502, 56, 62, 160, 392, 157, 319, 558, 612, 234, 44, 2, 31, 105, 123, 19, 30, 70, 25, 43, 94, 96, 89, 131, 54, 78, 68, 60, 53, 77, 52, 124, 41, 95, 57, 73, 61, 81, 71, 125, 75, 92, 59, 79, 76, 118, 109, 514, 42, 84, 88, 86, 115, 51, 36, 132, 121, 103, 38, 91, 127, 117, 111, 90, 40, 1, 3, 48, 64, 65, 14, 13, 93, 26, 102, 574, 169, 239, 278, 227, 213, 159, 192, 251, 173, 206, 246, 152, 248, 144, 148, 197, 167, 168, 199, 136, 228, 214, 238, 196, 221, 138, 139, 170, 229, 200, 147, 249, 242, 216, 176, 302, 154, 184, 247, 223, 180, 188, 189, 172, 182, 174, 178, 134, 226, 185, 340, 179, 183, 171, 237, 164, 145, 220, 526, 332, 343, 326, 327, 264, 333, 347, 324, 310, 285, 350, 304, 323, 268, 272, 337, 258, 279, 311, 287, 335, 342, 309, 290, 305, 321, 315, 348, 328, 378, 307, 295, 296, 265, 284, 331, 269, 330, 569, 255, 320, 277, 316, 282, 259, 341, 329, 308, 261, 291, 314, 262, 338, 281, 317, 271, 283, 369, 409, 408, 419, 427, 437, 398, 402, 404, 430, 416, 381, 355, 395, 363, 421, 372, 364, 356, 365, 400, 407, 425, 424, 360, 361, 354, 367, 382, 373, 438, 428, 422, 471, 359, 470, 456, 410, 405, 401, 432, 439, 368, 484, 580, 507, 539, 522, 504, 578, 517, 490, 556, 503, 498, 560, 532, 559, 506, 529, 518, 577, 512, 586, 488, 479, 583, 542, 546, 581, 561, 571, 568, 552, 587, 535, 520, 540, 572, 508, 499, 494, 573, 550, 481, 533, 505, 500, 564, 547, 497, 509, 496, 483, 495, 501, 476, 485, 493, 557, 576, 579, 551, 618, 607, 594, 592, 593, 590, 602, 597, 588, 318, 606, 87, 106, 591, 140, 598, 604, 534, 457, 37, 35, 600, 611, 613, 614, 616, 33, 621, 615, 619, 617, 620, 622, 623, 624, 626, 670, 34, 85, 32, 24, 155, 379, 474, 352, 370, 146, 207, 236, 477, 510, 668, 637, 634, 644, 638, 639, 640, 641, 659, 288, 647, 645, 650, 669, 675, 366, 186, 322, 297, 298, 383, 312, 252, 104, 177, 211, 491, 489, 181, 292, 208, 582, 97, 253, 153, 380, 629, 631, 632, 630, 633, 658, 666, 664, 665, 635, 166, 135, 475, 541, 133, 293, 263, 289, 301, 385, 231, 584, 267, 27, 390, 299, 325, 158, 273, 150, 126, 313, 528, 376, 99, 549, 113, 375, 371, 162, 98, 480, 538, 260, 589, 396, 434, 570, 436, 601, 394, 245, 128, 286, 515, 530, 201, 482, 212, 562, 486, 524, 513, 406, 418, 478, 22, 204, 608, 346, 423, 548, 585, 377, 198, 110, 553, 487, 563, 254, 232, 389, 120, 537, 610, 605, 627, 625, 628, 525, 636, 599, 230, 643, 511, 646, 661, 663, 676, 677, 678, 679, 680, 682, 683, 651, 681, 671, 684, 653, 21, 266, 303, 349, 393, 544, 545, 575, 609, 642, 648, 649, 652, 654, 655, 656, 657, 660, 662, 667, 672, 673, 674, 685, 686, 193, 603, 420, 130, 433, 543, 536, 250]

DUMP... dumps the entire RR database

(octo-venv) doghaus.eis.utoronto.ca$ azurecli dump azure.com | sed 10q
{'name': 'Q569_test', 'id': 2865802, 'type': 'GenericRecord', 'properties': {'comments': 'A solo A Resource Record', 'absoluteName': 'Q569_test.569.canadacentral.privatelink.afs.azure.net', 'rdata': '10.141.83.205', 'type': 'A', 'parentId': 2865024, 'parentType': 'Zone'}}
{'name': 'Q031_test', 'id': 2865803, 'type': 'GenericRecord', 'properties': {'comments': 'A solo A Resource Record', 'absoluteName': 'Q031_test.031.canadacentral.privatelink.afs.azure.net', 'rdata': '10.141.122.33', 'type': 'A', 'parentId': 2865025, 'parentType': 'Zone'}}
{'name': 'Q301_test', 'id': 2865804, 'type': 'GenericRecord', 'properties': {'comments': 'A solo A Resource Record', 'absoluteName': 'Q301_test.301.canadacentral.privatelink.afs.azure.net', 'rdata': '10.141.234.44', 'type': 'A', 'parentId': 2865026, 'parentType': 'Zone'}}
{'name': 'Q278_test', 'id': 2865805, 'type': 'GenericRecord', 'properties': {'comments': 'A solo A Resource Record', 'absoluteName': 'Q278_test.278.canadacentral.privatelink.afs.azure.net', 'rdata': '10.141.89.200', 'type': 'A', 'parentId': 2865027, 'parentType': 'Zone'}}
{'name': 'Q228_test', 'id': 2865806, 'type': 'GenericRecord', 'properties': {'comments': 'A solo A Resource Record', 'absoluteName': 'Q228_test.228.canadacentral.privatelink.afs.azure.net', 'rdata': '10.141.144.142', 'type': 'A', 'parentId': 2865028, 'parentType': 'Zone'}}
{'name': 'Q234_test', 'id': 2865807, 'type': 'GenericRecord', 'properties': {'comments': 'A solo A Resource Record', 'absoluteName': 'Q234_test.234.canadacentral.privatelink.afs.azure.net', 'rdata': '10.141.107.117', 'type': 'A', 'parentId': 2865029, 'parentType': 'Zone'}}
{'name': 'Q277_test', 'id': 2865808, 'type': 'GenericRecord', 'properties': {'comments': 'A solo A Resource Record', 'absoluteName': 'Q277_test.277.canadacentral.privatelink.afs.azure.net', 'rdata': '10.141.155.241', 'type': 'A', 'parentId': 2865030, 'parentType': 'Zone'}}
{'name': 'Q574_test', 'id': 2865809, 'type': 'GenericRecord', 'properties': {'comments': 'A solo A Resource Record', 'absoluteName': 'Q574_test.574.canadacentral.privatelink.afs.azure.net', 'rdata': '10.141.126.84', 'type': 'A', 'parentId': 2865031, 'parentType': 'Zone'}}
{'name': 'Q031_test', 'id': 2865811, 'type': 'GenericRecord', 'properties': {'comments': 'A solo A Resource Record', 'absoluteName': 'Q031_test.031.canadacentral.privatelink.azurecr.io', 'rdata': '10.141.146.150', 'type': 'A', 'parentId': 2865037, 'parentType': 'Zone'}}
{'name': 'Q278_test', 'id': 2865813, 'type': 'GenericRecord', 'properties': {'comments': 'A solo A Resource Record', 'absoluteName': 'Q278_test.278.canadacentral.privatelink.azurecr.io', 'rdata': '10.141.179.58', 'type': 'A', 'parentId': 2865039, 'parentType': 'Zone'}}


TEST.... Shows the merged data from a zone

(octo-venv) doghaus.eis.utoronto.ca$ azurecli test privatelink.openai.azure.com
privatelink.openai.azure.com 10.141.141.141
Q569_test {'type': 'A', 'values': ['10.141.147.144']}
n569_test {'type': 'A', 'values': ['10.140.28.214']}
q569_abcd {'type': 'A', 'values': ['10.141.12.14']}
q569_rps_test {'type': 'A', 'values': ['10.141.55.66']}
Q031_test {'type': 'A', 'values': ['10.141.96.222']}
q301 {'type': 'A', 'values': ['10.141.22.22']}
n301_hotdog {'type': 'A', 'values': ['10.140.44.55']}
n278_test {'type': 'A', 'values': ['10.140.217.168']}
q278-test {'type': 'A', 'values': ['10.141.1.178']}
q278_rps {'type': 'A', 'values': ['10.141.141.141']}
q278_gogo {'type': 'A', 'values': ['10.141.114.114']}
q278_hugo {'type': 'A', 'values': ['10.141.4.4']}
q278_winter_snow {'type': 'A', 'values': ['10.141.10.10']}
q278_summer_rain {'type': 'A', 'values': ['10.141.100.100']}
q278_test_rr {'type': 'A', 'values': ['10.141.111.222']}
q278_colt45_rr {'type': 'A', 'values': ['10.141.4.5']}
q278_the_beast {'type': 'A', 'values': ['10.141.6.6']}
q278_cfrb {'type': 'A', 'values': ['10.141.10.10']}
n228_test {'type': 'A', 'values': ['10.140.164.98']}
Q228_ttc {'type': 'A', 'values': ['10.141.47.200']}
n234_test {'type': 'A', 'values': ['10.140.94.76']}
Q277_test {'type': 'A', 'values': ['10.141.204.86']}
ab123 {'type': 'A', 'values': ['10.141.0.1']}
n277_test {'type': 'A', 'values': ['10.140.130.222']}


ZONES.... Shows zones at a certain level

$ azurecli zones -t bc tlds
net
io
com
ms
kubernetesconfiguration
test

# Leaf Zones from BC

(octo-venv) doghaus.eis.utoronto.ca$ azurecli zones -t bc  leaf | sed 10q
569.canadacentral.privatelink.afs.azure.net
031.canadacentral.privatelink.afs.azure.net
301.canadacentral.privatelink.afs.azure.net
278.canadacentral.privatelink.afs.azure.net
228.canadacentral.privatelink.afs.azure.net
234.canadacentral.privatelink.afs.azure.net
277.canadacentral.privatelink.afs.azure.net
574.canadacentral.privatelink.afs.azure.net
569.canadacentral.privatelink.azurecr.io
031.canadacentral.privatelink.azurecr.io

# Private Zones from BC
(octo-venv) doghaus.eis.utoronto.ca$ azurecli zones -t bc priv | sed 12q
canadacentral.privatelink.afs.azure.net
canadacentral.privatelink.azurecr.io
canadaeast.privatelink.afs.azure.net
privatelink-global.wvd.microsoft.com
privatelink.adf.azure.com
privatelink.agentsvc.azure-automation.net
privatelink.analysis.windows.net
privatelink.api.azureml.ms
privatelink.azconfig.io
privatelink.azure-api.net
privatelink.azure-automation.net
privatelink.azure-devices-provisioning.net

# Private Zones from a file
(octo-venv) doghaus.eis.utoronto.ca$ azurecli zones -t file  priv | sed 12q
canadacentral.privatelink.afs.azure.net
canadacentral.privatelink.azurecr.io
canadaeast.privatelink.afs.azure.net
privatelink-global.wvd.microsoft.com
privatelink.adf.azure.com
privatelink.agentsvc.azure-automation.net
privatelink.analysis.windows.net
privatelink.api.azureml.ms
privatelink.azconfig.io
privatelink.azure-api.net
privatelink.azure-automation.net
privatelink.azure-devices-provisioning.net




----------------------------
PowerDNS Docker

The powerdns server is running on mirror.eis.utoronto.ca under Docker.

The compose file is at:

$ pwd
/var/lib/docker/pdns

$ cat docker-compose.yml
version: "3.9"  # optional since v1.27.0

volumes:
  powerdns-db-data:
    name: powerdns-db-data

services:
  db:
    image: mariadb:10.1
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: l3tmein
    volumes:
      - powerdns-db-data:/var/lib/mysql
  powerdns:
    image: psitrax/powerdns
    ports:
      - "5353:53/tcp"
      - "5353:53/udp"
      - "8081:8081"
    environment:
      MYSQL_HOST: db
      MYSQL_PORT: 3306
      MYSQL_USER: root
      MYSQL_PASS: l3tmein
    depends_on:
      - db
    command: --api=yes --api-key=eaHuezahYeebie5joothie7v --loglevel=9 --webserver=yes --webserver-address=0.0.0.0 --webserver-allow-from=128.100.102.0/23 --webserver-password=eaHuezahYeebie5joothie7v --webserver-port=8081


To manage the Docker PowerDNS image on mirror:

a. First time, to create and start the images:

$ cd /var/lib/docker/pdns
# docker compose up

b. Subsequent times to maintain data from last access:

# docker compose start / stop / restart

# docker compose stop
[+] Stopping 2/2
 ✔ Container pdns-powerdns-1  Stopped                                                                                                                                                                                1.4s
 ✔ Container pdns-db-1        Stopped                                                                                                                                                                                2.8s
root@mirror:/var/lib/docker/pdns# docker compose restart
[+] Restarting 2/2
 ✔ Container pdns-db-1        Started                                                                                                                                                                                2.4s
 ✔ Container pdns-powerdns-1  Started


c. To view status of pdns container:

# docker compose ls
NAME                STATUS              CONFIG FILES
pdns                running(2)          /var/lib/docker/pdns/docker-compose.yml

# docker compose images
CONTAINER           REPOSITORY          TAG                 IMAGE ID            SIZE
pdns-db-1           mariadb             10.1                895244a22f37        352MB
pdns-powerdns-1     psitrax/powerdns    latest              720c44942097        63.7MB

# docker compose ps
NAME              IMAGE              COMMAND                  SERVICE    CREATED        STATUS         PORTS
pdns-db-1         mariadb:10.1       "docker-entrypoint.s…"   db         21 hours ago   Up 2 minutes   0.0.0.0:3306->3306/tcp, :::3306->3306/tcp
pdns-powerdns-1   psitrax/powerdns   "/entrypoint.sh --ap…"   powerdns   21 hours ago   Up 2 minutes   0.0.0.0:8081->8081/tcp, :::8081->8081/tcp, 0.0.0.0:5353->53/tcp, 0.0.0.0:5353->53/udp, :::5353->53/tcp, :::5353->53/udp


This docker container uses Volume to aid in storing data, as docker normally is
ephemeral. See: the following in the docker compose file:

volumes:
  powerdns-db-data:
    name: powerdns-db-data

Which is then referenced here:

db:
    image: mariadb:10.1
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: l3tmein
    volumes:
      - powerdns-db-data:/var/lib/mysql

See:

# docker volume ls
DRIVER    VOLUME NAME
local     powerdns-db-data

# docker volume inspect powerdns-db-data
[
    {
        "CreatedAt": "2024-02-07T16:19:02-05:00",
        "Driver": "local",
        "Labels": {
            "com.docker.compose.project": "pdns",
            "com.docker.compose.version": "2.24.1",
            "com.docker.compose.volume": "powerdns-db-data"
        },
        "Mountpoint": "/var/lib/docker/volumes/powerdns-db-data/_data",
        "Name": "powerdns-db-data",
        "Options": null,
        "Scope": "local"
    }
]

Wrote a script to backup the PowerDNS mysql data base:

# cat volume-backup.sh
#!/bin/sh

PATH=/bin:/usr/bin

CONTAINER="pdns-db-1"
dirname=${PWD##*/}

docker compose pause

for nv in `docker volume ls -q`
do
	f="${nv}_${dirname}"
	echo -n "Backing up $f ... "
	docker run \
		--rm \
		-v $nv:/data \
		-v $PWD:/backup \
		ubuntu \
		tar cvf /backup/$f.tar -C /data .
	echo "done"
done

docker compose unpause


And there's a restore template one as well, which I have not tried out yet:

#!/bin/bash

dirname=${PWD##*/}
for f in `ls *.tar.bz2`
do
  nv="${dirname}_${f%.tar.bz2}"
  echo -n "Restoring $nv ..."
  docker run -it --rm \
    -v $nv:/data -v $PWD:/backup alpine \
    sh -c "rm -rf /data/* /data/..?* /data/.[!.]* ; tar -C /data/ -xjf /backup/$f"
  echo "done"
done


