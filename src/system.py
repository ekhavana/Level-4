"""
System Initialization and Connection Management

This module handles:
* Device connection initialization
* Connection status handlers
* System startup procedures
"""

# Extron Library imports
from extronlib.system import ProgramLog

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
    ProgramLog(f'System: DSP connection status changed - {command}: {value}', 'warning')
    if command == 'ConnectionStatus' and value == 'Connected':
        ProgramLog('System: DSP connected, initializing volume feedback', 'warning')
        # Request initial volume levels for all outputs to trigger feedback
        for room, output in variables.DSP_OUTPUTS.items():
            devices.dvDSPLevel4.Update('OutputAttenuation', {'Output': output})
            ProgramLog(f'System: Requested volume feedback for {room} (Output {output})', 'warning')
        ProgramLog('System: Volume feedback initialization complete', 'warning')
    elif value == 'Disconnected':
        ProgramLog('System: DSP Level 4 Disconnected', 'error')

def PartyRoomDisplayConnectionHandler(command, value, qualifier):
    """Handle Party Room Display connection state changes"""
    if value == 'Connected':
        ProgramLog('System: Party Room Display Connected', 'warning')
    elif value == 'Disconnected':
        ProgramLog('System: Party Room Display Disconnected', 'error')

def YogaStudioDisplayConnectionHandler(command, value, qualifier):
    """Handle Yoga Studio Display connection state changes"""
    if value == 'Connected':
        ProgramLog('System: Yoga Studio Display Connected', 'warning')
    elif value == 'Disconnected':
        ProgramLog('System: Yoga Studio Display Disconnected', 'error')

def TerraceGalleryDisplay1ConnectionHandler(command, value, qualifier):
    """Handle Terrace Gallery Display 1 connection state changes"""
    if value == 'Connected':
        ProgramLog('System: Terrace Gallery Display 1 Connected', 'warning')
    elif value == 'Disconnected':
        ProgramLog('System: Terrace Gallery Display 1 Disconnected', 'error')

def TerraceGalleryDisplay2ConnectionHandler(command, value, qualifier):
    """Handle Terrace Gallery Display 2 connection state changes"""
    if value == 'Connected':
        ProgramLog('System: Terrace Gallery Display 2 Connected', 'warning')
    elif value == 'Disconnected':
        ProgramLog('System: Terrace Gallery Display 2 Disconnected', 'error')

# ========================================================================================
# DSP Feedback Handlers
# ========================================================================================

def DSPVolumeHandler(command, value, qualifier):
    """Handle DSP volume feedback and update UI sliders"""
    ProgramLog(f'System: DSP volume feedback - command={command}, value={value}dB, qualifier={qualifier}', 'warning')
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
            ProgramLog(f'System: Converted {dspLevel}dB to UI level {uiLevel} for {room}', 'warning')
            av.VolumeLevel[room] = uiLevel
            
            # Update slider if registered
            slider = av._VolumeSliders.get(room)
            if slider:
                ProgramLog(f'System: Setting slider for {room} to {uiLevel}', 'warning')
                slider.SetFill(uiLevel)  # Use SetFill() method for Extron sliders
            else:
                ProgramLog(f'System: Warning - No slider registered for {room}', 'warning')
            
            # Send feedback to Level 1 processor
            av._SendFeedbackToLevel1('VolumeFeedback', room, level=uiLevel)
            
        except (ValueError, TypeError) as e:
            ProgramLog(f'System: DSP volume feedback error - {e}', 'error')

def DSPMuteHandler(command, value, qualifier):
    """Handle DSP mute feedback and update UI buttons"""
    ProgramLog(f'System: DSP mute feedback - command={command}, value={value}, qualifier={qualifier}', 'warning')
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
        try:
            ProgramLog(f'System: Updating {room} mute to {value}', 'warning')
            av.AudioMuteState[room] = (value == 'On')
            
            # Send feedback to Level 1 processor
            av._SendFeedbackToLevel1('MuteFeedback', room, state=value)
            
        except Exception as e:
            ProgramLog(f'System: DSP mute feedback error - {e}', 'error')

# ========================================================================================
# Initialization
# ========================================================================================

def Initialize():
    """Initialize system and connect all devices"""
    ProgramLog('System: Starting initialization', 'warning')
    
    # Register connection handlers
    ProgramLog('System: Subscribing to DSP connection status', 'warning')
    devices.dvDSPLevel4.SubscribeStatus('ConnectionStatus', None, DSPConnectionHandler)
    devices.dvPartyRmDisplay.SubscribeStatus('ConnectionStatus', None, PartyRoomDisplayConnectionHandler)
    devices.dvYogaStudioDisplay.SubscribeStatus('ConnectionStatus', None, YogaStudioDisplayConnectionHandler)
    devices.dvTerraceGalleryDisplay1.SubscribeStatus('ConnectionStatus', None, TerraceGalleryDisplay1ConnectionHandler)
    devices.dvTerraceGalleryDisplay2.SubscribeStatus('ConnectionStatus', None, TerraceGalleryDisplay2ConnectionHandler)
    
    # Subscribe to DSP volume and mute feedback for all outputs
    ProgramLog('System: Subscribing to DSP volume and mute feedback', 'warning')
    for room, output in variables.DSP_OUTPUTS.items():
        devices.dvDSPLevel4.SubscribeStatus('OutputAttenuation', {'Output': output}, DSPVolumeHandler)
        ProgramLog(f'System: Subscribed to OutputAttenuation for {room} (Output {output})', 'warning')
        devices.dvDSPLevel4.SubscribeStatus('OutputMute', {'Output': output}, DSPMuteHandler)
        ProgramLog(f'System: Subscribed to OutputMute for {room} (Output {output})', 'warning')
    
    # Connect all network devices
    ProgramLog('System: Connecting to DSP', 'warning')
    devices.dvDSPLevel4.Connect()
    ProgramLog('System: Connecting to displays', 'warning')
    devices.dvPartyRmDisplay.Connect()
    devices.dvYogaStudioDisplay.Connect()
    devices.dvTerraceGalleryDisplay1.Connect()
    devices.dvTerraceGalleryDisplay2.Connect()
    
    # Connect to Level 1 processor for feedback
    ProgramLog('System: Connecting to Level 1 processor for feedback', 'warning')
    devices.dvRemoteLevel1.Connect()
    
    # Start remote control server
    remote.Start()

    ProgramLog('System: All devices connecting...', 'warning')
    ProgramLog('System: Initialization complete', 'warning')
