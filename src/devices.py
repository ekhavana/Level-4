"""
This is the place to define each of the devices in the system.
* Extron control devices (e.g. all extronlib.device objects)
* Non-control devices and services (e.g. device modules)
* User defined devices (e.g. all extronlib.interface objects or custom python coded devices)

Note: This is for definition only.  Connection and logic defined in system.py (see below).
"""

# Extron Library imports
from extronlib.device import ProcessorDevice, UIDevice
from extronlib.interface import (EthernetClientInterface)

# Module imports
from modules.helper.ConnectionHandler import GetConnectionHandler
import modules.device.extr_dsp_DMP128_FlexPlus_v1_0_9_0 as modDSP
import modules.device.smsg_display_QBxxC_QHxxC_QMxxC_Series_v1_0_4_0 as modSamsungTV
import modules.device.smsg_display_QNxxLS03DAFXZA_Series_v1_0_0_0 as modSamsungTVQN
import modules.device.smsg_display_Tizen_WebSocket_v1_0_0_0 as modSamsungTizenWS

# Define devices
##Control Processors
MainProcessor = ProcessorDevice('Level4Controller')

##UI Devices
dvTLPYogaStudio = UIDevice('YogaStudioTouchPanel')
dvPartyRoomTLP = UIDevice('PartyRoomTouchPanel')
dvTerraceGalleryTLP1 = UIDevice('TerraceGalleryTouchPanel')
dvTerraceGalleryTLP2 = UIDevice('TerraceGallery2TouchPanel')

##Control Devices
# Define any control devices here (e.g. extronlib.device objects, custom python coded devices, etc.)

# Create DSP module interface first
_moduleInterfaceDSP = modDSP.SSHClass('172.22.10.223', 22023, Credentials=('admin', 'extron'), Model='DMP 128 FlexPlus C AT')
# Wrap with ConnectionHandler for automatic reconnection and keep-alive polling
dvDSPLevel4 = GetConnectionHandler(_moduleInterfaceDSP, 'PartNumber', pollFrequency=3)

# Create display module interfaces
_moduleInterfacePartyRmDisplay = modSamsungTV.EthernetClass('172.22.10.51', 1515, Model='QB85C')
_moduleInterfaceYogaStudioDisplay = modSamsungTV.EthernetClass('172.22.10.52', 1515, Model='QB75C')

# Terrace Gallery displays are consumer Samsung Tizen TVs (The Frame, QN43LS03)
# controlled over the native WebSocket Remote Control API instead of MDC/Ex-Link.
# Port 8001 + Protocol='TCP' = unencrypted ws (works on this ControlScript API,
# which only supports TCP/UDP/SSH). If your TV firmware only exposes the secure
# endpoint, switch to (8002, Protocol='SSL'); the module will TLS-wrap via
# SSLWrap() when the firmware supports it.
# MACAddress enables Wake-on-LAN power-on (required to wake a TV that is fully off);
# fill in each TV's MAC to enable Power On.
_moduleInterfaceTerraceGalleryDisplay1 = modSamsungTizenWS.EthernetClass(
    '172.22.10.54', 8001, Protocol='TCP', Model='QN65LST7DAFXZA',
    MACAddress='B0:F2:F6:8B:34:05', Name='Level4Control')
_moduleInterfaceTerraceGalleryDisplay2 = modSamsungTizenWS.EthernetClass(
    '172.22.10.56', 8001, Protocol='TCP', Model='QN43LS03DAFXZA',
    MACAddress=None, Name='Level4Control')

# Wrap MDC displays with ConnectionHandler for automatic reconnection.
dvPartyRmDisplay = GetConnectionHandler(_moduleInterfacePartyRmDisplay, 'Power', pollFrequency=30)
dvYogaStudioDisplay = GetConnectionHandler(_moduleInterfaceYogaStudioDisplay, 'Power', pollFrequency=30)

# The Tizen WebSocket module manages its own handshake, keep-alive and
# reconnection, so it is used directly (not wrapped by GetConnectionHandler).
dvTerraceGalleryDisplay1 = _moduleInterfaceTerraceGalleryDisplay1
dvTerraceGalleryDisplay2 = _moduleInterfaceTerraceGalleryDisplay2

# Connection to Level 1 Processor for volume/mute feedback
# Keep-alive function for raw TCP connections
def _level1_keepalive(handler):
    """Send keepalive to Level 1 processor"""
    # Only send if actually connected - prevents library error logging
    # Check underlying interface state which reflects actual socket status
    wrapped = getattr(handler, '_WrappedInterface', None)
    if wrapped is None:
        return
    if getattr(wrapped, 'ConnectionStatus', None) != 'Connected':
        return
    try:
        handler.Send('\n')
    except:
        pass

# Create connection to Level 1 processor (172.22.10.100:10000)
_rawRemoteLevel1 = EthernetClientInterface('172.22.10.100', 10000, Protocol='TCP')
# Wrap with ConnectionHandler for automatic reconnection.
# This is a (mostly) one-way notification link to Level 1, so Level 1 may never
# reply. A large DisconnectLimit prevents the keep-alive send counter from
# triggering a false disconnect; genuine drops are still detected via the
# underlying socket Disconnected event and auto-reconnected.
dvRemoteLevel1 = GetConnectionHandler(_rawRemoteLevel1, _level1_keepalive,
                                      pollFrequency=10, DisconnectLimit=1000000)