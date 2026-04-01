"""
AV Control Module - Centralized control for all audio/video devices

This module handles:
* System power on/off for all rooms
* Volume and mute control via DSP
* Audio source selection and routing
* UI feedback callbacks for multi-panel synchronization
"""

# Extron Library imports
from extronlib.system import Wait

# Project imports
import devices
import variables

# ========================================================================================
# System State Tracking
# ========================================================================================

# Track system power state for each room
SystemPowerState = {
    'PartyRoom': False,
    'YogaStudio': False,
    'TerraceGallery': False,
}

# Track audio mute state for each zone
AudioMuteState = {
    'Gym': False,
    'YogaStudio': False,
    'TerraceGallery': False,
    'PartyRoom': False,
    'Courtyard': False,
}

# Track current volume for each zone (0-100)
VolumeLevel = {
    'Gym': 50,
    'YogaStudio': 50,
    'TerraceGallery': 50,
    'PartyRoom': 50,
    'Courtyard': 50,
}

# Track current audio source for each room
CurrentAudioSource = {
    'PartyRoom': None,
    'YogaStudio': None,
}

# ========================================================================================
# UI Feedback Callbacks - For Multi-Panel Synchronization
# ========================================================================================

# Registered callbacks for UI updates when state changes
# Format: {'event_type': [callback_function, ...]}
_UICallbacks = {
    'VolumeChanged': [],
    'MuteChanged': [],
    'PowerChanged': [],
    'SourceChanged': [],
}

def RegisterUICallback(eventType, callback):
    """
    Register a callback function to be notified of state changes
    
    Args:
        eventType: 'VolumeChanged', 'MuteChanged', 'PowerChanged', 'SourceChanged'
        callback: Function to call when event occurs
    """
    if eventType in _UICallbacks:
        _UICallbacks[eventType].append(callback)

def UnregisterUICallback(eventType, callback):
    """Remove a previously registered callback"""
    if eventType in _UICallbacks and callback in _UICallbacks[eventType]:
        _UICallbacks[eventType].remove(callback)

def _NotifyUICallbacks(eventType, **kwargs):
    """Notify all registered callbacks of a state change"""
    for callback in _UICallbacks.get(eventType, []):
        try:
            callback(**kwargs)
        except Exception as e:
            print(f'AV Control: UI callback error - {e}')

# ========================================================================================
# Utility Functions
# ========================================================================================

def ScaleVolume(uiValue):
    """
    Scale UI volume value (0-100) to DSP range using variables.py constants
    
    Args:
        uiValue: Volume level from UI (0-100)
    
    Returns:
        Scaled DSP volume value in dB
    """
    minUI = variables.VOLUME_MIN
    maxUI = variables.VOLUME_MAX
    minDSP = variables.DSP_VOLUME_MIN
    maxDSP = variables.DSP_VOLUME_MAX
    return int(((uiValue - minUI) / (maxUI - minUI)) * (maxDSP - minDSP) + minDSP)

def ScaleVolumeToUI(dspValue):
    """
    Scale DSP volume value to UI range (0-100)
    
    Args:
        dspValue: Volume level from DSP in dB
    
    Returns:
        Scaled UI volume value (0-100)
    """
    minUI = variables.VOLUME_MIN
    maxUI = variables.VOLUME_MAX
    minDSP = variables.DSP_VOLUME_MIN
    maxDSP = variables.DSP_VOLUME_MAX
    return int(((dspValue - minDSP) / (maxDSP - minDSP)) * (maxUI - minUI) + minUI)

# Alias for better readability
UnscaleVolume = ScaleVolumeToUI

# ========================================================================================
# Party Room System Power Functions
# ========================================================================================

def PartyRoomSystemPowerOn(callback=None):
    """
    Power on the Party Room system.
    Sequence:
    1. Unmute audio
    2. Set audio source to Music Player
    3. Power on TV
    4. Set TV input to HDMI 1
    
    Args:
        callback: Optional callback function to execute after power on sequence completes
    """
    print('AV Control: Party Room System Power On')
    SystemPowerState['PartyRoom'] = True
    
    # Unmute audio
    SetMute('PartyRoom', False, notifyUI=True)
    
    # Set audio source to Music Player
    SetAudioSource('PartyRoom', 'MusicPlayer')
    
    # Power on the display
    devices.dvPartyRmDisplay.Set('Power', 'On')
    
    # Set default input to HDMI 1
    @Wait(2)
    def SetDefaultInput():
        devices.dvPartyRmDisplay.Set('Input', 'HDMI 1')
        print('AV Control: Party Room - Display input set to HDMI 1')
        if callback:
            callback()
        _NotifyUICallbacks('PowerChanged', room='PartyRoom', power=True)

