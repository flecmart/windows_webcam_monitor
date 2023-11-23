from winreg import *
from contextlib import suppress
import itertools
import time
import configparser
import traceback
import paho.mqtt.client as mqtt

_connected_to_mqtt = False

def _subkeys(path, key, flags=0):
    with suppress(WindowsError), OpenKey(key, path, 0, KEY_READ|flags) as k:
        for i in itertools.count():
            yield EnumKey(k, i)

def _webcam_used(key):
    try:
        webcam_currently_in_use = QueryValueEx(key, "LastUsedTimeStop")[0] == 0
    except:
        webcam_currently_in_use = False
    return webcam_currently_in_use

def _webcam_used_by(registry_key):
    for key in _subkeys(registry_key, HKEY_CURRENT_USER):
        subkey = OpenKey(HKEY_CURRENT_USER, f'{registry_key}\{key}')
        if (_webcam_used(subkey)):
            return key
    
    return None

def get_app_using_webcam():
    return \
        _webcam_used_by(r'SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam\NonPackaged') or \
        _webcam_used_by(r'SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam')
    
def get_executable_name_from_registry_key(key):
    return key.split('#')[-1] if '#' in key else key.split('_')[0]

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
                used_by = get_app_using_webcam()
                if used_by != None:
                    if config['mqtt'].getboolean('publishFullPath') == False:
                        used_by = get_executable_name_from_registry_key(used_by)
                    client.publish(config['mqtt']['topic'], used_by)
                else:
                    client.publish(config['mqtt']['topic'], 'off')
            except Exception:
                traceback.print_exception()

            time.sleep(int(config['service']['interval_in_s']))