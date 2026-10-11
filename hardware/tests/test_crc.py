from simhelp import settle, simulate

from hwlib.crc import Crc8Byte


def crc8_reference(data: bytes, crc: int = 0) -> int:
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def hw_crc(data: bytes) -> int:
    dut = Crc8Byte()
    result = [0]

    async def bench(ctx):
        crc = 0
        for byte in data:
            ctx.set(dut.crc_in, crc)
            ctx.set(dut.data, byte)
            await settle(ctx)
            crc = ctx.get(dut.crc_out)
        result[0] = crc

    simulate(dut, bench, clock=False)
    return result[0]


def test_standard_check_value():
    assert hw_crc(b"123456789") == 0xF4


def test_matches_reference_on_many_inputs():
    for data in (b"\x00", b"\xff", b"\x80", b"\x01\x02\x03", bytes(range(32)), b"neatHack"):
        assert hw_crc(data) == crc8_reference(data), data


def test_single_bytes():
    for b in (0x00, 0x01, 0x07, 0x80, 0xAA, 0xFF):
        assert hw_crc(bytes([b])) == crc8_reference(bytes([b])), hex(b)
