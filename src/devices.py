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
_moduleInterfaceTerraceGalleryDisplay1 = modSamsungTVQN.SerialOverEthernetClass('172.22.10.54', 2001, Model='QN43LS03DAFXZA')
_moduleInterfaceTerraceGalleryDisplay2 = modSamsungTVQN.SerialOverEthernetClass('172.22.10.56', 2001, Model='QN43LS03DAFXZA')

# Wrap all displays with ConnectionHandler for automatic reconnection
dvPartyRmDisplay = GetConnectionHandler(_moduleInterfacePartyRmDisplay, 'Power', pollFrequency=30)
dvYogaStudioDisplay = GetConnectionHandler(_moduleInterfaceYogaStudioDisplay, 'Power', pollFrequency=30)
dvTerraceGalleryDisplay1 = GetConnectionHandler(_moduleInterfaceTerraceGalleryDisplay1, 'Power', pollFrequency=30)
dvTerraceGalleryDisplay2 = GetConnectionHandler(_moduleInterfaceTerraceGalleryDisplay2, 'Power', pollFrequency=30)

# Connection to Level 1 Processor for volume/mute feedback
# Keep-alive function for raw TCP connections
def _level1_keepalive(handler):
    """Send keepalive to Level 1 processor"""
    try:
        handler.Send('\n')
    except:
        pass

# Create connection to Level 1 processor (172.22.10.100:10000)
_rawRemoteLevel1 = EthernetClientInterface('172.22.10.100', 10000, Protocol='TCP')
# Wrap with ConnectionHandler for automatic reconnection
dvRemoteLevel1 = GetConnectionHandler(_rawRemoteLevel1, _level1_keepalive, pollFrequency=10)