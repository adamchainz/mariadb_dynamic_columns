# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import struct
import unittest


def column_create(dicty):
    buf = []

    flags = struct.pack('B', 4)
    buf.append(flags)

    column_count = 0
    column_directory = []
    directory_offset = 0
    name_offset = 0
    names = []
    data_offset = 0
    data = []
    for name, value in sorted(dicty.iteritems()):
        if value is None:
            continue

        encname = name.encode('utf-8')
        if isinstance(value, int):
            dtype, encvalue = encode_int(value)
        elif isinstance(value, basestring):
            dtype, encvalue = encode_string(value)
        elif isinstance(value, dict):
            dtype = 8
            encvalue = column_create(value)
        else:
            raise TypeError("Unencodable type {}".format(type(value)))

        column_count += 1
        column_directory.append(struct.pack('H', name_offset))
        column_directory.append(struct.pack('H', (data_offset << 4) + dtype))
        names.append(encname)
        name_offset += len(encname)
        data.append(encvalue)
        data_offset += len(encvalue)

        directory_offset += 2

    buf.append(struct.pack('H', column_count))
    enc_names = b''.join(names)
    buf.append(struct.pack('H', len(enc_names)))
    buf.append(b''.join(column_directory))
    buf.append(enc_names)
    buf.append(b''.join(data))

    return b''.join(buf)


def encode_int(value):
    """
    Stored in the schema:
    0: no data
    -1: 1
     1: 2
    -2: 3
     2: 4
    ...
    """
    if value == 0:
        encoded = b''
    else:
        encoded = abs(2 * value)
        if value < 0:
            encoded -= 1

        cut_last_byte = False
        if encoded <= (2 ** 8 - 1):
            code = 'B'
        elif encoded <= (2 ** 16 - 1):
            code = 'H'
        elif encoded <= (2 ** 24 - 1):
            # Want 3 bytes but only 4 bytes possible with struct
            code = 'I'
            cut_last_byte = True
        elif encoded <= (2 ** 32 - 1):
            code = 'I'
        else:
            raise ValueError("int {} too large".format(value))

        encoded = struct.pack(code, encoded)
        if cut_last_byte:
            encoded = encoded[:-1]
    return 0, encoded


def encode_string(value):
    encoded = value.encode('utf-8')
    return 3, b'\x21' + encoded  # 0x21 = utf8mb4 charset number


def hexs(byte_string):
    return ''.join(("%02X" % ord(x) for x in byte_string))


class ColumnCreateTests(unittest.TestCase):
    def assert_hex(self, dicty, hexstring):
        assert hexs(column_create(dicty)) == hexstring

    def test_a_1(self):
        self.assert_hex({"a": 1}, b"0401000100000000006102")

    def test_a_minus1(self):
        self.assert_hex({"a": -1}, b"0401000100000000006101")

    def test_a_minus2(self):
        self.assert_hex({"a": -2}, b"0401000100000000006103")

    def test_a_0(self):
        self.assert_hex({"a": 0}, b"04010001000000000061")

    def test_a_128(self):
        self.assert_hex({"a": 128}, b"040100010000000000610001")

    def test_a_65535(self):
        self.assert_hex({"a": 65535}, b"04010001000000000061FEFF01")

    def test_a_1048576(self):
        self.assert_hex({"a": 1048576}, b"04010001000000000061000020")

    def test_c_1(self):
        self.assert_hex({"c": 1}, b"0401000100000000006302")

    def test_a_1_b_2(self):
        self.assert_hex(
            {"a": 1, "b": 2},
            b"0402000200000000000100100061620204"
        )

    def test_a_1_b_2_c_3(self):
        self.assert_hex(
            {"a": 1, "b": 2, "c": 3},
            b"0403000300000000000100100002002000616263020406"
        )

    def test_abc_123(self):
        self.assert_hex(
            {"abc": 123},
            b"040100030000000000616263F6"
        )

    def test_string_empty(self):
        self.assert_hex({"a": ""}, b"0401000100000003006121")

    def test_string_values(self):
        self.assert_hex({"a": "string"}, b"0401000100000003006121737472696E67")

    def test_a_unicode_poo(self):
        self.assert_hex({"a": "💩"}, b"0401000100000003006121F09F92A9")

    def test_None(self):
        self.assert_hex({"a": None}, b"0400000000")

    def test_dict(self):
        self.assert_hex(
            {"a": {"b": "c"}},
            b"04010001000000080061040100010000000300622163"
        )

if __name__ == '__main__':
    unittest.main()
