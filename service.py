from winreg import *
from contextlib import suppress
import itertools
import time
import configparser
import paho.mqtt.client as mqtt

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

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.ini')
    client = mqtt.Client(client_id='windows_webcam_monitor')
    client.username_pw_set(config['mqtt']['user'], config['mqtt']['password'])
    client.connect(config['mqtt']['hostname'], int(config['mqtt']['port']))
    client.loop_start()

    while True:
        used_by = webcam_used_by()
        if used_by != None:
            client.publish(config['mqtt']['path'], used_by)
        else:
            client.publish(config['mqtt']['path'], 'off')
        
        time.sleep(int(config['service']['interval_in_s']))