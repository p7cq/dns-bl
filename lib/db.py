import sys

#
# read last used serial from db, increment it, and update serial db with current serial
#

def get_serial(db):
    try:
        f = open(db, 'r')
        serial = f.read()
    finally:
        f.close()

    if not serial:
        sys.exit("empty serial database")

    serial_current = str(int(serial) + 1)

    try:
        f = open(db, 'w+')
        f.write(serial_current)
    finally:
        f.close();
    return serial_current


def get_zone_header(db):
    try:
        f = open(db, 'r')
        header = f.read()
    finally:
        f.close()
    return header
