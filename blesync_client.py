from collections import namedtuple

import blesync
from micropython import const

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

def _split_data(payload):
    i = 0
    result = []
    data = memoryview(payload)
    len_data = len(data)
    while i < len_data:
        length = data[i]
        result.append(data[i + 1:i + 1 + length])
        i += length + 1
    return result


def parse_adv_data(payload):
    return {
        d[0]: d[1:]
        for d in _split_data(payload)
    }


def decode_adv_name(data):
    try:
        encoded_name = data[_ADV_TYPE_NAME]
    except KeyError:
        return ''
    else:
        return str(encoded_name, "utf-8")


def decode_adv_type(data):
    return data[_ADV_TYPE_FLAGS][0]


# def decode_services(payload):
#     services = []
#     for u in decode_field(payload, _ADV_TYPE_UUID16_COMPLETE):
#         services.append(bluetooth.UUID(struct.unpack("<h", u)[0]))
#     for u in decode_field(payload, _ADV_TYPE_UUID32_COMPLETE):
#         services.append(bluetooth.UUID(struct.unpack("<d", u)[0]))
#     for u in decode_field(payload, _ADV_TYPE_UUID128_COMPLETE):
#         services.append(bluetooth.UUID(u))
#     return services


BLEDevice = namedtuple(
    'BLEDevice',
    ('addr_type', 'addr', 'adv_name', 'adv_type_flags', 'rssi',)
)

BLEService = namedtuple(
    'BLEService',
    ('start_handle', 'end_handle', 'uuid')
)

_ADV_IND = const(0x00)
'''
Known as Advertising Indications (ADV_IND), where a peripheral device requests connection to any central device (i.e., not directed at a particular central device).
Example: A smart watch requesting connection to any central device.
'''
_ADV_DIRECT_IND = const(0x01)
'''
Similar to ADV_IND, yet the connection request is directed at a specific central device.
Example: A smart watch requesting connection to a specific central device.
'''
_ADV_SCAN_IND = const(0x02)
'''
Similar to ADV_NONCONN_IND, with the option additional information via scan responses.
Example: A warehouse pallet beacon allowing a central device to request additional information about the pallet. 
'''
_ADV_NONCONN_IND = const(0x03)
'''
Non connectable devices, advertising information to any listening device.
Example: Beacons in museums defining proximity to specific exhibits.
'''


class ConnectedCharacteristic:
    def __init__(self, service, conn_handle, value_handle):
        self._service = service
        self._name = name
        self._conn_handle = conn_handle
        self._value_handle = value_handle

    def notify(self, data=None):
        blesync.gatts_notify(self._conn_handle, self._value_handle, data)





class BLEClient:
    def __init__(self, *service_classes):
        self._service_classes = service_classes
        blesync.on_gatts_write(self._on_gatts_write)

    def scan(self):
        blesync.active(True)
        for addr_type, addr, adv_type, rssi, adv_data in blesync.gap_scan(
            2000,
            30000,
            30000
        ):
            parsed_data = parse_adv_data(adv_data)
            adv_name = decode_adv_name(parsed_data)
            adv_type_flags = decode_adv_type(parsed_data)

            # addr buffer is owned by caller so need to copy it.
            addr_copy = bytes(addr)
            yield BLEDevice(
                addr_type=addr_type,
                addr=addr_copy,
                adv_name=adv_name,
                adv_type_flags=adv_type_flags,
                rssi=rssi,
            )

    def connect(self, addr_type, addr):
        blesync.active(True)
        conn_handle = blesync.gap_connect(addr_type, addr)

        for start_handle, end_handle, uuid in blesync.gattc_discover_services(
            conn_handle
        ):
            for service_class in self._service_classes:
                try:
                    service = service_class(uuid)
                except ValueError:
                    continue

    def _on_gatts_write(self, conn_handle, value_handle):
        self.characteristics[(conn_handle, value_handle)]

    def _discover(self, service, conn_handle, start_handle, end_handle):
        characteristics = service.get_characteristics()

        for def_handle, value_handle, properties, uuid in blesync.gattc_discover_characteristics(
            conn_handle, start_handle, end_handle
        ):
            for attr_name, characteristic in characteristics:
                if characteristic.uuid != uuid:
                    continue

                characteristic_name, attr = characteristics[uuid]

                connected_characteristic = ConnectedCharacteristic(
                    service,
                    conn_handle,
                    value_handle,
                )

                setattr(
                    service,
                    characteristic_name,
                    connected_characteristic
                )

                # if bluetooth.FLAG_WRITE & properties == 0:
                # on_(characteristic_name)%_write_received
                # self.handles[uuid] = value_handle
                # if len(self.handles) == len(characteristics):
                #     break

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