def PartyRoomSystemPowerOff(callback=None):
    """
    Power off the Party Room system.
    Sequence:
    1. Mute audio
    2. Power off TV
    
    Args:
        callback: Optional callback function to execute after power off sequence completes
    """
    print('AV Control: Party Room System Power Off')
    SystemPowerState['PartyRoom'] = False
    
    # Mute audio
    SetMute('PartyRoom', True, notifyUI=True)
    
    # Power off the display
    devices.dvPartyRmDisplay.Set('Power', 'Off')
    
    if callback:
        @Wait(1)
        def ExecuteCallback():
            callback()
    _NotifyUICallbacks('PowerChanged', room='PartyRoom', power=False)

def PartyRoomGetSystemPowerState():
    """Returns the current power state of the Party Room system"""
    return SystemPowerState['PartyRoom']

# ========================================================================================
# Yoga Studio System Power Functions
# ========================================================================================

def YogaStudioSystemPowerOn(callback=None):
    """
    Power on the Yoga Studio system.
    Sequence:
    1. Unmute audio
    2. Set audio source to Music Player
    3. Power on TV
    4. Set TV input to HDMI 1
    
    Args:
        callback: Optional callback function to execute after power on sequence completes
    """
    print('AV Control: Yoga Studio System Power On')
    SystemPowerState['YogaStudio'] = True
    
    # Unmute audio
    SetMute('YogaStudio', False, notifyUI=True)
    
    # Set audio source to Music Player
    SetAudioSource('YogaStudio', 'MusicPlayer')
    
    # Power on the display
    devices.dvYogaStudioDisplay.Set('Power', 'On')
    
    # Set default input to HDMI 1
    @Wait(2)
    def SetDefaultInput():
        devices.dvYogaStudioDisplay.Set('Input', 'HDMI 1')
        print('AV Control: Yoga Studio - Display input set to HDMI 1')
        if callback:
            callback()
        _NotifyUICallbacks('PowerChanged', room='YogaStudio', power=True)

def YogaStudioSystemPowerOff(callback=None):
    """
    Power off the Yoga Studio system.
    Sequence:
    1. Mute audio
    2. Power off TV
    
    Args:
        callback: Optional callback function to execute after power off sequence completes
    """
    print('AV Control: Yoga Studio System Power Off')
    SystemPowerState['YogaStudio'] = False
    
    # Mute audio
    SetMute('YogaStudio', True, notifyUI=True)
    
    # Power off the display
    devices.dvYogaStudioDisplay.Set('Power', 'Off')
    
    if callback:
        @Wait(1)
        def ExecuteCallback():
            callback()
    _NotifyUICallbacks('PowerChanged', room='YogaStudio', power=False)

def YogaStudioGetSystemPowerState():
    """Returns the current power state of the Yoga Studio system"""
    return SystemPowerState['YogaStudio']

# ========================================================================================
# Terrace Gallery System Power Functions
# ========================================================================================

def TerraceGallerySystemPowerOn(callback=None):
    """
    Power on the Terrace Gallery system.
    Sequence:
    1. Unmute audio
    2. Power on both TVs
    3. Set both TV inputs to HDMI 1
    
    Args:
        callback: Optional callback function to execute after power on sequence completes
    """
    print('AV Control: Terrace Gallery System Power On')
    SystemPowerState['TerraceGallery'] = True
    
    # Unmute audio
    SetMute('TerraceGallery', False, notifyUI=True)
    
    # Power on both displays
    devices.dvTerraceGalleryDisplay1.Set('Power', 'On')
    devices.dvTerraceGalleryDisplay2.Set('Power', 'On')
    
    # Set default inputs to HDMI 1
    @Wait(2)
    def SetDefaultInputs():
        devices.dvTerraceGalleryDisplay1.Set('Input', 'HDMI 1')
        devices.dvTerraceGalleryDisplay2.Set('Input', 'HDMI 1')
        print('AV Control: Terrace Gallery - Display inputs set to HDMI 1')
        if callback:
            callback()
        _NotifyUICallbacks('PowerChanged', room='TerraceGallery', power=True)

