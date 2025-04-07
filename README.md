A standalone Python + BASH scripts that creates a DNS Response Policy Zone file for ISC's BIND DNS server using various block lists as source. Works with sources presenting block lists as text files, either in *FQDN* form

```
host1.example.org
host2.example.org
```

or in *hosts* form

```
127.0.0.1 host3.example.org
0.0.0.0 host4.example.org
```

> **_Note:_** Prior configuration of the DNS server is needed before making use of this script. Also, you may need other services/scripts for automating updates and performing zone reload checks along with some sort of notification system in case zone reload fails. Additionally, you may not want to run this script on the DNS server itself.

## Installation

Clone repository and move ```dns-bl``` folder in a location on your system, e.g. ```/opt```.

### Configuration

Initial configuration is performed in two places: the RPZ file header and program's configuration file, `dns-bl.ini`.

#### RPZ file header

Edit zone header file in *DNSBL_HOME/var/db/zone_header.db* according to your DNS server configuration. Leave the ```*``` character in place in order for the script to update the zone serial number.
The zone serial can be generated in two forms: *incremental*, or *daily incremental* in format `YYYYMMDDnn`.

#### Configuration properties

Configuration properties are defined in `[global]` section in `dns-bl.ini`.

- `rpz_file` - the absolute path to BIND9's response policy zone file
- `redirect` - the redirect used
- `add_subdomains` - whether to include subdomains for each domain
- `whitelist_file_prefix` - prefix of file(s) containing domains to exclude from generated RPZ file
- `zone_serial_form` - DNS zone file serial format
- `skip_block_list_download` - whether to skip download of block lists
- `run_dir` - the absolute path to the download directory

```ini
[global]
rpz_file = /var/named/rpz.db
redirect = IN CNAME .
add_subdomains = no
whitelist_file_prefix = whitelist_
zone_serial_form = incremental
skip_block_list_download = false
run_dir = /run/dns-bl
```

##### Whitelists

Whitelists are text files located in *DNSBL_HOME/etc* and contain FQDN entries that will not be included in the RPZ file. For them to be picked up, each file name must start with `whitelist_`, as defined by `whitelist_file_prefix` option, e.g., `/opt/dns-bl/etc/whitelist_default` containing:

```
host5.example.org
host5.example.org
```

##### Zone serial

The format of the serial can be either incremental, or daily incremental and is controlled by `zone_serial_form` configuration parameter.
A serial form specified as `daily-incremental` will result in `2025032901` for the first zone update performed in that specific day. All subsequent updates made in the same day will increment the last two digits (`02`, `03`, `...`).
####  Source (block list) properties

There are 3 types of sources supported:

- ingested using `rsync`
- ingested using `http` or `https`
- ingested using `file`

Each source must output the content as text files in one of the two formats supported, *hosts* or *FQDN*.

Source properties are described in their own section:
- `[source_name]` - section delimiter; a **unique** name for the source
- `url` - location of the source
- `categories`  - type of source content
- `enabled` - whether to use this section as input for RPZ file

Add each source in its own section, each section name specified between `[` and `]` must be unique. Example:

```ini
[source/1]
url = rsync://ftp.example.org/blacklist
categories = publicite,malware
enabled = yes

[source/2]
url = https://source1.example.org/lists/malware.txt
categories = malware
enabled = yes

[source/3]
url = file:/my/block-list
categories = custom
enabled = yes
```

For *source/0*, it will download all `categories` listed, for the other types `categories` is only used internally as a label.

#### Running

Run the BASH script as the ```root``` user:

```bash
/opt/dns-bl/bin/run.sh
```

The generated `rpz.db` file will have the same owner and group as its parent directory, `/var/named`.

If the configuration file is missing, a file containing default values will be generated automatically.

