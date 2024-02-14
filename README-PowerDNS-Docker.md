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


