"""
The variables file is for data that will be used throughout the project.  This could be static or
dynamic data.  After being initial loaded by main.py, it can be imported and used in any module
throughout the system.
"""

# ========================================================================================
# UI Navigation
# ========================================================================================

PAGES = {
    'Splash': 'Splash',
    'Main': 'Main',
}

POPUPS = {
    'Powering Down': 'Powering Down',
    'Confirmation': 'Confirmation',
    'Starting Up': 'Starting Up',
    'Help': 'Help',
}

# ========================================================================================
# DSP Configuration - DMP 128 FlexPlus
# ========================================================================================

# DSP Output Channel Assignments (to Amp - each output goes to a speaker zone)
# Output 1: Gym
# Output 2: Yoga Studio
# Output 3: Terrace Gallery
# Output 4: Party Room
# Output 5: Courtyard
DSP_OUTPUTS = {
    'Gym': '1',
    'YogaStudio': '2',
    'TerraceGallery': '3',
    'PartyRoom': '4',
    'Courtyard': '5',
}

# DSP Analog Input Assignments
# Analog Input 1: Music Player (BGM)
DSP_ANALOG_INPUTS = {
    'MusicPlayer': '1',
}

# DSP Dante Input Assignments
# Dante 1-4: Yoga Studio BT/Aux Wall Plate → Virtual Send A (1-4)
# Dante 5-8: Party Room BT Wall Plate → Virtual Send B (5-8)
# Dante 9: Yoga Studio TV Audio
# Dante 10: Terrace Gallery TV 1 Audio
# Dante 11: Terrace Gallery TV 2 Audio
# Dante 12: Party Room TV Audio
DSP_DANTE_INPUTS = {
    'BTPlate_YogaStudio_1': '1',
    'BTPlate_YogaStudio_2': '2',
    'BTPlate_YogaStudio_3': '3',
    'BTPlate_YogaStudio_4': '4',
    'BTPlate_PartyRoom_1': '5',
    'BTPlate_PartyRoom_2': '6',
    'BTPlate_PartyRoom_3': '7',
    'BTPlate_PartyRoom_4': '8',
    'YogaStudioTV': '9',
    'TerraceGalleryTV1': '10',
    'TerraceGalleryTV2': '11',
    'PartyRoomTV': '12',
}

# DSP Virtual Receive Assignments
# Virtual Receive A-D: From Virtual Send A (Yoga Studio BT Plate Dante 1-4)
# Virtual Receive E-H: From Virtual Send B (Party Room BT Plate Dante 5-8)
DSP_VIRTUAL_RECEIVES = {
    'VirtualReceiveA': 'A',
    'VirtualReceiveB': 'B',
    'VirtualReceiveC': 'C',
    'VirtualReceiveD': 'D',
    'VirtualReceiveE': 'E',
    'VirtualReceiveF': 'F',
    'VirtualReceiveG': 'G',
    'VirtualReceiveH': 'H',
}

# Combined input references for routing (type indicates Analog, Dante, or VirtualReceive)
DSP_INPUTS = {
    'MusicPlayer': {'Type': 'Analog', 'Channel': '1'},
    'BTPlate_YogaStudio': {'Type': 'VirtualReceive', 'Channel': 'A'},  # Virtual Receive A
    'BTPlate_PartyRoom': {'Type': 'VirtualReceive', 'Channel': 'B'},   # Virtual Receive B
    'YogaStudioTV': {'Type': 'VirtualReceive', 'Channel': 'C'},        # Virtual Receive C (from Dante 9)
    'TerraceGalleryTV1': {'Type': 'VirtualReceive', 'Channel': 'D'},   # Virtual Receive D (from Dante 10)
    'TerraceGalleryTV2': {'Type': 'VirtualReceive', 'Channel': 'E'},   # Virtual Receive E (from Dante 11)
    'PartyRoomTV': {'Type': 'VirtualReceive', 'Channel': 'F'},         # Virtual Receive F (from Dante 12)
}

# Maps each room to its TV input source (used to clear TV routing when switching to Music/BT)
ROOM_TV_SOURCE = {
    'YogaStudio': 'YogaStudioTV',
    'PartyRoom': 'PartyRoomTV',
}

# Audio Source Mapping for each room (for source selection buttons)
AUDIO_SOURCES = {
    'PartyRoom': {
        'MusicPlayer': {'Type': 'Analog', 'Channel': '1'},
        'BTPlate': {'Type': 'VirtualReceive', 'Channel': 'B'},  # Virtual Receive B
    },
    'YogaStudio': {
        'MusicPlayer': {'Type': 'Analog', 'Channel': '1'},
        'BTPlate': {'Type': 'VirtualReceive', 'Channel': 'A'},  # Virtual Receive A
    },
}

# Volume ranges (DSP uses -100 to 0 dB typically, UI slider 0-100)
VOLUME_MIN = 0
VOLUME_MAX = 100
DSP_VOLUME_MIN = -100  # dB
DSP_VOLUME_MAX = 0     # dB

# ========================================================================================
# Display Configuration
# ========================================================================================

DISPLAY_DEFAULT_INPUT = 'HDMI 1'

# Input options for Samsung displays (QBxxC series)
DISPLAY_INPUTS_QB = {
    'HDMI1': 'HDMI 1',
    'HDMI2': 'HDMI 2',
    'HDMI3': 'HDMI 3',
    'DisplayPort': 'DisplayPort',
    'MagicInfo': 'MagicInfo',
}

# Input options for Samsung displays (QN series - Terrace Gallery)
DISPLAY_INPUTS_QN = {
    'TV': 'TV',
    'HDMI1': 'HDMI 1',
    'HDMI2': 'HDMI 2',
    'HDMI3': 'HDMI 3',
    'HDMI4': 'HDMI 4',
}