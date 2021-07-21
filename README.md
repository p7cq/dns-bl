### dns-bl - DNS Response Policy Zone file generator

___

A standalone Python + BASH scripts that creates a DNS Response Policy Zone (RPZ) file for ISC's BIND DNS server using various block lists as source. Works with Shalla with other sources presenting block lists either in *domain*


```
host1.example.org
host2.example.org
...
```

or in *hosts* file form

```
127.0.0.1 host3.example.org
0.0.0.0 host4.example.org
...
```

Note that prior configuration of the DNS server is needed before making use of this script. Also, you may need some additional scripts for automating updates and performing zone reload checks along with some sort of notification system in case zone reload fails.

___

#### Installation

Clone repository and move ```dns-bl``` folder in a location on your system, e.g. ```/opt```. The resulting location will be the program's *home* directory - ```DNSBL_HOME```. 

___


#### Configuration

Initial configuration is performed in two places: the RPZ zone file header and program's configuration file. Subsequent configuration should only be made in the configuration file.

##### RPZ zone file header

Edit zone header file in *DNSBL_HOME/var/db/zone_header.db* according to your DNS server configuration. Leave the ```*``` character in place in order for the script to update the serial number.

##### Configuration file: RPZ file location

Open the configuration file located at ```DNSBL_HOME/conf/dns-bl.ini``` and edit ```rpz_file``` parameter to point to the server's configured RPZ file location, e.g.:

```ini
[global]
rpz_file = /var/named/rpz.db
...
```

##### Configuration file: whitelists

For any domain you want excluded from RPZ, add each on a line in a text file having the prefix *whitelist_* in its name, e.g. *whitelist_default*:

```
host5.example.org
host6.example.org
```

You can leave the *redirect* and *add_subdomains* options unchanged.

##### Configuration file: source sections

Add each source in its own section, following the example found in ```dns-bl.ini``` file. The section name must be unique. Example:

```ini
[source/1]
url = https://source1.example.org/lists/lists.tar.gz
file_type = gzip
categories = category1,category2/subcategory1,category3
enabled = yes

[source/2]
url = https://source1.example.org/lists/malware.txt
file_type = text
categories = malware
enabled = yes

[source/3]
url = https://source3.example.org/lists/ads.txt
file_type = text
categories = ads
enabled = yes
```

Listing multiple ```categories``` is only needed for Shalla, due to the specific structure the lists are delivered in. Each category or subcategory follows the directory layout as extracted in the filesystem. Do take a look at this structure before deciding which categories to include. If you need all categories, list each directory and subdirectory in the archive, as in ```[source/1]``` above.

___

#### Running

Run the BASH script as the ```root``` user:

```bash
# $DNSBL_HOME/bin/run.sh
```

The generated ```rpz.db``` file will have the same owner and group as its parent directory.

