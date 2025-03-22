# -*- coding: utf-8 -*-

# --- Kodi modules ---
try:
    import xbmc
    import xbmcaddon
    import xbmcgui
    import xbmcplugin
    import xbmcvfs
except:
    KODI_RUNTIME_AVAILABLE_UTILS = False
else:
    KODI_RUNTIME_AVAILABLE_UTILS = True

# --- Python standard library ---
# Check what modules are really used and remove not used ones.
import collections
import datetime
import errno
import fnmatch
import io
import json
import math
import os
import re
import shutil
import string
import sys
import threading
import time
import xml.etree.ElementTree
import xml.etree.ElementTree as ET
import zlib

ADDON_NAME = "Steam Games"

# Updates the mtime of a local file.
# This is to force and update of the image cache.
# stat.ST_MTIME is the time in seconds since the epoch.
def utils_update_file_mtime(fname_str):
    
    kodi_dialog_OK('utils_update_file_mtime() Updating "{}"'.format(fname_str))
    
    # log_debug('utils_update_file_mtime() Updating "{}"'.format(fname_str))
    filestat = os.stat(fname_str)
    time_str = time.ctime(filestat.st_mtime)
    
    kodi_dialog_OK('utils_update_file_mtime()     Old mtime "{}"'.format(time_str))
    # log_debug('utils_update_file_mtime()     Old mtime "{}"'.format(time_str))
    os.utime(fname_str)
    filestat = os.stat(fname_str)
    time_str = time.ctime(filestat.st_mtime)
    kodi_dialog_OK('utils_update_file_mtime() Current mtime "{}"'.format(time_str))
    # log_debug('utils_update_file_mtime() Current mtime "{}"'.format(time_str))

def text_limit_string(string, max_length):
    if max_length > 5 and len(string) > max_length:
        string = string[0:max_length-3] + '.'
    return string

def kodi_log(string):
    xbmc.log('{} LOGINFO: {}'.format(ADDON_NAME, string),level=xbmc.LOGINFO)    
    
# -------------------------------------------------------------------------------------------------
# Kodi notifications and dialogs
# -------------------------------------------------------------------------------------------------
# Displays a modal dialog with an OK button. Dialog can have up to 3 rows of text, however first
# row is multiline.
# Call examples:
#  1) ret = kodi_dialog_OK('Launch ROM?')

#  2) ret = kodi_dialog_OK('Launch ROM?', title = 'AML - Launcher')
def kodi_dialog_OK(text, title = ADDON_NAME):
    xbmcgui.Dialog().ok(title, text)   
    
# Returns True is YES was pressed, returns False if NO was pressed or dialog canceled.
def kodi_dialog_yesno(text, title = ADDON_NAME):
    return xbmcgui.Dialog().yesno(title, text)

# Returns True is YES was pressed, returns False if NO was pressed or dialog canceled.
def kodi_dialog_yesno_custom(text, yeslabel_str, nolabel_str, title = ADDON_NAME):
    return xbmcgui.Dialog().yesno(title, text, yeslabel = yeslabel_str, nolabel = nolabel_str)

def kodi_dialog_yesno_timer(text, timer_ms = 30000, title = ADDON_NAME):
    return xbmcgui.Dialog().yesno(title, text, autoclose = timer_ms)
    
# Displays a small box in the bottom right corner
def kodi_notify(text, title = ADDON_NAME, time = 3000):
    xbmcgui.Dialog().notification(title, text, xbmcgui.NOTIFICATION_INFO, time)

def kodi_notify_warn(text, title = ADDON_NAME, time = 3000):
    xbmcgui.Dialog().notification(title, text, xbmcgui.NOTIFICATION_WARNING, time)

# Do not use this function much because it is the same icon displayed when Python fails
# with an exception and that may confuse the user.
def kodi_notify_error(text, title = ADDON_NAME, time = 5000):
    xbmcgui.Dialog().notification(title, text, xbmcgui.NOTIFICATION_ERROR, time)

