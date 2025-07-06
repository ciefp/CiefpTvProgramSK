# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import logging
import requests
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Tools.LoadPixmap import LoadPixmap
import datetime
import time
from lxml import etree

PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpTvProgramSK"
EPG_DIR = "/tmp/CiefpProgramSK"
PICON_DIR = os.path.join(PLUGIN_PATH, "picon")
PLACEHOLDER_PICON = os.path.join(PLUGIN_PATH, "placeholder.png")
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_SK1.xml.gz"
CACHE_TIME = 86400  # 24 hours caching

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/ciefp_tvprogramsk.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def clean_channel_name(name):
    # Zadržava samo alfanumeričke karaktere i tačke, zatim pretvara u mala slova
    return ''.join(e.lower() if e.isalnum() or e == '.' else '' for e in name).strip()

class CiefpTvProgramSK(Screen):
    skin = """
        <screen name="CiefpTvProgramSK" position="center,center" size="1800,800" title="..:: CiefpTvProgramSK v1.0 ::..">
            <widget name="channelList" position="0,0" size="350,668" scrollbarMode="showAlways" itemHeight="33" font="Regular;28" />
            <widget name="epgInfo" position="370,0" size="1000,668" scrollbarMode="showAlways" itemHeight="33" font="Regular;28" />
            <widget name="sideBackground" position="1380,0" size="420,668" alphatest="on" />
            <widget name="picon" position="0,668" size="220,132" alphatest="on" />
            <widget name="pluginLogo" position="220,668" size="220,132" alphatest="on" />
            <widget name="backgroundLogo" position="440,668" size="1360,132" alphatest="on" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self["channelList"] = MenuList([], enableWrapAround=True)
        self["epgInfo"] = MenuList([], enableWrapAround=True)
        self["picon"] = Pixmap()
        self["pluginLogo"] = Pixmap()
        self["backgroundLogo"] = Pixmap()
        self["sideBackground"] = Pixmap()

        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"],
            {
                "ok": self.switchView,
                "cancel": self.exit,
                "up": self.up,
                "down": self.down
            }, -1)

        self.currentView = "channels"
        self.epgData = {}
        self.channelData = []
        self.epgLines = []
        self.epgScrollPos = 0
        self.focus_on_channels = True

        # Create directories if they don't exist
        for directory in [EPG_DIR, PICON_DIR]:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory)
                    logger.debug(f"Created directory: {directory}")
                except Exception as e:
                    logger.error(f"Error creating directory {directory}: {str(e)}")
                    self["epgInfo"].setList([f"Error: {str(e)}"])

        self.onLayoutFinish.append(self.loadPluginLogo)
        self.onLayoutFinish.append(self.loadBackgroundLogo)
        self.onLayoutFinish.append(self.loadSideBackground)
        self.onLayoutFinish.append(self.downloadAndParseData)

    def downloadAndParseData(self):
        cache_file = os.path.join(EPG_DIR, "epg_cache.xml")
        
        # Check cache first
        if os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file)) < CACHE_TIME:
            try:
                with open(cache_file, 'r') as f:
                    xml_data = f.read()
                logger.debug("Using cached EPG data")
                self.parseXMLData(xml_data)
                return
            except Exception as e:
                logger.error(f"Error reading cache: {str(e)}")

        try:
            # Download fresh EPG data
            logger.debug(f"Downloading EPG data from: {EPG_URL}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-US,en;q=0.5"
            }
            response = requests.get(EPG_URL, headers=headers, timeout=30)
            response.raise_for_status()

            # Decompress and parse
            with gzip.GzipFile(fileobj=BytesIO(response.content)) as gz:
                xml_data = gz.read().decode('utf-8')

            # Save to cache
            try:
                with open(cache_file, 'w') as f:
                    f.write(xml_data)
                logger.debug("EPG data saved to cache")
            except Exception as e:
                logger.error(f"Error saving cache: {str(e)}")

            self.parseXMLData(xml_data)

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {str(e)}")
            self["epgInfo"].setList([f"Network error: {str(e)}"])
        except Exception as e:
            logger.error(f"General error: {str(e)}")
            self["epgInfo"].setList([f"Error: {str(e)}"])

    def parseXMLData(self, xml_data):
        try:
            # Using lxml.etree for more robust parsing
            parser = etree.XMLParser(encoding='utf-8', recover=True)
            tree = etree.fromstring(xml_data.encode('utf-8'), parser=parser)

            self.channelData = []
            self.epgData = {}

            # Parse channels
            for channel in tree.xpath('//channel'):
                channel_id = channel.get('id')
                display_name = channel.xpath('display-name[1]/text()')
                icon = channel.xpath('icon[1]/@src')

                if not channel_id or not display_name:
                    continue

                channel_name = display_name[0].strip()
                self.channelData.append({
                    "id": channel_id,
                    "title": channel_name,
                    "alias": clean_channel_name(channel_name),
                    "logo": f"{clean_channel_name(channel_name)}.png",
                    "icon": icon[0] if icon else None
                })
                self.epgData[channel_name] = []

            logger.debug(f"Found {len(self.channelData)} channels")

            if not self.channelData:
                self["epgInfo"].setList(["No channels found in EPG data"])
                self["channelList"].setList(["No channels available"])
                return

            self["channelList"].setList([ch["title"] for ch in self.channelData])

            # Parse programs
            for program in tree.xpath('//programme'):
                channel_id = program.get('channel')
                start_time = program.get('start')
                stop_time = program.get('stop')
                title = program.xpath('title[1]/text()')
                desc = program.xpath('desc[1]/text()')
                category = program.xpath('category[1]/text()')
                icon = program.xpath('icon[1]/@src')

                if not (channel_id and start_time and title):
                    continue

                channel = next((ch for ch in self.channelData if ch['id'] == channel_id), None)
                if not channel:
                    continue

                channel_name = channel['title']
                program_data = {
                    'title': title[0].strip() if title else "Nepoznat naslov",
                    'desc': desc[0].strip() if desc else "Nema opisa",
                    'category': category[0].strip() if category else "",
                    'icon': icon[0] if icon else None
                }

                try:
                    time_str = start_time.split(' ')[0]
                    time_obj = datetime.datetime.strptime(time_str, '%Y%m%d%H%M%S')
                    start_timestamp = int(time_obj.timestamp())
                    if stop_time:
                        stop_time_str = stop_time.split(' ')[0]
                        stop_time_obj = datetime.datetime.strptime(stop_time_str, '%Y%m%d%H%M%S')
                        program_data['stop_timestamp'] = int(stop_time_obj.timestamp())
                    else:
                        program_data['stop_timestamp'] = None
                    program_data['start_timestamp'] = start_timestamp
                    self.epgData[channel_name].append(program_data)
                except ValueError as e:
                    logger.error(f"Time parsing error: {str(e)}")
                    continue

            self.updateEPGAndPicon()

        except Exception as e:
            logger.error(f"XML parsing error: {str(e)}")
            self["epgInfo"].setList([f"Error parsing EPG data: {str(e)}"])
            self["channelList"].setList(["Error loading channels"])

    def getEPGFromData(self, channel_name):
        epglist = self.epgData.get(channel_name, [])
        if not epglist:
            return [f"No EPG data for channel: {channel_name}"]

        epg_by_date = {}
        for program in sorted(epglist, key=lambda x: x['start_timestamp']):
            try:
                date_str = datetime.datetime.fromtimestamp(program['start_timestamp']).strftime('%Y%m%d')
                date_formatted = datetime.datetime.fromtimestamp(program['start_timestamp']).strftime('%d.%m.%Y')
                time_str = datetime.datetime.fromtimestamp(program['start_timestamp']).strftime('%H:%M')
                entry = f"{time_str} - {program['title']} ({program['category']})"
                if program['desc']:
                    entry += f"\n  {program['desc']}"
                if date_str not in epg_by_date:
                    epg_by_date[date_str] = []
                epg_by_date[date_str].append(entry)
            except ValueError as e:
                logger.error(f"Time formatting error: {str(e)}")
                continue

        result = []
        for date_str in sorted(epg_by_date.keys()):
            date_formatted = datetime.datetime.strptime(date_str, '%Y%m%d').strftime('%d.%m.%Y')
            result.append(f"--- {date_formatted} ---")
            result.extend(epg_by_date[date_str])
        
        if not result:
            return [f"No valid EPG data for channel: {channel_name}"]
        return result

    def loadPicon(self, channel_name):
        channel = next((ch for ch in self.channelData if ch["title"] == channel_name), None)
        if not channel:
            return

        # Lista mogućih naziva pikona
        possible_picon_names = [
            channel["logo"],
            channel["alias"] + ".png",
            channel["title"].replace(" ", "_") + ".png",
            channel["title"].replace(" ", "").lower() + ".png"
        ]

        pixmap = None

        # Provera svakog mogućeg naziva pikona
        for picon_name in possible_picon_names:
            filename = os.path.join(PICON_DIR, picon_name)
            logger.debug(f"Checking for picon: {filename}")  # Dodajte ovu liniju za praćenje
            if os.path.exists(filename):
                try:
                    pixmap = LoadPixmap(filename)
                    logger.debug(f"Picon loaded successfully: {filename}")  # Dodajte ovu liniju za uspešno učitavanje
                    break
                except Exception as e:
                    logger.error(f"Error loading picon: {str(e)}")

        # Ako nije pronađen nikakav picon, koristi se placeholder
        if not pixmap and os.path.exists(PLACEHOLDER_PICON):
            try:
                pixmap = LoadPixmap(PLACEHOLDER_PICON)
                logger.debug(f"Using placeholder picon: {PLACEHOLDER_PICON}")
            except Exception as e:
                logger.error(f"Error loading placeholder: {str(e)}")

        # Postavljanje pikona na widget
        if pixmap and self["picon"].instance:
            try:
                self["picon"].instance.setPixmap(pixmap)
            except Exception as e:
                logger.error(f"Error setting picon: {str(e)}")

    def updateEPGAndPicon(self):
        current = self["channelList"].getCurrent()
        if current:
            channel_name = current
            self.epgLines = self.getEPGFromData(channel_name)
            if self.epgLines:
                self["epgInfo"].setList(self.epgLines)
                
                # Find current program
                now = datetime.datetime.now()
                current_index = 0
                for i, line in enumerate(self.epgLines):
                    if not line.startswith("---"):
                        try:
                            time_str = line.split(" - ")[0]
                            epg_time = datetime.datetime.strptime(
                                f"{now.day}.{now.month}.{now.year} {time_str}",
                                "%d.%m.%Y %H:%M"
                            )
                            if epg_time <= now:
                                current_index = i
                            else:
                                break
                        except Exception as e:
                            logger.debug(f"EPG line parsing error: {str(e)}")
                
                self.epgScrollPos = current_index
                self["epgInfo"].moveToIndex(self.epgScrollPos)
            
            self.loadPicon(channel_name)
        else:
            self["epgInfo"].setList(["Select a channel to view EPG"])

    def switchView(self):
        self.currentView = "epg" if self.currentView == "channels" else "channels"
        self.focus_on_channels = self.currentView == "channels"
        self.epgScrollPos = 0
        self["channelList"].instance.setSelectionEnable(self.focus_on_channels)
        self["epgInfo"].instance.setSelectionEnable(not self.focus_on_channels)
        logger.debug(f"Switched focus to {'channels' if self.focus_on_channels else 'EPG'}")
        self.updateEPGAndPicon()

    def exit(self):
        self.close()

    def up(self):
        if self.currentView == "channels":
            self["channelList"].up()
            self.updateEPGAndPicon()
        else:
            self["epgInfo"].up()

    def down(self):
        if self.currentView == "channels":
            self["channelList"].down()
            self.updateEPGAndPicon()
        else:
            self["epgInfo"].down()

    def loadPluginLogo(self):
        logo_path = os.path.join(PLUGIN_PATH, "plugin_logo.png")
        if os.path.exists(logo_path):
            try:
                pixmap = LoadPixmap(logo_path)
                if pixmap and self["pluginLogo"].instance:
                    self["pluginLogo"].instance.setPixmap(pixmap)
            except Exception as e:
                logger.error(f"Error loading plugin logo: {str(e)}")

    def loadBackgroundLogo(self):
        logo_path = os.path.join(PLUGIN_PATH, "background_logo.png")
        if os.path.exists(logo_path):
            try:
                pixmap = LoadPixmap(logo_path)
                if pixmap and self["backgroundLogo"].instance:
                    self["backgroundLogo"].instance.setPixmap(pixmap)
            except Exception as e:
                logger.error(f"Error loading background logo: {str(e)}")

    def loadSideBackground(self):
        bg_path = os.path.join(PLUGIN_PATH, "side_background.png")
        if os.path.exists(bg_path):
            try:
                pixmap = LoadPixmap(bg_path)
                if pixmap and self["sideBackground"].instance:
                    self["sideBackground"].instance.setPixmap(pixmap)
            except Exception as e:
                logger.error(f"Error loading side background: {str(e)}")

def main(session, **kwargs):
    session.open(CiefpTvProgramSK)

def Plugins(**kwargs):
    return [PluginDescriptor(
        name="CiefpTvProgramSK",
        description="EPG plugin,epgshare v1.0",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="icon.png",
        fnc=main
    )]