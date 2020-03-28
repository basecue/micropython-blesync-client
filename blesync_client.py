from collections import namedtuple

from micropython import const
import bluetooth

import blesync
import struct

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x3)
_ADV_TYPE_UUID32_COMPLETE = const(0x5)
_ADV_TYPE_UUID128_COMPLETE = const(0x7)
_ADV_TYPE_UUID16_MORE = const(0x2)
_ADV_TYPE_UUID32_MORE = const(0x4)
_ADV_TYPE_UUID128_MORE = const(0x6)
_ADV_TYPE_APPEARANCE = const(0x19)


# 0x00 - ADV_IND - connectable and scannable
# undirected
# advertising
# 0x01 - ADV_DIRECT_IND - connectable
# directed
# advertising
# 0x02 - ADV_SCAN_IND - scannable
# undirected
# advertising
# 0x03 - ADV_NONCONN_IND - non - connectable
# undirected
# advertising
# 0x04 - SCAN_RSP - scan
# response


def decode_field(payload, adv_type):
    i = 0
    result = []
    while i + 1 < len(payload):
        if payload[i + 1] == adv_type:
            result.append(payload[i + 2: i + payload[i] + 1])
        i += 1 + payload[i]
    return result


def decode_name(payload):
    n = decode_field(payload, _ADV_TYPE_NAME)
    return str(n[0], "utf-8") if n else ""


def decode_services(payload):
    services = []
    for u in decode_field(payload, _ADV_TYPE_UUID16_COMPLETE):
        services.append(bluetooth.UUID(struct.unpack("<h", u)[0]))
    for u in decode_field(payload, _ADV_TYPE_UUID32_COMPLETE):
        services.append(bluetooth.UUID(struct.unpack("<d", u)[0]))
    for u in decode_field(payload, _ADV_TYPE_UUID128_COMPLETE):
        services.append(bluetooth.UUID(u))
    return services


BLEDevice = namedtuple(
    'BLEDevice',
    ('addr_type', 'addr', 'name', 'connectable', 'rssi', 'services')
)

BLEService = namedtuple(
    'BLEService',
    ('start_handle', 'end_handle', 'uuid')
)


class BLEClient:
    def __init__(self, *service_classes):
        self._service_classes = service_classes

    def scan(self):
        blesync.active(True)
        for addr_type, addr, connectable, rssi, adv_data in blesync.gap_scan(
            2000,
            30000,
            30000
        ):
            services = decode_services(adv_data)
            name = decode_name(adv_data)
            # addr buffer is owned by caller so need to copy it.
            addr_copy = bytes(addr)
            yield BLEDevice(
                addr_type=addr_type,
                addr=addr_copy,
                name=name,
                connectable=connectable,
                rssi=rssi,
                services=services
            )

    def connect(self, addr_type, addr):
        blesync.active(True)
        conn_handle = blesync.gap_connect(addr_type, addr)

        ret = {}
        for start_handle, end_handle, uuid in blesync.gattc_discover_services(
            conn_handle
        ):
            for service_class in self._service_classes:
                try:
                    service = service_class(uuid, conn_handle)
                except ValueError:
                    continue

                ret[uuid] = service
        return ret


    # def discover_characteristics(self, service: BLEService, callback):
    #     self._assert_active()
    #
    #     # TODO consider list
    #     self._discover_characteristics_callback[service] = callback
    #     _ble.gattc_discover_characteristics(
    #         service.conn_handle, service.start_handle, service.end_handle
    #     )

    # def disconnect(self, connection: BLEConnection, callback):
    #     self._assert_active()
    #     self._disconnect_callback[connection] = callback
    #     _ble.gap_disconnect(connection.conn_handle)
