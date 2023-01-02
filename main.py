# Thanks : 
# 1.	"max7219.py" library file from Mike Causer's Github is used in this script.
# https://github.com/mcauser/micropython-max7219/blob/master/max7219.py
# 2.	"umqttsimple.py" library file from Rui Santos's Github is used in this script.
# https://github.com/RuiSantosdotme/ESP-MicroPython/blob/master/code/MQTT/umqttsimple.py
#
# At a high level the python script works as below:
# – At startup fetches the time from the specified NTP server (I have a local NTP server, else we can give the IP Address of a public NTP server as well) and updates it’s internal real time clock (RTC) and displays time
# – It also subscribes to the given MQTT topic
# – Every 10 minutes syncs the internal real time clock (RTC) with the NTP server.
# – If the Wifi, NTP or MQTT connections are failed, there will be an indication on the LED Matrix.
# – There are some commands that it can accept over MQTT (offset in hours from UTC, reboot module, etc)
# – “utc_offset.var” file sored on the Wemos D1 module is used to store consistent variable on UTC offset value to be used.
# – We can send texts to the clock through MQTT which will be displays as static text (if the string is 8 characters or less) or  as scrolling text (if the string is more than 8 characters). In my case it displays the weather information parodically pushed to it through MQTT by a Nodered instance.

from machine import RTC
import network
import ntptime
from machine import Pin, SPI
import max7219
import time
from umqttsimple import MQTTClient
import ubinascii
import gc
import esp

spi = SPI(1, baudrate=10000000)
screen = max7219.Max7219(64, 8, spi, Pin(15))

screen.brightness(1)
screen.fill(0)
screen.show()
time.sleep(0.5)

timezone_hour = 0 # Defaulting to UTC

counter = 0
string = ""
cycle_time = 1
ntp_sync_err = 0

clock = "--------"

network_fail = 0
max_network_fail = 14400

wifi_network = '<your-wifi-network-name>'
wifi_pw = '<your-wifi-network-passwd'

station = network.WLAN(network.STA_IF)

station.active(True)

def connect():
    global screen, wifi_network, wifi_pw, network_fail, max_network_fail
    if station.isconnected()==False:
        try:
            station.connect(wifi_network, wifi_pw)
        except:
            network_fail += 1
            print("Trying to reconnect Wifi..."+str(network_fail))
            if network_fail > max_network_fail:
                time.sleep(1)
                gc.collect()
                machine.reset()
    if station.isconnected()!=False:
        network_fail = 0
        print("Wifi reconnection successful")
        print("(IP Adress, Subnet Mask, Gateway, DNS)")
        print(station.ifconfig())
     
def disconnect():
    if station.active() == True: 
        station.active(False)
    if station.isconnected() == False:
        print("Disconnected")
        
while station.isconnected()==False:
    try:
        station.connect(wifi_network, wifi_pw)
    except:
        network_fail += 1
        if network_fail%2==0:
            wifimsg = "WIFI .!."
        else:
            wifimsg = "WIFI !.!"
            print("Trying to connect Wifi..."+str(network_fail))
            screen.fill(0)
            screen.text(wifimsg, 0, 0, 1)
            screen.show()
            time.sleep(1)
            if network_fail > max_network_fail:
                time.sleep(1)
                gc.collect()
                machine.reset()
 
### MQTT #######################################################################
mqtt_fail = 0
max_mqtt_fail = 28800

mqtt_server = '<your-mqtt-server-address>'
mqtt_un = '<your-mqtt-username>'
mqtt_pw = '<your-mqtt-password>'
topic_sub = b'wifi-clock1/toesp' # topic used to send commands to the clock
topic_pub = b'wifi-clock1/fromesp' # topic used to send received outputs from the clock
client_id = 'wifi-clock1'

status_cycle = 1200

