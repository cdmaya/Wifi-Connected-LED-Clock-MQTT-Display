# Wifi-Connected-LED-Clock-MQTT-Display

For some time, I wanted to buy several digital clocks with the following attributes

Wouldn’t require setting time manually – NOT HAVING THIS ABILITY THIS IS THE DEALBREAKER !!! – IT MUST fetch time from an NTP server and set the internal clock accordingly and will sync with the NTP server periodically.
Would need to be plugged in to main power (USB), and it must be able to run for several hours with a rechargeable battery in case the main power gets off.
Daylight saving time changes should be handled automatically (Twice a year)
It should display custom messages pushed through MQTT (Weather or other alerts)
It should display a message if the network connectivity is gone or if the NTP server is not accessible. In these cases, it must still show the time using the internal clock, until the network/NTP connection is reset, and time can be synced with NTP server successfully once the connectivity is restored.
It must have large LED digits that are conformably visible from the other end of the room.

I researched for some time if I could buy a digital clock with at least most of the above attributes (No 1 above is a MUST) but I couldn’t find any on Amazon, AliExpress or Banggood for a reasonable price.

I started researching on making something with the extra ESP modules that I had at hand and was playing around with the MAX7219 8x8 LED Displays through C/C++ on Arduino. In the meantime, I saw some projects in YouTube on programming ESP8266 (and ESP32) modules using Micropython. Personally, for me, Python programming is easier than C/C++ programming and I tested some basic LED blink programs with Micropython and goot hooked onto it due to the simplicity and easiness of using Micropython through Thonny IDE and  also found there is a very good python library written to drive the MAX7291 LED Matrix.

So decided to build the LED Clock/Display uisng Micropython.

There are the components used:

2 x 4X8X8 MAX7291 LED Matrix Displays
Wemos D1 mini (ESP8266)
TP4056 Charging Modile
7V Li-ion 18650 Rechargeable battery and holder.
Push Button

Circuit Diagram:

![Circuit](https://user-images.githubusercontent.com/51185952/210280613-6f356eb0-2a25-4609-85ac-7f9d121d5ccc.png)

The python script (Shared in Github) was uploaded to Wemos D1 uisng Thonny (Python IDE).

Python Code : Shared on Github

Thanks :

"max7219.py" library file from Mike Causer's Github is used in this script.

https://github.com/mcauser/micropython-max7219/blob/master/max7219.py

"umqttsimple.py" library file from Rui Santos's Github is used in this script.

https://github.com/RuiSantosdotme/ESP-MicroPython/blob/master/code/MQTT/umqttsimple.py

At a high level the python script works as below:

- At startup fetches the time from the specified NTP server (I have a local NTP server, else we can give the IP Address of a public NTP server as well) and updates it's internal real time clock (RTC) and displays time

- It also subscribes to the given MQTT topic

- Every 10 minutes syncs the internal real time clock (RTC) with the NTP server.

- If the Wifi, NTP or MQTT connections are failed, there will be an indication on the LED Matrix.

- There are some commands that it can accept over MQTT (offset in hours from UTC, reboot module, etc)

- “utc_offset.var” file sored on the Wemos D1 module is used to store consistent variable on UTC offset value to be used.

- We can send texts to the clock through MQTT which will be displays as static text (if the string is 8 characters or less) or  as scrolling text ((if the string is more than 8 characters). In my case it displays the weather information parodically pushed to it through MQTT by a Nodered instance.




Also there is a push button to reset the clock manually (connecting RST pin to GND in Wemos D1) and also a connection from  D0 to RST pint in case if a soft reboot is needed (command through MQTT)

The casing for the clock used here is a Bamboo Wood Stacking Drawer Organizer (Amazon).

Transparent color plastic film sheets (Amazon) were cut and used to cover the face and give the LED matrix a better sleek look.

As always thanks for reading!