def kodi_refresh_container():
    xbmc.log('kodi_refresh_container()')
    xbmc.executebuiltin('Container.Refresh')
 
# Returns a directory.
def kodi_dialog_get_directory(d_heading, d_dir = ''):
    if d_dir:
        ret = xbmcgui.Dialog().browse(0, d_heading, '', defaultt = d_dir)
    else:
        ret =  xbmcgui.Dialog().browse(0, d_heading, '')

    return ret
 
def kodi_dialog_get_image(d_heading, mask = '', default_file = ''):
    if mask and default_file:
        ret = xbmcgui.Dialog().browse(2, d_heading, '', mask = mask, defaultt = default_file)
    elif default_file:
        ret = xbmcgui.Dialog().browse(2, d_heading, '', defaultt = default_file)
    elif mask:
        ret = xbmcgui.Dialog().browse(2, d_heading, '', mask = mask)
    else:
        ret = xbmcgui.Dialog().browse(2, d_heading, '')

    return ret
 
def save_timestamp(path):
    # Obter o timestamp Unix atual
    timestamp_unix = int(datetime.datetime.now().timestamp())

    # Criar o dicionário com o timestamp Unix
    timestamp_data = {
        "last_scan": timestamp_unix
    }

    timestamp_json_path = os.path.join(path, '_scan_timestamp.json')

    try:
        with open(timestamp_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(timestamp_data, json_file, ensure_ascii=False, indent=4)
    except Exception as e:
        kodi_notify_error(f'Error saving timestamp JSON: {str(e)}')

def read_nfo_data(nfo_file):
    """
    Lê um arquivo NFO e retorna os dados estruturados.
    :param nfo_file: Caminho para o arquivo NFO.
    :return: Dicionário com os dados do jogo extraídos do NFO.
    """
    if not os.path.exists(nfo_file):
        return {}
    
    try:
        tree = ET.parse(nfo_file)
        root = tree.getroot()

        return {
            "title": root.findtext("title", default=""),
            "year": root.findtext("year", default=""),
            "genre": root.findtext("genre", default=""),
            "tags": root.findtext("tags", default=""),
            "developer": root.findtext("developer", default=""),
            "nplayers": root.findtext("nplayers", default=""),
            "esrb": root.findtext("esrb", default=""),
            "rating": root.findtext("rating", default=""),
            "plot": root.findtext("plot", default="")
        }
    except ET.ParseError as e:
        xbmcgui.Dialog().notification("Erro", f"Falha ao processar o NFO: {str(e)}", xbmcgui.NOTIFICATION_ERROR, 5000)
        return {}



def format_last_play_time(seconds):
    """
    Converte o tempo em segundos (Unix Epoch) para uma data legível no formato YYYY-MM-DD.
    """
    try:
        return datetime.datetime.utcfromtimestamp(int(seconds)).strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return ""  # Retorna vazio se não for possível converter
        
        
        
# Wrapper class for xbmcgui.Dialog().select(). Takes care of Kodi bugs.
# v17 (Krypton) Python API changes:
#   Preselect option added.
#   Added new option useDetails.
#   Allow listitems for parameter list
class KodiSelectDialog(object):
    def __init__(self, heading = ADDON_NAME, rows = [], preselect = -1, useDetails = False):
        self.heading = heading
        self.rows = rows
        self.preselect = preselect
        self.useDetails = useDetails
        self.dialog = xbmcgui.Dialog()

    def setHeading(self, heading): self.heading = heading

    def setRows(self, row_list): self.rows = row_list

    def setPreselect(self, preselect): self.preselect = preselect

    def setUseDetails(self, useDetails): self.useDetails = useDetails

    def executeDialog(self):
        selection = self.dialog.select(self.heading, self.rows, useDetails = self.useDetails)
        selection = None if selection < 0 else selection   
        return selection