def TerraceGallerySystemPowerOff(callback=None):
    """
    Power off the Terrace Gallery system.
    Sequence:
    1. Mute audio
    2. Power off both TVs
    
    Args:
        callback: Optional callback function to execute after power off sequence completes
    """
    print('AV Control: Terrace Gallery System Power Off')
    SystemPowerState['TerraceGallery'] = False
    
    # Mute audio
    SetMute('TerraceGallery', True, notifyUI=True)
    
    # Power off both displays
    devices.dvTerraceGalleryDisplay1.Set('Power', 'Off')
    devices.dvTerraceGalleryDisplay2.Set('Power', 'Off')
    
    if callback:
        @Wait(1)
        def ExecuteCallback():
            callback()
    _NotifyUICallbacks('PowerChanged', room='TerraceGallery', power=False)

def TerraceGalleryGetSystemPowerState():
    """Returns the current power state of the Terrace Gallery system"""
    return SystemPowerState['TerraceGallery']

# ========================================================================================
# Individual Display Power Functions (for manual TV control buttons)
# ========================================================================================

def TerraceGalleryTV1PowerOn():
    """Power on Terrace Gallery TV1 only"""
    print('AV Control: Terrace Gallery TV1 Power On')
    devices.dvTerraceGalleryDisplay1.Set('Power', 'On')

def TerraceGalleryTV1PowerOff():
    """Power off Terrace Gallery TV1 only"""
    print('AV Control: Terrace Gallery TV1 Power Off')
    devices.dvTerraceGalleryDisplay1.Set('Power', 'Off')

def TerraceGalleryTV2PowerOn():
    """Power on Terrace Gallery TV2 only"""
    print('AV Control: Terrace Gallery TV2 Power On')
    devices.dvTerraceGalleryDisplay2.Set('Power', 'On')

def TerraceGalleryTV2PowerOff():
    """Power off Terrace Gallery TV2 only"""
    print('AV Control: Terrace Gallery TV2 Power Off')
    devices.dvTerraceGalleryDisplay2.Set('Power', 'Off')

def PartyRoomTVPowerOn():
    """Power on Party Room TV"""
    print('AV Control: Party Room TV Power On')
    devices.dvPartyRmDisplay.Set('Power', 'On')

def PartyRoomTVPowerOff():
    """Power off Party Room TV"""
    print('AV Control: Party Room TV Power Off')
    devices.dvPartyRmDisplay.Set('Power', 'Off')

def YogaStudioTVPowerOn():
    """Power on Yoga Studio TV"""
    print('AV Control: Yoga Studio TV Power On')
    devices.dvYogaStudioDisplay.Set('Power', 'On')

def YogaStudioTVPowerOff():
    """Power off Yoga Studio TV"""
    print('AV Control: Yoga Studio TV Power Off')
    devices.dvYogaStudioDisplay.Set('Power', 'Off')

# ========================================================================================
# DSP Volume Control Functions
# ========================================================================================

def SetVolume(room, level, notifyUI=True):
    """
    Set volume level for a room
    
    Args:
        room: Room name ('PartyRoom', 'YogaStudio', 'TerraceGallery', 'Gym', 'Courtyard')
        level: Volume level 0-100
        notifyUI: Whether to notify UI callbacks (set False to prevent feedback loops)
    """
    if room not in variables.DSP_OUTPUTS:
        print(f'AV Control: Unknown room {room}')
        return
    
    # Clamp volume to valid range
    level = max(variables.VOLUME_MIN, min(variables.VOLUME_MAX, level))
    VolumeLevel[room] = level
    
    # Scale to DSP range
    dspLevel = ScaleVolume(level)
    output = variables.DSP_OUTPUTS[room]
    
    print(f'AV Control: {room} Volume set to {level} (DSP: {dspLevel}dB)')
    devices.dvDSPLevel4.Set('OutputAttenuation', dspLevel, {'Output': output})
    
    # Notify registered UI callbacks
    if notifyUI:
        _NotifyUICallbacks('VolumeChanged', room=room, level=level)

