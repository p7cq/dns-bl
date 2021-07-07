### dns-bl - DNS Response Policy Zone file generator

___

Create DNS RPZ file using various block list URLs as source. 

Works with Shalla's ```shallalist.tar.gz``` and with various sources presenting block lists either as a domain

```
host1.example.org
host2.example.org
...
```
or as a hosts file:
```
127.0.0.1 host3.example.org
0.0.0.0 host4.example.org
...
```
