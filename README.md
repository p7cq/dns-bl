### dns-bl - DNS Response Policy Zone file generator

___

Create DNS RPZ file using various block list URLs as source. 

Works with Shalla's ```shallalist.tar.gz``` and with various sources presenting block lists either as a domain

```
bad.host.com
worst.host.com
...
```
or as a hosts file:
```
127.0.0.1 bad.host.com
0.0.0.0 worst.host.com
...
```