def GetVolume(room):
    """Get current volume level for a room"""
    return VolumeLevel.get(room, 50)

def PartyRoomSetVolume(level):
    """Set Party Room volume"""
    SetVolume('PartyRoom', level)

def YogaStudioSetVolume(level):
    """Set Yoga Studio volume"""
    SetVolume('YogaStudio', level)

def TerraceGallerySetVolume(level):
    """Set Terrace Gallery volume"""
    SetVolume('TerraceGallery', level)

# ========================================================================================
# DSP Mute Control Functions
# ========================================================================================

def SetMute(room, muteState, notifyUI=True):
    """
    Set mute state for a room
    
    Args:
        room: Room name ('PartyRoom', 'YogaStudio', 'TerraceGallery', 'Gym', 'Courtyard')
        muteState: True for mute, False for unmute
        notifyUI: Whether to notify UI callbacks (set False to prevent feedback loops)
    """
    if room not in variables.DSP_OUTPUTS:
        print(f'AV Control: Unknown room {room}')
        return
    
    AudioMuteState[room] = muteState
    output = variables.DSP_OUTPUTS[room]
    muteValue = 'On' if muteState else 'Off'
    
    print(f'AV Control: {room} Mute set to {muteValue}')
    devices.dvDSPLevel4.Set('OutputMute', muteValue, {'Output': output})
    
    # Notify registered UI callbacks
    if notifyUI:
        _NotifyUICallbacks('MuteChanged', room=room, muted=muteState)

def ToggleMute(room, notifyUI=True):
    """Toggle mute state for a room and return new state"""
    currentState = AudioMuteState.get(room, False)
    SetMute(room, not currentState, notifyUI)
    return not currentState

def GetMuteState(room):
    """Get current mute state for a room"""
    return AudioMuteState.get(room, False)

def PartyRoomSetMute(muteState):
    """Set Party Room mute state"""
    SetMute('PartyRoom', muteState)

def PartyRoomToggleMute():
    """Toggle Party Room mute"""
    return ToggleMute('PartyRoom')

def YogaStudioSetMute(muteState):
    """Set Yoga Studio mute state"""
    SetMute('YogaStudio', muteState)

def YogaStudioToggleMute():
    """Toggle Yoga Studio mute"""
    return ToggleMute('YogaStudio')

def TerraceGallerySetMute(muteState):
    """Set Terrace Gallery mute state"""
    SetMute('TerraceGallery', muteState)

def TerraceGalleryToggleMute():
    """Toggle Terrace Gallery mute"""
    return ToggleMute('TerraceGallery')

def GymSetVolume(level):
    """Set Gym volume"""
    SetVolume('Gym', level)

def GymSetMute(muteState):
    """Set Gym mute state"""
    SetMute('Gym', muteState)

def GymToggleMute():
    """Toggle Gym mute"""
    return ToggleMute('Gym')

def CourtyardSetVolume(level):
    """Set Courtyard volume"""
    SetVolume('Courtyard', level)

def CourtyardSetMute(muteState):
    """Set Courtyard mute state"""
    SetMute('Courtyard', muteState)

def CourtyardToggleMute():
    """Toggle Courtyard mute"""
    return ToggleMute('Courtyard')

# ========================================================================================
# Gym System Power Functions
# ========================================================================================

def GymSystemPowerOn(callback=None):
    """
    Power on the Gym system.
    Sequence:
    1. Unmute audio
    
    Args:
        callback: Optional callback function to execute after power on sequence completes
    """
    print('AV Control: Gym System Power On')
    
    # Unmute audio
    SetMute('Gym', False, notifyUI=True)
    
    if callback:
        callback()

def GymSystemPowerOff(callback=None):
    """
    Power off the Gym system.
    Sequence:
    1. Mute audio
    
    Args:
        callback: Optional callback function to execute after power off sequence completes
    """
    print('AV Control: Gym System Power Off')
    
    # Mute audio
    SetMute('Gym', True, notifyUI=True)
    
    if callback:
        callback()

# ========================================================================================
# Courtyard System Power Functions
# ========================================================================================

