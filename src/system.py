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

def _RequestTVAudioFeedback(tv_key, label):
    """Query a display's real volume/mute. Skipped while the panel is in standby."""
    if av.RequestTVLocalAudioFeedback(tv_key):
        ProgramLog(f'System: Requested {label} volume/mute feedback', 'warning')
    else:
        ProgramLog(f'System: {label} audio query deferred until display powers on', 'warning')


def _HandleTVPower(tv_key, label, value):
    """Track real display power so audio commands are only sent when awake."""
    av.SetTVLocalPowerState(tv_key, value == 'On')
    av._emit_tv_power(label, 'On' if value == 'On' else 'Off')
    if value == 'On':
        _RequestTVAudioFeedback(tv_key, label)


def DSPConnectionHandler(command, value, qualifier):
    """Handle DSP connection state changes"""
    ProgramLog(f'System: DSP connection status changed - {command}: {value}', 'warning')
    if command == 'ConnectionStatus' and value == 'Connected':
        ProgramLog('System: DSP connected, initializing safe routing', 'warning')
        av.InitializeDSPRouting()
        av.RefreshLocalVolumeUI()
        ProgramLog('System: Volume feedback initialization requested', 'warning')
    elif value == 'Disconnected':
        ProgramLog('System: DSP Level 4 Disconnected', 'error')

def PartyRoomDisplayConnectionHandler(command, value, qualifier):
    """Handle Party Room Display connection state changes"""
    if value == 'Connected':
        ProgramLog('System: Party Room Display Connected', 'warning')
        # Push this TV's power state so the Main TP updates on (re)connect.
        av.SyncTVPowerFeedbackToLevel1('Party Room TV')
        _RequestTVAudioFeedback('PartyRoomTV', 'Party Room TV')
    elif value == 'Disconnected':
        ProgramLog('System: Party Room Display Disconnected', 'error')

def YogaStudioDisplayConnectionHandler(command, value, qualifier):
    """Handle Yoga Studio Display connection state changes"""
    if value == 'Connected':
        ProgramLog('System: Yoga Studio Display Connected', 'warning')
        av.SyncTVPowerFeedbackToLevel1('Yoga Studio TV')
        _RequestTVAudioFeedback('YogaStudioTV', 'Yoga Studio TV')
    elif value == 'Disconnected':
        ProgramLog('System: Yoga Studio Display Disconnected', 'error')

def TerraceGalleryDisplay1ConnectionHandler(command, value, qualifier):
    """Handle Terrace Gallery Display 1 connection state changes"""
    if value == 'Connected':
        ProgramLog('System: Terrace Gallery Display 1 Connected', 'warning')
        av.SyncTVPowerFeedbackToLevel1('Terrace Gallery TV 1')
    elif value == 'Disconnected':
        ProgramLog('System: Terrace Gallery Display 1 Disconnected', 'error')

def TerraceGalleryDisplay2ConnectionHandler(command, value, qualifier):
    """Handle Terrace Gallery Display 2 connection state changes"""
    if value == 'Connected':
        ProgramLog('System: Terrace Gallery Display 2 Connected', 'warning')
        av.SyncTVPowerFeedbackToLevel1('Terrace Gallery TV 2')
    elif value == 'Disconnected':
        ProgramLog('System: Terrace Gallery Display 2 Disconnected', 'error')

# Whether we have already pushed a full feedback snapshot since the Level 1
# feedback link last became confirmed. Reset on disconnect so a reconnect
# re-pushes power/source/audio state to the Main TP.
_level1_synced = False

def Level1FeedbackReceiveData(interface, data):
    """Handle data received from the Level 1 processor on the feedback link.

    The feedback client is wrapped by RawTcpHandler, which only marks the link
    as 'Connected' and resets its keep-alive send counter when ResponseAccepted()
    is called. Without this, the link never reports Connected and force-disconnects
    after DisconnectLimit keep-alives. Any byte from Level 1 confirms the link.
    """
    global _level1_synced
    try:
        devices.dvRemoteLevel1.ResponseAccepted()
        if not _level1_synced:
            _level1_synced = True
            ProgramLog('System: Level 1 feedback link confirmed — pushing '
                       'TV power + source + audio snapshot to Main TP', 'warning')
            # Push once per (re)connect so the Main TP power controls and Audio
            # Zones reflect current state at system power-on, not only on change.
            av.SyncTVPowerFeedbackToLevel1()
            av.SyncSourceFeedbackToLevel1()
            av.SyncAudioFeedbackToLevel1()
    except Exception as e:
        ProgramLog(f'System: Level 1 feedback ResponseAccepted error - {e}', 'error')

def Level1FeedbackDisconnected(interface, state):
    """Reset the sync latch so the next Level 1 (re)connect re-pushes state."""
    global _level1_synced
    _level1_synced = False
    ProgramLog('System: Level 1 feedback link disconnected', 'warning')

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
            av._VolumeFeedbackReceived.add(room)

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
            av.ApplyMuteUI(room)

            # Send feedback to Level 1 processor
            av._SendFeedbackToLevel1('MuteFeedback', room, state=value)
            
        except Exception as e:
            ProgramLog(f'System: DSP mute feedback error - {e}', 'error')


def PartyRoomDisplayPowerHandler(command, value, qualifier):
    _HandleTVPower('PartyRoomTV', 'Party Room TV', value)


def YogaStudioDisplayPowerHandler(command, value, qualifier):
    _HandleTVPower('YogaStudioTV', 'Yoga Studio TV', value)


def PartyRoomDisplayVolumeHandler(command, value, qualifier):
    av.HandleTVLocalVolumeFeedback('PartyRoomTV', value)


def PartyRoomDisplayMuteHandler(command, value, qualifier):
    av.HandleTVLocalMuteFeedback('PartyRoomTV', value)


def YogaStudioDisplayVolumeHandler(command, value, qualifier):
    av.HandleTVLocalVolumeFeedback('YogaStudioTV', value)


def YogaStudioDisplayMuteHandler(command, value, qualifier):
    av.HandleTVLocalMuteFeedback('YogaStudioTV', value)

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

    # Subscribe before Connect so initial/reconnect queries seed real TV audio
    # state without changing the Power command used by each connection keepalive.
    devices.dvPartyRmDisplay.SubscribeStatus('Power', None, PartyRoomDisplayPowerHandler)
    devices.dvYogaStudioDisplay.SubscribeStatus('Power', None, YogaStudioDisplayPowerHandler)
    devices.dvPartyRmDisplay.SubscribeStatus('Volume', None, PartyRoomDisplayVolumeHandler)
    devices.dvPartyRmDisplay.SubscribeStatus('AudioMute', None, PartyRoomDisplayMuteHandler)
    devices.dvYogaStudioDisplay.SubscribeStatus('Volume', None, YogaStudioDisplayVolumeHandler)
    devices.dvYogaStudioDisplay.SubscribeStatus('AudioMute', None, YogaStudioDisplayMuteHandler)
    
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
    # Confirm the link whenever Level 1 sends anything so RawTcpHandler reports
    # Connected and resets its keep-alive counter (prevents false disconnect).
    devices.dvRemoteLevel1.ReceiveData = Level1FeedbackReceiveData
    try:
        devices.dvRemoteLevel1.Disconnected = Level1FeedbackDisconnected
    except Exception as e:
        ProgramLog(f'System: could not hook Level 1 Disconnected - {e}', 'warning')
    devices.dvRemoteLevel1.Connect()
    
    # Start remote control server
    remote.Start()

    ProgramLog('System: All devices connecting...', 'warning')
    ProgramLog('System: Initialization complete', 'warning')
