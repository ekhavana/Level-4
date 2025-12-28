"""
System Initialization and Connection Management

This module handles:
* Device connection initialization
* Connection status handlers
* System startup procedures
"""

# Project imports
import devices
import control.remote as remote

# ========================================================================================
# Connection Status Handlers
# ========================================================================================

def DSPConnectionHandler(interface, state):
    """Handle DSP connection state changes"""
    if state == 'Connected':
        print('System: DSP Level 4 Connected')
    elif state == 'Disconnected':
        print('System: DSP Level 4 Disconnected')

def PartyRoomDisplayConnectionHandler(interface, state):
    """Handle Party Room Display connection state changes"""
    if state == 'Connected':
        print('System: Party Room Display Connected')
    elif state == 'Disconnected':
        print('System: Party Room Display Disconnected')

def YogaStudioDisplayConnectionHandler(interface, state):
    """Handle Yoga Studio Display connection state changes"""
    if state == 'Connected':
        print('System: Yoga Studio Display Connected')
    elif state == 'Disconnected':
        print('System: Yoga Studio Display Disconnected')

def TerraceGalleryDisplay1ConnectionHandler(interface, state):
    """Handle Terrace Gallery Display 1 connection state changes"""
    if state == 'Connected':
        print('System: Terrace Gallery Display 1 Connected')
    elif state == 'Disconnected':
        print('System: Terrace Gallery Display 1 Disconnected')

def TerraceGalleryDisplay2ConnectionHandler(interface, state):
    """Handle Terrace Gallery Display 2 connection state changes"""
    if state == 'Connected':
        print('System: Terrace Gallery Display 2 Connected')
    elif state == 'Disconnected':
        print('System: Terrace Gallery Display 2 Disconnected')

# ========================================================================================
# Initialization
# ========================================================================================

def Initialize():
    """Initialize system and connect all devices"""
    
    # Register connection handlers
    devices.dvDSPLevel4.SubscribeStatus('ConnectionStatus', None, DSPConnectionHandler)
    devices.dvPartyRmDisplay.SubscribeStatus('ConnectionStatus', None, PartyRoomDisplayConnectionHandler)
    devices.dvYogaStudioDisplay.SubscribeStatus('ConnectionStatus', None, YogaStudioDisplayConnectionHandler)
    devices.dvTerraceGalleryDisplay1.SubscribeStatus('ConnectionStatus', None, TerraceGalleryDisplay1ConnectionHandler)
    devices.dvTerraceGalleryDisplay2.SubscribeStatus('ConnectionStatus', None, TerraceGalleryDisplay2ConnectionHandler)
    
    # Connect all network devices
    devices.dvDSPLevel4.Connect()
    devices.dvPartyRmDisplay.Connect()
    devices.dvYogaStudioDisplay.Connect()
    devices.dvTerraceGalleryDisplay1.Connect()
    devices.dvTerraceGalleryDisplay2.Connect()
    
    # Start remote control server (listening on TCP 5000)
    remote.Start()

    print('System: All devices connecting...')
    print('System Initialized')
