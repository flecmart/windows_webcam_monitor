from winreg import *
from contextlib import suppress
import itertools
import time
import configparser
import traceback
import paho.mqtt.client as mqtt

_connected_to_mqtt = False

def subkeys(path, key, flags=0):
    with suppress(WindowsError), OpenKey(key, path, 0, KEY_READ|flags) as k:
        for i in itertools.count():
            yield EnumKey(k, i)

def webcam_used(key):
    return QueryValueEx(key, "LastUsedTimeStop")[0] == 0

def webcam_used_by():
    webcam_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam\NonPackaged'

    for key in subkeys(webcam_key, HKEY_CURRENT_USER):
        subkey = OpenKey(HKEY_CURRENT_USER, f'{webcam_key}\{key}')
        if (webcam_used(subkey)):
            return key
    
    return None

def get_executable_name_from_path(path):
    return path.split("#")[-1]

def on_connect(client, userdata, flags, rc):
    global _connected_to_mqtt
    if rc == 0:
        _connected_to_mqtt = True
    else:
        _connected_to_mqtt = False
        
def on_disconnect(client, userdata, rc):
    global _connected_to_mqtt
    _connected_to_mqtt = False
        
if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.ini')
    client = mqtt.Client(client_id='windows_webcam_monitor')
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=300)
    client.username_pw_set(config['mqtt']['user'], config['mqtt']['password'])
    client.connect(config['mqtt']['hostname'], int(config['mqtt']['port']))
    client.loop_start() # reconnects are handled automatically
    
    while True:
        if _connected_to_mqtt:
            try:
                used_by = webcam_used_by()
                if used_by != None:
                    if config['mqtt'].getboolean('publishFullPath') == False:
                        used_by = get_executable_name_from_path(used_by)
                    client.publish(config['mqtt']['path'], used_by)
                else:
                    client.publish(config['mqtt']['path'], 'off')
            except Exception:
                traceback.print_exception()

            time.sleep(int(config['service']['interval_in_s']))