def CourtyardSystemPowerOn(callback=None):
    """
    Power on the Courtyard system.
    Sequence:
    1. Unmute audio
    
    Args:
        callback: Optional callback function to execute after power on sequence completes
    """
    print('AV Control: Courtyard System Power On')
    
    # Unmute audio
    SetMute('Courtyard', False, notifyUI=True)
    
    if callback:
        callback()

def CourtyardSystemPowerOff(callback=None):
    """
    Power off the Courtyard system.
    Sequence:
    1. Mute audio
    
    Args:
        callback: Optional callback function to execute after power off sequence completes
    """
    print('AV Control: Courtyard System Power Off')
    
    # Mute audio
    SetMute('Courtyard', True, notifyUI=True)
    
    if callback:
        callback()

# ========================================================================================
# DSP Audio Source Selection Functions
# ========================================================================================

def SetMixpointMute(inputType, inputChannel, outputChannel, muteState):
    """
    Set mixpoint mute state based on input type (Analog, Dante, or VirtualReceive)
    
    Args:
        inputType: 'Analog', 'Dante', or 'VirtualReceive'
        inputChannel: Input channel number as string
        outputChannel: Output channel number as string
        muteState: 'On' or 'Off'
    """
    if inputType == 'Analog':
        # For analog inputs, use standard MixpointMute
        devices.dvDSPLevel4.Set('MixpointMute', muteState, {'Input': inputChannel, 'Output': outputChannel})
    elif inputType == 'Dante':
        # For Dante inputs, use Dante-specific mixpoint control
        devices.dvDSPLevel4.Set('MixpointMute', muteState, {'Input': inputChannel, 'Output': outputChannel})
    elif inputType == 'VirtualReceive':
        # For Virtual Receive inputs (BT Plates routed through Virtual Sends A/B)
        # Virtual Receives use VirtualReturnMute command
        devices.dvDSPLevel4.Set('VirtualReturnMute', muteState, {'Input': inputChannel, 'Output': outputChannel})

def SetAudioSource(room, source):
    """
    Set audio source for a room using DSP mixpoint routing
    Handles both Analog and Dante inputs
    
    Args:
        room: Room name ('PartyRoom', 'YogaStudio')
        source: Source name ('MusicPlayer', 'BTPlate')
    """
    if room not in variables.AUDIO_SOURCES:
        print(f'AV Control: Unknown room {room} for audio source')
        return
    
    if source not in variables.AUDIO_SOURCES[room]:
        print(f'AV Control: Unknown source {source} for room {room}')
        return
    
    CurrentAudioSource[room] = source
    output = variables.DSP_OUTPUTS[room]
    
    print(f'AV Control: {room} Audio Source set to {source}')
    _NotifyUICallbacks('SourceChanged', room=room, source=source)
    
    # Mute all sources first, then unmute selected
    for srcName, srcConfig in variables.AUDIO_SOURCES[room].items():
        srcType = srcConfig['Type']
        muteState = 'Off' if srcName == source else 'On'
        
        if 'Channel' in srcConfig:
            # Single channel source
            SetMixpointMute(srcType, srcConfig['Channel'], output, muteState)
        elif 'Channels' in srcConfig:
            # Multi-channel source (like BT Plate with 4 channels)
            for channel in srcConfig['Channels']:
                SetMixpointMute(srcType, channel, output, muteState)

def GetCurrentAudioSource(room):
    """Get current audio source for a room"""
    return CurrentAudioSource.get(room)

def PartyRoomSelectMusicPlayer():
    """Select Music Player as Party Room audio source"""
    SetAudioSource('PartyRoom', 'MusicPlayer')

def PartyRoomSelectBTPlate():
    """Select Bluetooth Plate as Party Room audio source"""
    SetAudioSource('PartyRoom', 'BTPlate')

def YogaStudioSelectMusicPlayer():
    """Select Music Player as Yoga Studio audio source"""
    SetAudioSource('YogaStudio', 'MusicPlayer')

def YogaStudioSelectBTPlate():
    """Select Bluetooth Plate as Yoga Studio audio source"""
    SetAudioSource('YogaStudio', 'BTPlate')

# ========================================================================================
# DSP Audio Routing Functions (Send TV Audio to Zones)
# ========================================================================================

