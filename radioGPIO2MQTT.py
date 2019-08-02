#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import sys
from time import sleep
import threading
import os
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

class RotaryEncoder:
    
    def __init__(self, gpioA, gpioB, gpioSW, pressCallback):
        self.gpioA = gpioA
        self.gpioB = gpioB
        self.gpioSW = gpioSW
        self.pressCallback = pressCallback
        self.counter = 0
        self.levelA = 1
        self.levelB = 1
        self.lock = threading.Lock()
        GPIO.setup(self.gpioA, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.gpioB, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.gpioSW, GPIO.IN)

        GPIO.add_event_detect(gpioA, GPIO.RISING, callback=self.rotary_interrupt)
        GPIO.add_event_detect(gpioB, GPIO.RISING, callback=self.rotary_interrupt)
        GPIO.add_event_detect(self.gpioSW, GPIO.RISING, callback=self.pressCallback, bouncetime=1500)
        return
    
    def rotary_interrupt(self, channel):
        newLevelA = GPIO.input(self.gpioA)
        newLevelB = GPIO.input(self.gpioB)

        #Debounce identical interrupts
        if self.levelA == newLevelA and self.levelB == newLevelB:
            return

        self.levelA = newLevelA
        self.levelA = newLevelB

        if (newLevelA and newLevelB):
            self.lock.acquire()
            if channel == self.gpioA:
                self.counter += 1
            else:
                self.counter -= 1
            self.lock.release()
        return

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")
    client.subscribe("hass/status")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    if msg.topic == "hass/status":
        sendDiscover()

HOST = sys.argv[1]
PORT = int(sys.argv[2])
USERNAME = sys.argv[3]
PASSWORD = sys.argv[4]

def sendDiscover():
    publish.single('homeassistant/sensor/home_radio_volume/config', payload='{"name": "Home Radio Volume"}', hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD})
    publish.single('homeassistant/sensor/home_radio_selector/config', payload='{"name": "Home Radio Selector"}', hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD})
    publish.single('homeassistant/sensor/home_radio_onoff/config', payload='{"name": "Home Radio OnOff"}', hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD})
    publish.single('homeassistant/sensor/home_radio_next/config', payload='{"name": "Home Radio Next"}', hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD})
    publish.single('homeassistant/sensor/home_radio_selector_press/config', payload='{"name": "Home Radio Selector Press"}', hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD})
 
volume_topic = 'homeassistant/sensor/home_radio_volume/state'
selector_topic = 'homeassistant/sensor/home_radio_selector/state'
selector_press_topic = 'homeassistant/sensor/home_radio_selector_press/state'
onoff_topic = 'homeassistant/sensor/home_radio_onoff/state'
next_topic = 'homeassistant/sensor/home_radio_next/state'
client = mqtt.Client("ha-client")
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(USERNAME, PASSWORD)
client.connect(HOST, PORT, 60)
client.loop_start() 
sendDiscover()

domain = 'script'
mediaplayer_name = 'media_player.wohnzimmer_2'
RoPush = 26
RoPushOffOn = 21
CLOCKPIN_LEFT = 5
DATAPIN_LEFT = 6
SWITCHPIN_LEFT = 13
CLOCKPIN_RIGHT = 20
DATAPIN_RIGHT = 12
SWITCHPIN_RIGHT = 16
global counter
global ky040_left
global ky040_right
currentOnOff = False
lastVolTime = 0

def setup():
    print("GPIO setup")
    
    global ky040_left
    global ky040_right
    global counter
    global current_input_select
    current_input_select = "input_select.radio_main_menu"

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RoPush, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(RoPushOffOn, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    ky040_left = RotaryEncoder(CLOCKPIN_LEFT, DATAPIN_LEFT, SWITCHPIN_LEFT, rotaryButtonPressLeft)
    ky040_right = RotaryEncoder(CLOCKPIN_RIGHT, DATAPIN_RIGHT, SWITCHPIN_RIGHT, rotaryButtonPressRight)
    GPIO.add_event_detect(RoPush, GPIO.FALLING, callback=button_press, bouncetime=1000)
    GPIO.add_event_detect(RoPushOffOn, GPIO.FALLING, callback=toggle_media_player, bouncetime=1000)

def rotaryButtonPressLeft(dummy):
    time.sleep(1)

def rotaryButtonPressRight(dummy):
    publish.single(selector_press_topic, payload="True", hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)
    publish.single(selector_press_topic, payload="False", hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)

def button_press(ev=None):
    publish.single(next_topic, payload="True", hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)
    publish.single(next_topic, payload="False", hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)

def toggle_media_player(ev=None):
    global currentOnOff
    currentOnOff = not currentOnOff
    publish.single(onoff_topic, payload=str(currentOnOff), hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)
    print("toggle_media_player")

def loop():
    lastVolTime = 0
    currentVolume = 20
    currentSelector = 1000
    while True:
        time.sleep(0.1)
        
        try:
            ##########
            # Volume #
            ##########
            ky040_left.lock.acquire()
            newValue = ky040_left.counter
            ky040_left.counter = 0
            ky040_left.lock.release()
            if (newValue != 0):
                newVolume = currentVolume + newValue*abs(newValue)
                if (newVolume > 0 and newVolume < 100):
                    publish.single(volume_topic, payload=str(newVolume), hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)
                    print("Setting rotary left value (volume): " + str(currentVolume) + " -> " + str(newVolume) + " (inc: " + str(newValue) + ")")
                    currentVolume = newVolume
            
            ##########
            # Menu   #
            ##########
            ky040_right.lock.acquire()
            newValue = ky040_right.counter
            ky040_right.counter = 0
            ky040_right.lock.release()
            if (newValue != 0):
                if (newValue > 0):
                    currentSelector = currentSelector + 1
                elif (newValue < 0):
                    currentSelector = currentSelector - 1
                print("Setting rotary right value (menu): ", newValue)
                publish.single(selector_topic, payload=str(currentSelector), hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)
        except:
            print("Some exception")
            print(traceback.format_exc())

def destroy():
    GPIO.cleanup()             # Release resource

if __name__ == '__main__':     # Program start from here
    setup()
    try:
        loop()
    except KeyboardInterrupt:  # When 'Ctrl+C' is pressed, the child program destroy() will be  executed.
        destroy()