def sub_cb(topic, msg):
    global string, timezone_hour, counter
    print ('Received Message %s from topic %s' %(msg, topic))
    msg = str(msg.decode())
    if msg[0:8]=="display ":
        string = msg[8:]
        print("Display - "+msg[8:])
        return
    elif msg=="utcoffset":
        try:
            client.publish(topic_pub, "utcoffset "+str(timezone_hour))
        except:
            print ('Could not publish to %s' %(topic_pub))
    elif msg[0:10]=="utcoffset ":
        utcoffset = msg[10:]
        try:
            utcoffset = int(utcoffset)
            if utcoffset!=timezone_hour:
                timezone_hour = utcoffset
                f_utc_offset = open("utc_offset.var","w")
                f_utc_offset.write(str(timezone_hour))
                f_utc_offset.close()
                print("UTC offset saved in memory: "+str(timezone_hour))
                counter = 0
            else:
                print("UTC offset is the same as saved in memory: "+str(utcoffset))
        except:
            print("UTC offset couldn't be updated with: "+str(utcoffset))
        try:
            client.publish(topic_pub, "utcoffset "+str(timezone_hour))
        except:
            print ('Could not publish to %s' %(topic_pub))
    elif msg=="time":
        try:
            client.publish(topic_pub, "time "+str(hours)+":"+str(minutes)+":"+str(seconds))
        except:
            print ('Could not publish to %s' %(topic_pub))
    elif str(msg)=="reset 1":
        print("Resetting - ESP")
        try:
            client.disconnect()
            station.disconnect()
        except:
            pass
        time.sleep(1)
        gc.collect()
        machine.reset()
    elif str(msg)=="clock":
        try:
            client.publish(topic_pub, "clock "+str(clock))
        except:
            print ('Could not publish to %s' %(topic_pub))  
        

    
def connect_and_subscribe():
    global client_id, mqtt_server, topic_sub
    if station.isconnected()==False:
        connect()
    if station.isconnected()!=False:
        network_fail = 0
        try:
            client = MQTTClient(client_id, mqtt_server, user=mqtt_un, password=mqtt_pw)
            client.set_callback(sub_cb)
            client.connect()
            client.subscribe(topic_sub)
            print('Connected to %s MQTT broker, subscribed to %s topic' % (mqtt_server, topic_sub))
            return client
        except:
            print('Could not connect to %s MQTT broker, nor subscribe to %s topic' % (mqtt_server, topic_sub))


def restart_and_reconnect():
    global mqtt_fail, max_mqtt_fail
    mqtt_fail += 1
    print('Failed to connect to MQTT. Retrying...'+str(mqtt_fail))
    connect_and_subscribe()
    if mqtt_fail > max_mqtt_fail:
        print('Failed to connect to MQTT. Restarting ESP...')
        try:
            client.disconnect()
            station.disconnect()
        except:
            pass
        time.sleep(1)
        gc.collect()
        machine.reset()
  
try:
    client = connect_and_subscribe()
except:
    restart_and_reconnect()
  
###############################################################################
    

    
rtc = RTC()
ntptime.settime()
ntptime.host = '<your-ntp-server-address>'

f_utc_offset = open("utc_offset.var","r")
try:
    timezone_hour = int(f_utc_offset.read())
except:
    timezone_hour = 0 # Defaulting to UTC
f_utc_offset.close()

try:
    sec = ntptime.time()
    timezone_sec = timezone_hour * 3600
    sec = int(sec + timezone_sec)
    (year, month, day, hours, minutes, seconds, weekday, yearday) = time.localtime(sec)
    rtc.datetime((year, month, day, 0, hours, minutes, seconds, 0))
    print("RTC Synced to NTP Server succesfully")
    print(str(hours)+":"+str(minutes)+":"+str(seconds))
    ntp_sync_err = 0
    counter += 1
except:
    print("RTC sync to NTP Server Failed")
    hours = 0
    minutes = 0
    seconds = 0
    ntp_sync_err += 3

