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
import modules.device.extr_dsp_DMP128_FlexPlus_v1_0_9_0 as modDSP
import modules.device.smsg_display_QBxxC_QHxxC_QMxxC_Series_v1_0_4_0 as modSamsungTV
import modules.device.smsg_display_QNxxLS03DAFXZA_Series_v1_0_0_0 as modSamsungTVQN

# Define devices
##Control Processors
MainProcessor = ProcessorDevice('MainController')

##UI Devices
dvTLPYogaStudio = UIDevice('YogaStudioTouchPanel')
dvPartyRoomTLP = UIDevice('PartyRoomTouchPanel')
dvTerraceGalleryTLP1 = UIDevice('TerraceGalleryTouchPanel1')
dvTerraceGalleryTLP2 = UIDevice('TerraceGalleryTouchPanel2')

##Control Devices
# Define any control devices here (e.g. extronlib.device objects, custom python coded devices, etc.)

dvDSPLevel4 = modDSP.SSHClass('192.168.1.223', 22023, Credentials=('admin', 'extron'), Model='DMP 128 FlexPlus C AT')
dvPartyRmDisplay = modSamsungTV.EthernetClass('192.168.1.51', 1515, 'QB85C')
dvYogaStudioDisplay = modSamsungTV.EthernetClass('192.168.1.52', 1515, 'QB75C')
dvTerraceGalleryDisplay1 = modSamsungTVQN.SerialOverEthernetClass('192.168.1.54', 2001, Model='QN43LS03DAFXZA')
dvTerraceGalleryDisplay2 = modSamsungTVQN.SerialOverEthernetClass('192.168.1.56', 2001, Model='QN43LS03DAFXZA')