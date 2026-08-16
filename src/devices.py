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
import modules.device.roku_ecp as modRoku

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

# Terrace Gallery Tizen TVs — port 8002 + SSL + Token= (wss).
# Pair from laptop (same VLAN), then paste Token=:
#   python docs/pair_samsung_tizen.py 172.22.10.54 Level4Control
#   python docs/pair_samsung_tizen.py 172.22.10.56 Level4Control
# Log must show: TLS enabled (wss) → WebSocket open (no unauthorized).
_moduleInterfaceTerraceGalleryDisplay1 = modSamsungTizenWS.EthernetClass(
    '172.22.10.54', 8002, Protocol='SSL', Model='QN65LST7DAFXZA',
    MACAddress='B0:F2:F6:8B:34:05', Name='Level4Control',
    Token=None,  # paste after pair_samsung_tizen.py
    # The Terrace (.54) is actually powered ON when its WebSocket connects (it
    # does not sit in standby with the socket open the way the .56 Frame does).
    # Seeding 'Off' (AssumeStandbyOnConnect=True) therefore put On/Off in
    # anti-phase: the first On press fired a KEY_POWER "wake" toggle that turned
    # the already-on TV OFF, and every press stayed inverted after that. Seed
    # 'On' instead (AssumeStandbyOnConnect=False) so On powers on / Off powers
    # off. The input-select self-heal (_note_tv_on) still corrects the model if
    # the assumption is ever wrong.
    AssumeStandbyOnConnect=False,
)
_moduleInterfaceTerraceGalleryDisplay2 = modSamsungTizenWS.EthernetClass(
    '172.22.10.56', 8002, Protocol='SSL', Model='QN43LS03DAFXZA',
    MACAddress='B0:F2:F6:8B:27:FF', Name='Level4Control',
    # Token=None so the TV issues a *real* token on first connect (approve the
    # "Allow this device" prompt on the TV). The driver saves it to
    # tizen_token_172_22_10_56.txt and reuses it — same as .54, which is stable
    # precisely because it holds a genuine TV-issued token. The old manual value
    # '69782556' was never a valid paired token and caused ~10s session drops.
    Token=None,
    # The Frame (LS03) also keeps the WebSocket open in standby/Art Mode, so it
    # connects while actually off. Assume standby on connect so KEY_POWER On/Off
    # don't invert (same fix as .54).
    AssumeStandbyOnConnect=True)

# Wrap MDC displays with ConnectionHandler for automatic reconnection.
dvPartyRmDisplay = GetConnectionHandler(_moduleInterfacePartyRmDisplay, 'Power', pollFrequency=30)
dvYogaStudioDisplay = GetConnectionHandler(_moduleInterfaceYogaStudioDisplay, 'Power', pollFrequency=30)

# The Tizen WebSocket module manages its own handshake, keep-alive and
# reconnection, so it is used directly (not wrapped by GetConnectionHandler).
dvTerraceGalleryDisplay1 = _moduleInterfaceTerraceGalleryDisplay1
dvTerraceGalleryDisplay2 = _moduleInterfaceTerraceGalleryDisplay2

# Roku ECP (:8060) — replace placeholder IPs when known on site
dvPartyRoomRoku = modRoku.EthernetClass('172.20.2.222', 8060)
dvTerraceGalleryRoku1 = modRoku.EthernetClass('172.20.2.210', 8060)
dvTerraceGalleryRoku2 = modRoku.EthernetClass('172.20.2.209', 8060)

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