def RouteAudioToZone(source, zone):
    """
    Route audio from a source to a specific zone
    Handles both Analog and Dante inputs
    
    Args:
        source: Source input name from DSP_INPUTS
        zone: Destination zone name from DSP_OUTPUTS
    """
    if source not in variables.DSP_INPUTS:
        print(f'AV Control: Unknown source {source}')
        return
    
    if zone not in variables.DSP_OUTPUTS:
        print(f'AV Control: Unknown zone {zone}')
        return
    
    sourceConfig = variables.DSP_INPUTS[source]
    outputChannel = variables.DSP_OUTPUTS[zone]
    srcType = sourceConfig['Type']
    
    print(f'AV Control: Routing {source} to {zone}')
    
    if 'Channel' in sourceConfig:
        # Single channel source
        SetMixpointMute(srcType, sourceConfig['Channel'], outputChannel, 'Off')
    elif 'Channels' in sourceConfig:
        # Multi-channel source
        for channel in sourceConfig['Channels']:
            SetMixpointMute(srcType, channel, outputChannel, 'Off')

def RouteAudioToAllZones(source):
    """Route audio from a source to all zones"""
    if source not in variables.DSP_INPUTS:
        print(f'AV Control: Unknown source {source}')
        return
    
    sourceConfig = variables.DSP_INPUTS[source]
    srcType = sourceConfig['Type']
    
    print(f'AV Control: Routing {source} to All Zones')
    
    for zoneName, outputChannel in variables.DSP_OUTPUTS.items():
        if 'Channel' in sourceConfig:
            SetMixpointMute(srcType, sourceConfig['Channel'], outputChannel, 'Off')
        elif 'Channels' in sourceConfig:
            for channel in sourceConfig['Channels']:
                SetMixpointMute(srcType, channel, outputChannel, 'Off')

def ClearAudioRouting(source):
    """Clear all audio routing from a source"""
    if source not in variables.DSP_INPUTS:
        print(f'AV Control: Unknown source {source}')
        return
    
    sourceConfig = variables.DSP_INPUTS[source]
    srcType = sourceConfig['Type']
    
    print(f'AV Control: Clearing routing from {source}')
    
    for zoneName, outputChannel in variables.DSP_OUTPUTS.items():
        if 'Channel' in sourceConfig:
            SetMixpointMute(srcType, sourceConfig['Channel'], outputChannel, 'On')
        elif 'Channels' in sourceConfig:
            for channel in sourceConfig['Channels']:
                SetMixpointMute(srcType, channel, outputChannel, 'On')

# Party Room TV Audio Routing
def PartyRoomTVRouteToAll():
    """Route Party Room TV audio to all zones"""
    RouteAudioToAllZones('PartyRoomTV')

def PartyRoomTVRouteToGym():
    """Route Party Room TV audio to Gym"""
    ClearAudioRouting('PartyRoomTV')
    RouteAudioToZone('PartyRoomTV', 'Gym')

def PartyRoomTVRouteToYogaStudio():
    """Route Party Room TV audio to Yoga Studio"""
    ClearAudioRouting('PartyRoomTV')
    RouteAudioToZone('PartyRoomTV', 'YogaStudio')

def PartyRoomTVRouteToTerrace():
    """Route Party Room TV audio to Terrace Gallery"""
    ClearAudioRouting('PartyRoomTV')
    RouteAudioToZone('PartyRoomTV', 'TerraceGallery')

def PartyRoomTVRouteToPartyRoom():
    """Route Party Room TV audio to Party Room"""
    ClearAudioRouting('PartyRoomTV')
    RouteAudioToZone('PartyRoomTV', 'PartyRoom')

def PartyRoomTVRouteToCourtyard():
    """Route Party Room TV audio to Courtyard"""
    ClearAudioRouting('PartyRoomTV')
    RouteAudioToZone('PartyRoomTV', 'Courtyard')

# Yoga Studio TV Audio Routing
def YogaStudioTVRouteToAll():
    """Route Yoga Studio TV audio to all zones"""
    RouteAudioToAllZones('YogaStudioTV')

