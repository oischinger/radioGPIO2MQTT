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
    print("Connected with result code "+str(rc), flush=True)

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")
    client.subscribe("homeassistant/status")
    client.subscribe(ext_lights_topic + "/set")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    messages.append(msg)

HOST = sys.argv[1]
PORT = int(sys.argv[2])
USERNAME = sys.argv[3]
PASSWORD = sys.argv[4]

messages=[]

volume_topic = 'homeassistant/sensor/home_radio_volume'
selector_topic = 'homeassistant/sensor/home_radio_selector'
selector_press_topic = 'homeassistant/sensor/home_radio_selector_press'
onoff_topic = 'homeassistant/sensor/home_radio_onoff'
next_topic = 'homeassistant/sensor/home_radio_next'

ext_lights_topic = 'homeassistant/light/home_radio_extlights'

def sendDiscover():
    publish.single(volume_topic + '/config', payload='{"name": "Home Radio Volume", "state_topic": "' + volume_topic + '"}', hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD})
    publish.single(selector_topic + '/config', payload='{"name": "Home Radio Selector", "state_topic": "' + selector_topic + '"}', hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD})
    publish.single(onoff_topic + '/config', payload='{"name": "Home Radio OnOff", "state_topic": "' + onoff_topic + '"}', hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD})
    publish.single(next_topic + '/config', payload='{"name": "Home Radio Next", "state_topic": "' + next_topic + '"}', hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD})
    publish.single(selector_press_topic + '/config', payload='{"name": "Home Radio Selector Press", "state_topic": "' + selector_press_topic + '"}', hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD})
    publish.single(ext_lights_topic + '/config', payload='{"name": "Home Radio External Light", "state_topic": "' + ext_lights_topic + '/state", "command_topic": "' + ext_lights_topic + '/set"}', hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD})

client = mqtt.Client("ha-client")

def setupmqtt():
    client.on_connect = on_connect
    client.on_message = on_message
    client.username_pw_set(USERNAME, PASSWORD)
    print("Connecting to " + HOST, flush=True)
    client.connect_async(HOST, PORT, 60)
    client.loop_start() 
    print("Sending discover", flush=True)
    sendDiscover()

RoPushNext = 26
RoPushOffOn = 21
CLOCKPIN_LEFT = 5
DATAPIN_LEFT = 6
SWITCHPIN_LEFT = 13
CLOCKPIN_RIGHT = 20
DATAPIN_RIGHT = 12
SWITCHPIN_RIGHT = 16
EXT_LIGHT_PIN = 25
global counter
global ky040_left
global ky040_right
currentOnOff = False
RoPushOffOnLastPullUp = 0

def setup():
    print("GPIO setup", flush=True)
    
    global ky040_left
    global ky040_right
    global counter

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RoPushNext, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(RoPushOffOn, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    ky040_left = RotaryEncoder(CLOCKPIN_LEFT, DATAPIN_LEFT, SWITCHPIN_LEFT, rotaryButtonPressLeft)
    ky040_right = RotaryEncoder(CLOCKPIN_RIGHT, DATAPIN_RIGHT, SWITCHPIN_RIGHT, rotaryButtonPressRight)
    GPIO.add_event_detect(RoPushNext, GPIO.FALLING, callback=button_press_next, bouncetime=100)
    GPIO.add_event_detect(RoPushOffOn, GPIO.BOTH, callback=button_press_on_off, bouncetime=100)
    GPIO.setup(EXT_LIGHT_PIN, GPIO.OUT)

def rotaryButtonPressLeft(dummy):
    time.sleep(1)

def rotaryButtonPressRight(dummy):
    publish.single(selector_press_topic + "/state", payload="True", hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)
    publish.single(selector_press_topic + "/state", payload="False", hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)

def button_press_next(ev=None):
    publish.single(next_topic + "/state", payload="True", hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)
    publish.single(next_topic + "/state", payload="False", hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)

def button_press_on_off(ev=None):
    global currentOnOff
    global RoPushOffOnLastPullUp
    if GPIO.input(RoPushOffOn) == 1:
        RoPushOffOnLastPullUp = time.time()
    else:
        if RoPushOffOnLastPullUp > 0 and (time.time() - RoPushOffOnLastPullUp) >= 1.0:
            currentOnOff = not currentOnOff
            publish.single(onoff_topic + "/state", payload=str(currentOnOff), hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)
            print("toggle_media_player", flush=True)
        RoPushOffOnLastPullUp = 0

def loop():
    currentVolume = 20
    currentSelector = 1000
    while True:
        time.sleep(0.2)
        if len(messages)>0:
            msg=messages.pop(0)

            if msg.topic == "homeassistant/status":
                sendDiscover()
            elif msg.topic == ext_lights_topic + "/set":
                value=str(msg.payload.decode("utf-8"))
                print("received ", value, flush=True)
                gpioValue = value == "ON" and 1 or 0
                GPIO.output(EXT_LIGHT_PIN, gpioValue)
                publish.single(ext_lights_topic + "/state", payload=value, hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)
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
                    publish.single(volume_topic + "/state", payload=str(newVolume), hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)
                    print("Setting rotary left value (volume): " + str(currentVolume) + " -> " + str(newVolume) + " (inc: " + str(newValue) + ")", flush=True)
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
                print("Setting rotary right value (menu): ", newValue, flush=True)
                publish.single(selector_topic + "/state", payload=str(currentSelector), hostname=HOST, port=PORT, auth={'username': USERNAME, 'password': PASSWORD}, retain=True)
        except:
            print("Some exception", flush=True)
            print(traceback.format_exc(), flush=True)

def destroy():
    GPIO.remove_event_detect(RoPush)
    GPIO.remove_event_detect(RoPushOffOn)
    GPIO.remove_event_detect(CLOCKPIN_LEFT)
    GPIO.remove_event_detect(DATAPIN_LEFT)
    GPIO.remove_event_detect(SWITCHPIN_LEFT)
    GPIO.remove_event_detect(CLOCKPIN_RIGHT)
    GPIO.remove_event_detect(DATAPIN_RIGHT)
    GPIO.remove_event_detect(SWITCHPIN_RIGHT)
    GPIO.cleanup()

if __name__ == '__main__':
    setup()
    setupmqtt()
    try:
        loop()
    except KeyboardInterrupt:  # When 'Ctrl+C' is pressed, the child program destroy() will be  executed.
        destroy()
