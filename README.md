
# CiefpTvProgramSK 

- **Version: 1.1**
- **Author: Ciefp**

![Bouquet](https://github.com/ciefp/CiefpTvProgramSK/blob/main/ciefptvprogramsk.jpg)

- **CiefpTvProgramSK is an Enigma2 plugin designed to display the Electronic Program Guide (EPG) for TV channels,**
- **using data downloaded from https://epgshare01.online/epgshare01/epg_ripper_SK1.xml.gz.**
- **The plugin allows users to view the channel list and detailed EPG information, including show names, broadcast times, descriptions and categories.**
- **It supports the display of picons (channel icons), plugin logos and background graphics, with data caching for faster loading.**
- **The interface is intuitive, with navigation between the channel list and EPG information, and is adapted for the Enigma2 platform.**

# Using the plugin

# Navigation:
- **Channel list: The left side of the screen displays a list of available channels downloaded from an XML file.**
- **EPG information: The right side displays program details for the selected channel (time, title, description, category).**
- **Use the Up/Down keys to navigate through the channel list or EPG information, depending on the current focus.**
- **Press OK to switch focus between the channel list and EPG information.**
- **Press Cancel (or Exit) to exit the plugin.**

# Functionalities:
- **Picon display: The icon of the selected channel is displayed at the bottom of the screen if available in the folder /usr/lib/enigma2/python/Plugins/Extensions/CiefpTvProgramSK/picon.**
- **If the icon is not found, the default icon (placeholder.png) is used.**
- **Data caching: EPG data is cached in /tmp/CiefpProgramSK/epg_cache.xml for 24 hours to reduce data downloads.**
- **Logging: The plugin logs activities and errors in the file /tmp/ciefp_tvprogramsk.log for diagnostics.**

# ..:: CiefpSettings ::..