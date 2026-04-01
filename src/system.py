"""
System Initialization and Connection Management

This module handles:
* Device connection initialization
* Connection status handlers
* System startup procedures
"""

# Project imports
import devices
import variables
import control.remote as remote
import control.av as av

# ========================================================================================
# Connection Status Handlers
# ========================================================================================

def DSPConnectionHandler(command, value, qualifier):
    """Handle DSP connection state changes"""
    if value == 'Connected':
        print('System: DSP Level 4 Connected')
    elif value == 'Disconnected':
        print('System: DSP Level 4 Disconnected')

def PartyRoomDisplayConnectionHandler(command, value, qualifier):
    """Handle Party Room Display connection state changes"""
    if value == 'Connected':
        print('System: Party Room Display Connected')
    elif value == 'Disconnected':
        print('System: Party Room Display Disconnected')

def YogaStudioDisplayConnectionHandler(command, value, qualifier):
    """Handle Yoga Studio Display connection state changes"""
    if value == 'Connected':
        print('System: Yoga Studio Display Connected')
    elif value == 'Disconnected':
        print('System: Yoga Studio Display Disconnected')

def TerraceGalleryDisplay1ConnectionHandler(command, value, qualifier):
    """Handle Terrace Gallery Display 1 connection state changes"""
    if value == 'Connected':
        print('System: Terrace Gallery Display 1 Connected')
    elif value == 'Disconnected':
        print('System: Terrace Gallery Display 1 Disconnected')

def TerraceGalleryDisplay2ConnectionHandler(command, value, qualifier):
    """Handle Terrace Gallery Display 2 connection state changes"""
    if value == 'Connected':
        print('System: Terrace Gallery Display 2 Connected')
    elif value == 'Disconnected':
        print('System: Terrace Gallery Display 2 Disconnected')

# ========================================================================================
# DSP Feedback Handlers
# ========================================================================================

def DSPVolumeHandler(command, value, qualifier):
    """Handle DSP volume feedback and update UI sliders"""
    output = qualifier.get('Output')
    if not output:
        return
    
    # Map output number to room name
    room = None
    for roomName, outputNum in variables.DSP_OUTPUTS.items():
        if outputNum == output:
            room = roomName
            break
    
    if room:
        # Convert DSP dB value to UI slider value (0-100)
        try:
            dspLevel = float(value)
            uiLevel = av.UnscaleVolume(dspLevel)
            av.VolumeLevel[room] = uiLevel
            print(f'System: {room} Volume feedback: {uiLevel} (DSP: {dspLevel}dB)')
            # Notify UI to update slider (without triggering another DSP command)
            av._NotifyUICallbacks('VolumeChanged', room=room, level=uiLevel)
        except (ValueError, TypeError):
            pass

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
    
    # Subscribe to DSP volume feedback for all outputs
    for room, output in variables.DSP_OUTPUTS.items():
        devices.dvDSPLevel4.SubscribeStatus('OutputAttenuation', {'Output': output}, DSPVolumeHandler)
        print(f'System: Subscribed to volume feedback for {room} (Output {output})')
    
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