def YogaStudioTVRouteToGym():
    """Route Yoga Studio TV audio to Gym"""
    ClearAudioRouting('YogaStudioTV')
    RouteAudioToZone('YogaStudioTV', 'Gym')

def YogaStudioTVRouteToYogaStudio():
    """Route Yoga Studio TV audio to Yoga Studio"""
    ClearAudioRouting('YogaStudioTV')
    RouteAudioToZone('YogaStudioTV', 'YogaStudio')

def YogaStudioTVRouteToTerrace():
    """Route Yoga Studio TV audio to Terrace Gallery"""
    ClearAudioRouting('YogaStudioTV')
    RouteAudioToZone('YogaStudioTV', 'TerraceGallery')

def YogaStudioTVRouteToPartyRoom():
    """Route Yoga Studio TV audio to Party Room"""
    ClearAudioRouting('YogaStudioTV')
    RouteAudioToZone('YogaStudioTV', 'PartyRoom')

def YogaStudioTVRouteToCourtyard():
    """Route Yoga Studio TV audio to Courtyard"""
    ClearAudioRouting('YogaStudioTV')
    RouteAudioToZone('YogaStudioTV', 'Courtyard')

# Terrace Gallery TV1 Audio Routing
def TerraceGalleryTV1RouteToAll():
    """Route Terrace Gallery TV1 audio to all zones"""
    RouteAudioToAllZones('TerraceGalleryTV1')

def TerraceGalleryTV1RouteToGym():
    """Route Terrace Gallery TV1 audio to Gym"""
    ClearAudioRouting('TerraceGalleryTV1')
    RouteAudioToZone('TerraceGalleryTV1', 'Gym')

def TerraceGalleryTV1RouteToYogaStudio():
    """Route Terrace Gallery TV1 audio to Yoga Studio"""
    ClearAudioRouting('TerraceGalleryTV1')
    RouteAudioToZone('TerraceGalleryTV1', 'YogaStudio')

def TerraceGalleryTV1RouteToTerrace():
    """Route Terrace Gallery TV1 audio to Terrace Gallery"""
    ClearAudioRouting('TerraceGalleryTV1')
    RouteAudioToZone('TerraceGalleryTV1', 'TerraceGallery')

def TerraceGalleryTV1RouteToPartyRoom():
    """Route Terrace Gallery TV1 audio to Party Room"""
    ClearAudioRouting('TerraceGalleryTV1')
    RouteAudioToZone('TerraceGalleryTV1', 'PartyRoom')

def TerraceGalleryTV1RouteToCourtyard():
    """Route Terrace Gallery TV1 audio to Courtyard"""
    ClearAudioRouting('TerraceGalleryTV1')
    RouteAudioToZone('TerraceGalleryTV1', 'Courtyard')

# Terrace Gallery TV2 Audio Routing
def TerraceGalleryTV2RouteToAll():
    """Route Terrace Gallery TV2 audio to all zones"""
    RouteAudioToAllZones('TerraceGalleryTV2')

def TerraceGalleryTV2RouteToGym():
    """Route Terrace Gallery TV2 audio to Gym"""
    ClearAudioRouting('TerraceGalleryTV2')
    RouteAudioToZone('TerraceGalleryTV2', 'Gym')

def TerraceGalleryTV2RouteToYogaStudio():
    """Route Terrace Gallery TV2 audio to Yoga Studio"""
    ClearAudioRouting('TerraceGalleryTV2')
    RouteAudioToZone('TerraceGalleryTV2', 'YogaStudio')

def TerraceGalleryTV2RouteToTerrace():
    """Route Terrace Gallery TV2 audio to Terrace Gallery"""
    ClearAudioRouting('TerraceGalleryTV2')
    RouteAudioToZone('TerraceGalleryTV2', 'TerraceGallery')

def TerraceGalleryTV2RouteToPartyRoom():
    """Route Terrace Gallery TV2 audio to Party Room"""
    ClearAudioRouting('TerraceGalleryTV2')
    RouteAudioToZone('TerraceGalleryTV2', 'PartyRoom')

def TerraceGalleryTV2RouteToCourtyard():
    """Route Terrace Gallery TV2 audio to Courtyard"""
    ClearAudioRouting('TerraceGalleryTV2')
    RouteAudioToZone('TerraceGalleryTV2', 'Courtyard')
