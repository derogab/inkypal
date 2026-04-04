"""Minimal Raspberry Pi driver for Waveshare 2.13 inch e-Paper V4.

This file is adapted from Waveshare's Python demo driver for `epd2in13_V4.py`
and `epdconfig.py`, both released under the MIT license.
Only the Raspberry Pi path and the methods needed by this project are kept.
"""

from __future__ import annotations

import time

import gpiozero
import spidev

EPD_WIDTH = 122
EPD_HEIGHT = 250


class RaspberryPiInterface:
    """Thin GPIO/SPI wrapper for the Waveshare HAT pinout."""

    RST_PIN = 17
    DC_PIN = 25
    CS_PIN = 8
    BUSY_PIN = 24
    PWR_PIN = 18

    def __init__(self) -> None:
        self.spi = spidev.SpiDev()
        self.gpio_rst = gpiozero.LED(self.RST_PIN)
        self.gpio_dc = gpiozero.LED(self.DC_PIN)
        self.gpio_pwr = gpiozero.LED(self.PWR_PIN)
        self.gpio_busy = gpiozero.Button(self.BUSY_PIN, pull_up=False)

    def digital_write(self, pin: int, value: int) -> None:
        if pin == self.RST_PIN:
            self.gpio_rst.on() if value else self.gpio_rst.off()
        elif pin == self.DC_PIN:
            self.gpio_dc.on() if value else self.gpio_dc.off()
        elif pin == self.PWR_PIN:
            self.gpio_pwr.on() if value else self.gpio_pwr.off()

    def digital_read(self, pin: int) -> int:
        if pin == self.BUSY_PIN:
            return int(self.gpio_busy.value)
        raise ValueError(f"Unsupported input pin: {pin}")

    @staticmethod
    def delay_ms(delay_ms: int) -> None:
        time.sleep(delay_ms / 1000.0)

    def spi_writebyte(self, data: list[int]) -> None:
        self.spi.writebytes(data)

    def spi_writebyte2(self, data: bytes | bytearray | list[int]) -> None:
        self.spi.writebytes2(data)

    def module_init(self) -> None:
        self.gpio_pwr.on()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 4_000_000
        self.spi.mode = 0b00

    def module_exit(self) -> None:
        self.spi.close()
        self.gpio_rst.off()
        self.gpio_dc.off()
        self.gpio_pwr.off()


class EPD:
    """Minimal driver for full-screen and partial updates."""

    def __init__(self) -> None:
        self.io = RaspberryPiInterface()
        self.reset_pin = self.io.RST_PIN
        self.dc_pin = self.io.DC_PIN
        self.busy_pin = self.io.BUSY_PIN
        self.cs_pin = self.io.CS_PIN
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT
        self._initialized = False

    def reset(self) -> None:
        self.io.digital_write(self.reset_pin, 1)
        self.io.delay_ms(20)
        self.io.digital_write(self.reset_pin, 0)
        self.io.delay_ms(2)
        self.io.digital_write(self.reset_pin, 1)
        self.io.delay_ms(20)

    def send_command(self, command: int) -> None:
        self.io.digital_write(self.dc_pin, 0)
        self.io.spi_writebyte([command])

    def send_data(self, data: int) -> None:
        self.io.digital_write(self.dc_pin, 1)
        self.io.spi_writebyte([data])

    def send_data_block(self, data: bytes | bytearray | list[int]) -> None:
        self.io.digital_write(self.dc_pin, 1)
        self.io.spi_writebyte2(data)

    def read_busy(self) -> None:
        while self.io.digital_read(self.busy_pin) == 1:
            self.io.delay_ms(10)

    def turn_on_display(self) -> None:
        self.send_command(0x22)
        self.send_data(0xF7)
        self.send_command(0x20)
        self.read_busy()

    def turn_on_display_part(self) -> None:
        self.send_command(0x22)
        self.send_data(0xFF)
        self.send_command(0x20)
        self.read_busy()

    def set_window(self, x_start: int, y_start: int, x_end: int, y_end: int) -> None:
        self.send_command(0x44)
        self.send_data((x_start >> 3) & 0xFF)
        self.send_data((x_end >> 3) & 0xFF)
        self.send_command(0x45)
        self.send_data(y_start & 0xFF)
        self.send_data((y_start >> 8) & 0xFF)
        self.send_data(y_end & 0xFF)
        self.send_data((y_end >> 8) & 0xFF)

    def set_cursor(self, x: int, y: int) -> None:
        self.send_command(0x4E)
        self.send_data(x & 0xFF)
        self.send_command(0x4F)
        self.send_data(y & 0xFF)
        self.send_data((y >> 8) & 0xFF)

    def init(self) -> None:
        self.io.module_init()
        self._initialized = True
        self.reset()
        self.read_busy()
        self.send_command(0x12)
        self.read_busy()
        self.send_command(0x01)
        self.send_data(0xF9)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_command(0x11)
        self.send_data(0x03)
        self.set_window(0, 0, self.width - 1, self.height - 1)
        self.set_cursor(0, 0)
        self.send_command(0x3C)
        self.send_data(0x05)
        self.send_command(0x21)
        self.send_data(0x00)
        self.send_data(0x80)
        self.send_command(0x18)
        self.send_data(0x80)
        self.read_busy()

    def get_buffer(self, image) -> bytearray:
        image_width, image_height = image.size
        if image_width == self.width and image_height == self.height:
            mono = image.convert("1")
        elif image_width == self.height and image_height == self.width:
            mono = image.rotate(90, expand=True).convert("1")
        else:
            raise ValueError(
                f"Image must be {self.width}x{self.height} or {self.height}x{self.width}, got {image_width}x{image_height}"
            )
        return bytearray(mono.tobytes("raw"))

    def display(self, image_buffer: bytes | bytearray | list[int]) -> None:
        self.send_command(0x24)
        self.send_data_block(image_buffer)
        self.turn_on_display()

    def display_part_base_image(self, image_buffer: bytes | bytearray | list[int]) -> None:
        self.send_command(0x24)
        self.send_data_block(image_buffer)
        self.send_command(0x26)
        self.send_data_block(image_buffer)
        self.turn_on_display()

    def display_partial(self, image_buffer: bytes | bytearray | list[int]) -> None:
        self.io.digital_write(self.reset_pin, 0)
        self.io.delay_ms(1)
        self.io.digital_write(self.reset_pin, 1)

        self.send_command(0x3C)
        self.send_data(0x80)

        self.send_command(0x01)
        self.send_data(0xF9)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x11)
        self.send_data(0x03)

        self.set_window(0, 0, self.width - 1, self.height - 1)
        self.set_cursor(0, 0)

        self.send_command(0x24)
        self.send_data_block(image_buffer)
        self.turn_on_display_part()

    def clear(self, color: int = 0xFF) -> None:
        line_width = self.width // 8 if self.width % 8 == 0 else (self.width // 8) + 1
        self.send_command(0x24)
        self.send_data_block([color] * (self.height * line_width))
        self.turn_on_display()

    def sleep(self) -> None:
        if not self._initialized:
            return
        try:
            self.send_command(0x10)
            self.send_data(0x01)
            self.io.delay_ms(2000)
        finally:
            self._initialized = False
            self.io.module_exit()
