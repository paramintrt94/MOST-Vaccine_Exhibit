# Importing libraries used to program this script
from colorzero import Color
from time import time
import math

class Cell:
    color_sensitivity = 1  # set color sensitivity (higher number allows higher variance in color reading)
    max_variation = 5 # set how much variation to allow
    certainty_level = 6  # set higher value to ignore more ambient lighting when no piece is placed
    inoc_duration = 2 # set how long it takes to inoculate
    immune_duration = 6  # set to how many seconds before immune reset
    exp_value = 0.1  # set how aggressive to fade color, lower value keeps green on longer
    k_value = math.log(1 / exp_value)
    red_limits = [range(30 - color_sensitivity, 43 + color_sensitivity),
                  range(8 - color_sensitivity, 11 + color_sensitivity),
                  range(8 - color_sensitivity, 11 + color_sensitivity)]
    green_limits = [range(0 - color_sensitivity, 5 + color_sensitivity),
                    range(25 - color_sensitivity, 31 + color_sensitivity),
                    range(17 - color_sensitivity, 29 + color_sensitivity)]
    white_limits = [range(10 - color_sensitivity, 11 + color_sensitivity),
                    range(18 - color_sensitivity, 21 + color_sensitivity),
                    range(15 - color_sensitivity, 22 + color_sensitivity)]

    def __init__(self, led, idx):
        self.idx = idx
        self.status = "healthy"
        self.prev_status = "healthy"
        self.led = led
        self.led.color = (0, 0, 0)
        self.last_immunized = -1
        self.prev_color = ""
        self.prev_color_readings = [[], [], []]  # [[list of prev red], [list of prev green], [list of prev blue]]
        self.consistency_count = 0
        # end of init

    def update_status(self, sensor, debug_level=0):
        # updates cell and LED color to respond to piece being placed on sensor
        color = self.check_color(sensor, debug_level)
        # ~ self.prev_status = self.status
        if  self.status == "healthy":
            # if LEDs are currently off, turn them on. If on, move on.
            None if self.led.is_lit else self.led.on()
            if color == "red":
                print("Cell " + str(self.idx) + " is now infected.") if debug_level == 1 else None
                self.status = "infected"
                self.led.color = (1, 0, 0)
            elif color == "green" or color == "white":
                print("Cell " + str(self.idx) + " is being inoculated.") if debug_level == 1 else None
                self.prev_status = "healthy"
                self.status = "inoculating"
                self.last_immunized = time()

        elif self.status == "infected":
            if color == "green" or color == "white":
                self.prev_status = "infected"
                self.status = "inoculating"
                self.last_immunized = time()

        elif self.status == "immune":
            if not(color == "green" or color == "white"):
                self.prev_status = "immune"
                self.status = "reverting"
                self.last_immunized = time()

        elif self.status == "inoculating":
            if color == "red":
                # if virus piece is placed back on sensor while inoculating, cell reverts to being infected
                self.last_immunized = -1
                self.status = "infected"
            elif color == "green" or color == "white":
                # slowly fade to green while piece is still on sensor
                elapsed_time = time() - self.last_immunized
                elapsed_time_percent = elapsed_time / self.inoc_duration
                if elapsed_time_percent >= 1:
                    print("Cell " + str(self.idx) + " is now immunized.") if debug_level == 1 else None
                    self.status = "immune"
                    self.last_immunized = time()
                    self.led.color = (0, 1, 0)
                else:
                    # ~ print("prev status", self.prev_status)
                    if self.prev_status == "healthy":
                        # ~ print(self.led.value)
                        self.led.color = (1-elapsed_time_percent, 1, 1-elapsed_time_percent)
                    elif self.prev_status == "infected":
                        self.led.color = (1-elapsed_time_percent, elapsed_time_percent, 0)
            else:
                # if piece was lifted off before being fully inoculated, cell will revert to previous status
                self.status = self.prev_status
                print("Cell " + str(
                    self.idx) + " reverting back to "+self.prev_status) if debug_level == 1 else None
                if self.prev_status == "healthy":
                    self.led.color = (1, 1, 1)
                elif self.prev_status == "infected":
                    self.led.color = (1, 0, 0)

        elif self.status == "reverting":
            elapsed_time = time() - self.last_immunized
            elapsed_time_percent = elapsed_time / self.immune_duration
            
            if elapsed_time_percent >= 1:
                print("Cell " + str(
                    self.idx) + " Reset to healthy.") if debug_level == 1 else None
                self.status = "healthy"
                self.led.color = (1, 1, 1)
            else:
                fade_level = self.exp_value * math.exp(self.k_value * elapsed_time_percent)
                self.led.color = (fade_level, 1, fade_level)

    def is_consistent(self, rgb_color_reading):
        for i in range(3):
            self.prev_color_readings[i].append(rgb_color_reading[i])
        if len(self.prev_color_readings[0]) < self.certainty_level + 1:
            return False
        else:
            for i in range(3):
                self.prev_color_readings[i].pop(0)
            diff = 0
            for color_group in self.prev_color_readings:
                for idx in range(1, len(color_group)):
                    if color_group[idx] != color_group[idx-1]:
                        diff += 1
            if diff <= self.max_variation:
                self.consistency_count += 1
                return True
            else:
                self.consistency_count = 0
                return False

    def check_color(self, sensor, debug_level):
        # reads sensor color data and outputs color as string (red, green, white, invalid)
        sensor_color_rgb = sensor.color_rgb_bytes
        print(str(sensor_color_rgb)+" [" + self.prev_color + "]\t",end="") if debug_level >= 2 else None  # print rgb sensor reading in (r,g,b) values
        if self.is_consistent(sensor_color_rgb):
            # checking for red piece
            if (sensor_color_rgb[0] in self.red_limits[0]) and (
                    sensor_color_rgb[1] in self.red_limits[1]) and (
                    sensor_color_rgb[2] in self.red_limits[2]):
                print("S" + str(
                    self.idx) + " detected virus piece") if self.consistency_count == self.certainty_level and debug_level == 1 else None

                self.prev_color = "red"
                return "red"
            # checking for green piece
            elif (sensor_color_rgb[0] in self.green_limits[0]) and (
                    sensor_color_rgb[1] in self.green_limits[1]) and (
                    sensor_color_rgb[2] in self.green_limits[2]):
                print("S" + str(
                    self.idx) + " detected deactivated virus vaccine") if self.consistency_count == self.certainty_level and debug_level == 1 else None
                self.prev_color = "green"
                return "green"
            # checking for white piece
            elif (sensor_color_rgb[0] in self.white_limits[0]) and (
                    sensor_color_rgb[1] in self.white_limits[1]) and (
                    sensor_color_rgb[2] in self.white_limits[2]):
                print("S" + str(
                    self.idx) + " detected mRNA messenger piece") if self.consistency_count == self.certainty_level and debug_level == 1 else None
                self.prev_color = "white"
                return "white"
            else:
                self.prev_color = "invalid"
                return "invalid"
        else:
            self.prev_color = "invalid"
            return "invalid"