while True:
    if station.isconnected()==False:
        try:
            connect()
        except:
            network_fail += 1
            print('Failed to connect to Wifi. Retrying...'+str(network_fail))
            if network_fail > max_network_fail:
                print('Failed to connect to Wifi. Restarting ESP...')
                try:
                    client.disconnect()
                    station.disconnect()
                except:
                    pass
                time.sleep(1)
                gc.collect()
                machine.reset()
                
    if station.isconnected()!=False:                
        network_fail = 0
    
    try:
        new_msg = client.check_msg()
    except:
        restart_and_reconnect()
   
    if string=="" or string=='None':
        if counter%status_cycle==0:
            try:
                f_utc_offset = open("utc_offset.var","r")
                try:
                    timezone_hour = int(f_utc_offset.read())
                except:
                    pass
                f_utc_offset.close()

                sec = ntptime.time()
                timezone_sec = timezone_hour * 3600
                sec = int(sec + timezone_sec)
                (year, month, day, hours, minutes, seconds, weekday, yearday) = time.localtime(sec)
                rtc.datetime((year, month, day, 0, hours, minutes, seconds, 0))
                print("RTC sync to NTP Server succesfull")
                ntp_sync_err = 0
            except:
                print("RTC sync to NTP Server Failed")
                ntp_sync_err += 1
  #          print(str(hours)+":"+str(minutes)+":"+str(seconds))
        else:
            (year, month, day, weekday, hours, minutes, seconds, subseconds) = rtc.datetime()
  #          print(str(hours)+":"+str(minutes)+":"+str(seconds))
            
        if counter%600==0:
            try:
                client.publish(topic_pub, "time "+str(hours)+":"+str(minutes)+":"+str(seconds))
            except:
                pass
        hours = int(hours)
        am_or_pm = "A"
        if hours>=12:
            am_or_pm = "P"
        if hours>12:
            hours=hours-12
        if hours==0:
            hours = 12
        if hours<10:
            hours = " "+str(hours)
        if minutes<10:
            minutes = "0"+str(minutes)
        if counter%2==0:
            time_seperator = ":"
        else:
            time_seperator = " "
        if network_fail>2:
            if counter%6==0:
                am_or_pm = am_or_pm+"w"
            elif counter%6==1:
                am_or_pm = am_or_pm+"i"
            elif counter%6==2:
                am_or_pm = am_or_pm+"f"
            elif counter%6==3:
                am_or_pm = am_or_pm+"i"
            elif counter%6==4:
                am_or_pm = am_or_pm+"!"
            else:
                am_or_pm = am_or_pm+"."
        elif ntp_sync_err>2:
            if counter%5==0:
                am_or_pm = am_or_pm+"n"
            elif counter%5==1:
                am_or_pm = am_or_pm+"t"
            elif counter%5==2:
                am_or_pm = am_or_pm+"p"
            elif counter%5==3:
                am_or_pm = am_or_pm+"!"
            else:
                am_or_pm = am_or_pm+"."
            if ntp_sync_err>100:
                   ntp_sync_err = 101
        if timezone_hour==0 and counter%2==0:
            am_or_pm = "UT"
        string = " "+str(hours)+time_seperator+str(minutes)+str(am_or_pm)
        clock = string
#        print(string)
        cycle_time = 0.5
        screen.fill(0)
        screen.text(string, 0, 0, 1)
        screen.show()
    else:
        if len(string)<9:
            cycle_time = 3
            screen.fill(0)
            screen.text(string, 0, 0, 1)
            screen.show()
        else:
            cycle_time = 1
            msg_length = len(string)
            msg_length = (msg_length*8)
            screen.fill(0)
            for x in range (64, -msg_length, -1):
                screen.text(string, x, 0, 1)
                screen.show()
                time.sleep(0.05)
                screen.fill(0)
    
    counter += 1
    if counter>=7200:
        counter = 0
    string = ""
    time.sleep(cycle_time)
    screen.fill(0)
  
try:
    disconnect()
except:
    pass
time.sleep(5)
gc.collect()
machine.reset()
