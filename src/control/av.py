"""
AV Control Module - Centralized control for all audio/video devices

This module handles:
* System power on/off for all rooms
* Volume and mute control via DSP
* Audio source selection and routing
* UI feedback callbacks for multi-panel synchronization
"""

# Extron Library imports
from extronlib.system import Wait, ProgramLog

# Python imports
import json

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
    'TerraceGalleryTV1': None,
    'TerraceGalleryTV2': None,
}

# Track TV power state for the Main TP power controls, keyed by the Level 1 zone
# label. Updated by the individual TV power functions and pushed to Level 1 on
# change, on (re)connect, and on system power-on (see SyncTVPowerFeedbackToLevel1).
TVPowerState = {
    'Party Room TV': 'Off',
    'Yoga Studio TV': 'Off',
    'Terrace Gallery TV 1': 'Off',
    'Terrace Gallery TV 2': 'Off',
}

# Volume slider / mute button registry for DSP feedback
_VolumeSliders = {}
_MuteButtons = {}
_VolumeFeedbackReceived = set()


def RegisterVolumeSlider(room, slider):
    """Register a slider to receive volume feedback for a room"""
    ProgramLog(f'AV: Registering volume slider for {room}', 'warning')
    _VolumeSliders[room] = slider
    ApplyVolumeUI(room)
    ProgramLog(f'AV: Slider registered for {room}, total sliders: {len(_VolumeSliders)}', 'warning')


def RegisterMuteButton(room, button):
    """Register a mute button to receive mute feedback for a room"""
    ProgramLog(f'AV: Registering mute button for {room}', 'warning')
    _MuteButtons[room] = button
    ApplyMuteUI(room)


def ApplyVolumeUI(room=None):
    """Push known room level(s) onto registered slider(s)."""
    rooms = [room] if room else list(_VolumeSliders.keys())
    for r in rooms:
        slider = _VolumeSliders.get(r)
        if slider is None or r not in _VolumeFeedbackReceived:
            continue
        level = VolumeLevel.get(r)
        if level is None:
            continue
        try:
            slider.SetFill(int(level))
            ProgramLog(f'AV: ApplyVolumeUI {r} → {level}', 'warning')
        except Exception as e:
            ProgramLog(f'AV: ApplyVolumeUI {r} failed: {e}', 'warning')


def ApplyMuteUI(room=None):
    """Push known mute state(s) onto registered mute button(s)."""
    rooms = [room] if room else list(_MuteButtons.keys())
    for r in rooms:
        button = _MuteButtons.get(r)
        if button is None:
            continue
        muted = AudioMuteState.get(r, False)
        try:
            button.SetState(1 if muted else 0)
        except Exception as e:
            ProgramLog(f'AV: ApplyMuteUI {r} failed: {e}', 'warning')


def RequestVolumeSyncFromDSP(rooms=None):
    """Query DSP for current zone levels and mute states."""
    targets = rooms if rooms else list(variables.DSP_OUTPUTS.keys())
    for room in targets:
        output = variables.DSP_OUTPUTS.get(room)
        if not output:
            continue
        try:
            devices.dvDSPLevel4.Update('OutputAttenuation', {'Output': str(output)})
            devices.dvDSPLevel4.Update('OutputMute', {'Output': str(output)})
        except Exception as e:
            ProgramLog(f'AV: Volume sync request failed for {room}: {e}', 'warning')


def RefreshLocalVolumeUI(rooms=None):
    """Re-query DSP and re-apply slider/mute fill (after TP Online / Main page)."""
    RequestVolumeSyncFromDSP(rooms)

    @Wait(0.5)
    def _apply_soon():
        ApplyVolumeUI()
        ApplyMuteUI()

    @Wait(2.0)
    def _apply_again():
        ApplyVolumeUI()
        ApplyMuteUI()


def ApplyTVLocalVolumeUI(tv_key=None):
    """Push cached TV-local volume feedback onto registered slider(s)."""
    keys = [tv_key] if tv_key else list(_TVLocalSliders.keys())
    for key in keys:
        slider = _TVLocalSliders.get(key)
        if slider is None:
            continue
        level = TVLocalVolume.get(key)
        if level is None:
            continue
        try:
            slider.SetFill(int(level))
        except Exception:
            pass


def ApplyTVLocalMuteUI(tv_key=None):
    """Push cached TV-local mute feedback onto registered button(s)."""
    keys = [tv_key] if tv_key else list(_TVLocalMuteButtons.keys())
    for key in keys:
        button = _TVLocalMuteButtons.get(key)
        if button is None:
            continue
        try:
            button.SetState(1 if TVLocalMute.get(key, False) else 0)
        except Exception:
            pass


def RefreshTVLocalVolumeUI(tv_key=None):
    ApplyTVLocalVolumeUI(tv_key)
    ApplyTVLocalMuteUI(tv_key)

    @Wait(0.5)
    def _again():
        ApplyTVLocalVolumeUI(tv_key)
        ApplyTVLocalMuteUI(tv_key)

# ========================================================================================
# Level 1 Processor Feedback
# ========================================================================================

# Map internal room names to Level 1 zone names (must match exactly)
_ZONE_NAME_MAP = {
    'PartyRoom': 'Party Room',
    'YogaStudio': 'Yoga Studio',
    'TerraceGallery': 'Terrace Gallery',
    'TerraceGalleryTV1': 'Terrace Gallery TV 1',
    'TerraceGalleryTV2': 'Terrace Gallery TV 2',
    'Gym': 'Level 4 Gym',
    'Courtyard': 'Level 4 Courtyard',
    'Party Room TV': 'Party Room TV',
    'Yoga Studio TV': 'Yoga Studio TV',
    'Terrace Gallery TV 1': 'Terrace Gallery TV 1',
    'Terrace Gallery TV 2': 'Terrace Gallery TV 2',
}

_SOURCE_TO_L1 = {
    'MusicPlayer': 'Music Player',
    'BTPlate': 'BT Plate',
    'Music': 'Music Player',
    'BT': 'BT Plate',
    'HDMI': 'HDMI',
    'Roku': 'Roku',
    'DisplayAV': 'Display A/V',
    'Display A/V': 'Display A/V',
}

def _SendFeedbackToLevel1(command, room, **kwargs):
    """Send feedback message to Level 1 processor"""
    try:
        # Check if connected to Level 1 before sending
        # Use underlying interface state which reflects actual socket status
        handler = devices.dvRemoteLevel1
        wrapped = getattr(handler, '_WrappedInterface', None)
        if wrapped is None or getattr(wrapped, 'ConnectionStatus', None) != 'Connected':
            return  # Silently drop feedback when not connected
        # Convert internal room name to Level 1 zone name
        zone = _ZONE_NAME_MAP.get(room, room)
        data = {'zone': zone}
        data.update(kwargs)
        message = json.dumps({'command': command, 'data': data}) + '\n'
        handler.Send(message)
        ProgramLog(f'AV: Sent {command} to Level1 - zone={zone}, data={kwargs}', 'warning')
    except Exception as e:
        ProgramLog(f'AV: Error sending feedback to Level1 - {e}', 'error')

def _emit_tv_power(label, state):
    """Record a TV's power state and push PowerFeedback to Level 1.

    label is the Level 1 zone label (e.g. 'Terrace Gallery TV 1'); state is
    'On' or 'Off'. Uses the existing _SendFeedbackToLevel1 format so the Main TP
    power controls stay in sync.
    """
    TVPowerState[label] = state
    _SendFeedbackToLevel1('PowerFeedback', label, state=state)

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
    """Power on Party Room: unmute zone, Music Player source. Other L4 zones untouched."""
    print('AV Control: Party Room System Power On')
    SystemPowerState['PartyRoom'] = True

    SetMute('PartyRoom', False, notifyUI=True)
    SetAudioSource('PartyRoom', 'MusicPlayer')

    @Wait(0.5)
    def Done():
        if callback:
            callback()
        _NotifyUICallbacks('PowerChanged', room='PartyRoom', power=True)


def PartyRoomSystemPowerOff(callback=None):
    """Shut down Party Room only: mute Party zone + power off TV. Music Player stays up for other zones."""
    print('AV Control: Party Room System Power Off')
    SystemPowerState['PartyRoom'] = False

    SetMute('PartyRoom', True, notifyUI=True)
    devices.dvPartyRmDisplay.Set('Power', 'Off')
    _emit_tv_power('Party Room TV', 'Off')

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
    """Power on Yoga Studio: unmute zone, Music Player source. Other L4 zones untouched."""
    print('AV Control: Yoga Studio System Power On')
    SystemPowerState['YogaStudio'] = True

    SetMute('YogaStudio', False, notifyUI=True)
    SetAudioSource('YogaStudio', 'MusicPlayer')

    @Wait(0.5)
    def Done():
        if callback:
            callback()
        _NotifyUICallbacks('PowerChanged', room='YogaStudio', power=True)


def YogaStudioSystemPowerOff(callback=None):
    """Shut down Yoga Studio only: mute Yoga zone + power off TV. Music Player stays up for other zones."""
    print('AV Control: Yoga Studio System Power Off')
    SystemPowerState['YogaStudio'] = False

    SetMute('YogaStudio', True, notifyUI=True)
    devices.dvYogaStudioDisplay.Set('Power', 'Off')
    _emit_tv_power('Yoga Studio TV', 'Off')

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
    """Power on Terrace Gallery TVs (Roku / HDMI 1). No DSP zone mute — audio is local on Frames."""
    print('AV Control: Terrace Gallery System Power On')
    SystemPowerState['TerraceGallery'] = True

    devices.dvTerraceGalleryDisplay1.Set('Power', 'On')
    devices.dvTerraceGalleryDisplay2.Set('Power', 'On')
    _emit_tv_power('Terrace Gallery TV 1', 'On')
    _emit_tv_power('Terrace Gallery TV 2', 'On')

    @Wait(2)
    def SetDefaultInputs():
        devices.dvTerraceGalleryDisplay1.Set('Input', 'HDMI 1')
        devices.dvTerraceGalleryDisplay2.Set('Input', 'HDMI 1')
        print('AV Control: Terrace Gallery - Display inputs set to HDMI 1 (Roku)')
        if callback:
            callback()
        _NotifyUICallbacks('PowerChanged', room='TerraceGallery', power=True)


def TerraceGallerySystemPowerOff(callback=None):
    """Power off Terrace TVs only. Do not mute DSP Music Player / other zones."""
    print('AV Control: Terrace Gallery System Power Off')
    SystemPowerState['TerraceGallery'] = False

    devices.dvTerraceGalleryDisplay1.Set('Power', 'Off')
    devices.dvTerraceGalleryDisplay2.Set('Power', 'Off')
    _emit_tv_power('Terrace Gallery TV 1', 'Off')
    _emit_tv_power('Terrace Gallery TV 2', 'Off')

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
    _emit_tv_power('Terrace Gallery TV 1', 'On')

def TerraceGalleryTV1PowerOff():
    """Power off Terrace Gallery TV1 only"""
    print('AV Control: Terrace Gallery TV1 Power Off')
    devices.dvTerraceGalleryDisplay1.Set('Power', 'Off')
    _emit_tv_power('Terrace Gallery TV 1', 'Off')

def TerraceGalleryTV2PowerOn():
    """Power on Terrace Gallery TV2 only"""
    print('AV Control: Terrace Gallery TV2 Power On')
    devices.dvTerraceGalleryDisplay2.Set('Power', 'On')
    _emit_tv_power('Terrace Gallery TV 2', 'On')

def TerraceGalleryTV2PowerOff():
    """Power off Terrace Gallery TV2 only"""
    print('AV Control: Terrace Gallery TV2 Power Off')
    devices.dvTerraceGalleryDisplay2.Set('Power', 'Off')
    _emit_tv_power('Terrace Gallery TV 2', 'Off')

def _terrace_select_roku(display, roku, tv_key, zone_label, roku_label):
    """Select Roku (HDMI 1) on a Terrace Frame WITHOUT risking a power-off.

    The Tizen KEY_POWER is a toggle with no state feedback, so Set('Power','On')
    can fire a "wake" KEY_POWER that turns an already-on TV OFF when the
    connect-time power assumption was 'Off'. Selecting a source proves the TV is
    on, so we ground the driver's power model to 'On' first (self-heal), send a
    harmless Wake-on-LAN to cover a genuinely-off TV, and then select the input.
    No KEY_POWER toggle is ever sent here.
    """
    # Ground power to On (no key) so the input select can't toggle the TV off.
    ground = getattr(display, 'NotePowerOn', None)
    if callable(ground):
        ground('Roku source select')
    wake = getattr(display, 'WakeOnLan', None)
    if callable(wake):
        wake()
    # Selecting the input also self-heals power=On inside the driver.
    display.Set('Input', 'HDMI 1')
    _roku_wake(roku, roku_label)
    CurrentAudioSource[tv_key] = 'Roku'
    _emit_tv_power(zone_label, 'On')
    _SendFeedbackToLevel1('SourceFeedback', zone_label, source='Roku')
    _NotifyUICallbacks('SourceChanged', room=tv_key, source='Roku')

def TerraceSelectRoku1():
    """Select Roku (HDMI 1) on Terrace TV1. Ensures TV is On, never toggles off."""
    ProgramLog('AV: TerraceSelectRoku1', 'warning')
    _terrace_select_roku(devices.dvTerraceGalleryDisplay1,
                         devices.dvTerraceGalleryRoku1,
                         'TerraceGalleryTV1', 'Terrace Gallery TV 1',
                         'Terrace Roku 1')

def TerraceSelectRoku2():
    """Select Roku (HDMI 1) on Terrace TV2. Ensures TV is On, never toggles off."""
    ProgramLog('AV: TerraceSelectRoku2', 'warning')
    _terrace_select_roku(devices.dvTerraceGalleryDisplay2,
                         devices.dvTerraceGalleryRoku2,
                         'TerraceGalleryTV2', 'Terrace Gallery TV 2',
                         'Terrace Roku 2')

def TerraceRokuKey1(action):
    return _roku_key(devices.dvTerraceGalleryRoku1, action, 'Terrace Roku 1')

def TerraceRokuKey2(action):
    return _roku_key(devices.dvTerraceGalleryRoku2, action, 'Terrace Roku 2')

def _roku_wake(roku, label):
    """Wake a Roku via ECP PowerOn."""
    if roku is None:
        ProgramLog(f'AV: {label} wake skipped — device missing', 'warning')
        return False
    try:
        ok = roku.PowerOn()
        ProgramLog(f'AV: {label} wake (PowerOn) -> {ok}', 'warning')
        return ok
    except Exception as e:
        ProgramLog(f'AV: {label} wake failed: {e}', 'error')
        return False

def _roku_key(roku, action, label):
    ProgramLog(f'AV: {label} key {action}', 'warning')
    if roku is None:
        ProgramLog(f'AV: {label} device missing', 'error')
        return False
    method = getattr(roku, action, None)
    if method is None or not callable(method):
        ProgramLog(f'AV: {label} has no action {action}', 'error')
        return False
    try:
        ok = method()
        ProgramLog(f'AV: {label} {action} -> {ok}', 'warning')
        return ok
    except Exception as e:
        ProgramLog(f'AV: {label} {action} failed: {e}', 'error')
        return False

# TV-local volume and mute ---------------------------------------------------------

_TV_LOCAL_DEVICES = {
    'PartyRoomTV': lambda: devices.dvPartyRmDisplay,
    'YogaStudioTV': lambda: devices.dvYogaStudioDisplay,
    'TerraceTV1': lambda: devices.dvTerraceGalleryDisplay1,
    'TerraceTV2': lambda: devices.dvTerraceGalleryDisplay2,
}

_TV_LOCAL_ZONE_LABELS = {
    'PartyRoomTV': 'Party Room TV',
    'YogaStudioTV': 'Yoga Studio TV',
    'TerraceTV1': 'Terrace Gallery TV 1',
    'TerraceTV2': 'Terrace Gallery TV 2',
}

# Samsung MDC NAKs Volume/AudioMute while the panel sits in standby, so audio
# commands are cached and replayed once the display reports power on.
_TV_LOCAL_POWER = {}

def _IsTVLocalPowered(tv_key):
    return _TV_LOCAL_POWER.get(tv_key, False)

def SetTVLocalPowerState(tv_key, powered):
    """Record real display power and replay cached audio when it comes on."""
    powered = bool(powered)
    was_powered = _TV_LOCAL_POWER.get(tv_key)
    _TV_LOCAL_POWER[tv_key] = powered
    if powered and not was_powered:
        ApplyPendingTVLocalAudio(tv_key)
    return powered

def RequestTVLocalAudioFeedback(tv_key):
    """Query real Volume/AudioMute, but only while the display is awake."""
    getter = _TV_LOCAL_DEVICES.get(tv_key)
    if not getter or not _IsTVLocalPowered(tv_key):
        return False
    try:
        device = getter()
        device.Update('Volume')
        device.Update('AudioMute')
        return True
    except Exception as e:
        ProgramLog(f'AV: RequestTVLocalAudioFeedback {tv_key} failed: {e}', 'error')
        return False

def ApplyPendingTVLocalAudio(tv_key):
    """Push cached volume/mute to a display that just powered on, then resync."""
    getter = _TV_LOCAL_DEVICES.get(tv_key)
    if not getter:
        return
    level = TVLocalVolume.get(tv_key)
    muted = TVLocalMute.get(tv_key, False)
    try:
        device = getter()
        if level is not None:
            device.Set('Volume', int(level))
        device.Set('AudioMute', 'On' if muted else 'Off')
    except Exception as e:
        ProgramLog(f'AV: ApplyPendingTVLocalAudio {tv_key} failed: {e}', 'error')

    @Wait(2)
    def _query_real_state():
        RequestTVLocalAudioFeedback(tv_key)

TVLocalVolume = {
    'PartyRoomTV': 20,
    'YogaStudioTV': 20,
    'TerraceTV1': 20,
    'TerraceTV2': 20,
}

TVLocalMute = {
    'PartyRoomTV': False,
    'YogaStudioTV': False,
    'TerraceTV1': False,
    'TerraceTV2': False,
}

_TVLocalSliders = {}
_TVLocalMuteButtons = {}

def RegisterTVLocalVolumeSlider(tv_key, slider):
    _TVLocalSliders[tv_key] = slider
    ApplyTVLocalVolumeUI(tv_key)

def RegisterTVLocalMuteButton(tv_key, button):
    _TVLocalMuteButtons[tv_key] = button
    ApplyTVLocalMuteUI(tv_key)

def PreviewTVLocalVolume(tv_key, level):
    level = max(0, min(100, int(level)))
    TVLocalVolume[tv_key] = level
    slider = _TVLocalSliders.get(tv_key)
    if slider is not None:
        try:
            slider.SetFill(level)
        except Exception:
            pass

def SetTVLocalVolume(tv_key, level):
    level = max(0, min(100, int(level)))
    TVLocalVolume[tv_key] = level
    slider = _TVLocalSliders.get(tv_key)
    if slider is not None:
        try:
            slider.SetFill(level)
        except Exception:
            pass
    getter = _TV_LOCAL_DEVICES.get(tv_key)
    if not getter:
        return
    if not _IsTVLocalPowered(tv_key):
        ProgramLog(f'AV: {tv_key} volume cached at {level} - display is off', 'warning')
    else:
        try:
            getter().Set('Volume', level)
        except Exception as e:
            ProgramLog(f'AV: SetTVLocalVolume {tv_key} failed: {e}', 'error')
    label = _TV_LOCAL_ZONE_LABELS.get(tv_key)
    if label:
        _SendFeedbackToLevel1('VolumeFeedback', label, level=level)

def SetTVLocalMute(tv_key, mute_state):
    mute_state = bool(mute_state)
    TVLocalMute[tv_key] = mute_state
    ApplyTVLocalMuteUI(tv_key)
    getter = _TV_LOCAL_DEVICES.get(tv_key)
    if not getter:
        return mute_state
    if not _IsTVLocalPowered(tv_key):
        state_text = 'On' if mute_state else 'Off'
        ProgramLog(f'AV: {tv_key} mute cached as {state_text} - display is off', 'warning')
    else:
        try:
            getter().Set('AudioMute', 'On' if mute_state else 'Off')
        except Exception as e:
            ProgramLog(f'AV: SetTVLocalMute {tv_key} failed: {e}', 'error')
    label = _TV_LOCAL_ZONE_LABELS.get(tv_key)
    if label:
        _SendFeedbackToLevel1(
            'MuteFeedback', label, state='On' if mute_state else 'Off'
        )
    return mute_state

def ToggleTVLocalMute(tv_key):
    new_state = not TVLocalMute.get(tv_key, False)
    return SetTVLocalMute(tv_key, new_state)

def HandleTVLocalVolumeFeedback(tv_key, value):
    """Cache real display volume feedback, update UI, and notify Level 1."""
    try:
        level = max(0, min(100, int(value)))
    except (TypeError, ValueError):
        ProgramLog(f'AV: Invalid TV volume feedback {tv_key}={value}', 'warning')
        return
    TVLocalVolume[tv_key] = level
    ApplyTVLocalVolumeUI(tv_key)
    label = _TV_LOCAL_ZONE_LABELS.get(tv_key)
    if label:
        _SendFeedbackToLevel1('VolumeFeedback', label, level=level)

def HandleTVLocalMuteFeedback(tv_key, value):
    """Cache real display mute feedback, update UI, and notify Level 1."""
    muted = value == 'On'
    TVLocalMute[tv_key] = muted
    ApplyTVLocalMuteUI(tv_key)
    label = _TV_LOCAL_ZONE_LABELS.get(tv_key)
    if label:
        _SendFeedbackToLevel1(
            'MuteFeedback', label, state='On' if muted else 'Off'
        )

def PartyRoomTVPowerOn():
    """Power on Party Room TV"""
    print('AV Control: Party Room TV Power On')
    devices.dvPartyRmDisplay.Set('Power', 'On')
    _emit_tv_power('Party Room TV', 'On')

def PartyRoomTVPowerOff():
    """Power off Party Room TV"""
    print('AV Control: Party Room TV Power Off')
    devices.dvPartyRmDisplay.Set('Power', 'Off')
    _emit_tv_power('Party Room TV', 'Off')

def YogaStudioTVPowerOn():
    """Power on Yoga Studio TV"""
    print('AV Control: Yoga Studio TV Power On')
    devices.dvYogaStudioDisplay.Set('Power', 'On')
    _emit_tv_power('Yoga Studio TV', 'On')

def YogaStudioTVPowerOff():
    """Power off Yoga Studio TV"""
    print('AV Control: Yoga Studio TV Power Off')
    devices.dvYogaStudioDisplay.Set('Power', 'Off')
    _emit_tv_power('Yoga Studio TV', 'Off')

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
    ProgramLog(f'AV: SetVolume called - room={room}, level={level}', 'warning')
    if room not in variables.DSP_OUTPUTS:
        ProgramLog(f'AV: Warning - Unknown room {room}', 'warning')
        return
    
    # Clamp volume to valid range
    level = max(variables.VOLUME_MIN, min(variables.VOLUME_MAX, level))
    VolumeLevel[room] = level
    
    # Scale to DSP range
    dspLevel = ScaleVolume(level)
    output = variables.DSP_OUTPUTS[room]
    
    ProgramLog(f'AV: Converted UI level {level} to DSP value {dspLevel}dB', 'warning')
    ProgramLog(f'AV: Setting OutputAttenuation for {room} (Output {output}) to {dspLevel}dB', 'warning')
    devices.dvDSPLevel4.Set('OutputAttenuation', dspLevel, {'Output': output})
    _VolumeFeedbackReceived.add(room)

    slider = _VolumeSliders.get(room)
    if slider is not None:
        try:
            slider.SetFill(int(level))
        except Exception:
            pass

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
        muteState: True to mute, False to unmute
        notifyUI: Whether to notify UI callbacks (set False to prevent feedback loops)
    """
    ProgramLog(f'AV: SetMute called - room={room}, state={muteState}', 'warning')
    if room not in variables.DSP_OUTPUTS:
        ProgramLog(f'AV: Warning - Unknown room {room}', 'warning')
        return
    
    AudioMuteState[room] = muteState
    output = variables.DSP_OUTPUTS[room]
    dspMuteValue = 'On' if muteState else 'Off'
    
    ProgramLog(f'AV: Setting OutputMute for {room} (Output {output}) to {dspMuteValue}', 'warning')
    devices.dvDSPLevel4.Set('OutputMute', dspMuteValue, {'Output': output})
    ApplyMuteUI(room)

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
    End the Gym UI power sequence without interrupting continuous BGM.
    
    Args:
        callback: Optional callback function to execute after power off sequence completes
    """
    print('AV Control: Gym System Power Off')

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
    End the Courtyard UI power sequence without interrupting continuous BGM.
    
    Args:
        callback: Optional callback function to execute after power off sequence completes
    """
    print('AV Control: Courtyard System Power Off')

    if callback:
        callback()

# ========================================================================================
# DSP Audio Source Selection Functions
# ========================================================================================

def _GetMixpointInput(inputType, inputChannel):
    """Resolve the Input qualifier value for MixpointGain/MixpointMute based on input type."""
    if inputType == 'VirtualReceive':
        return f'V. Return {inputChannel}'
    else:  # Analog or Dante - both use numeric channel string '1'-'12'
        return inputChannel


def _IsProtectedVirtualReturn(inputType, inputChannel):
    return (
        inputType == 'VirtualReceive'
        and str(inputChannel) in variables.DSP_PROTECTED_VIRTUAL_RETURNS
    )

def SetMixpointLevel(inputType, inputChannel, outputChannel, level):
    """
    Set mixpoint gain (crosspoint level) for any input type.
    All inputs use MixpointGain with {'Input': ..., 'Output': ...}.
    Analog/Dante use numeric channel string; VirtualReceive uses 'V. Return X'.
    """
    inputKey = _GetMixpointInput(inputType, inputChannel)
    ProgramLog(f'AV: MixpointGain - Input={inputKey}, Output={outputChannel}, Level={level}dB', 'warning')
    devices.dvDSPLevel4.Set('MixpointGain', level, {'Input': inputKey, 'Output': outputChannel})

def SetMixpointMute(inputType, inputChannel, outputChannel, muteState):
    """
    Set mixpoint mute (crosspoint mute) for any input type.
    All inputs use MixpointMute with {'Input': ..., 'Output': ...}.
    Analog/Dante use numeric channel string; VirtualReceive uses 'V. Return X'.
    """
    if _IsProtectedVirtualReturn(inputType, inputChannel) and muteState != 'On':
        ProgramLog(
            f'AV: Blocking unmute of protected Virtual Return {inputChannel}',
            'warning',
        )
        muteState = 'On'
    inputKey = _GetMixpointInput(inputType, inputChannel)
    ProgramLog(f'AV: MixpointMute - Input={inputKey}, Output={outputChannel}, Mute={muteState}', 'warning')
    devices.dvDSPLevel4.Set('MixpointMute', muteState, {'Input': inputKey, 'Output': outputChannel})


def ProtectTVReturns():
    """Globally mute TV returns C/F and their local room crosspoints."""
    for channel in variables.DSP_PROTECTED_VIRTUAL_RETURNS:
        devices.dvDSPLevel4.Set(
            'VirtualReturnMute', 'On', {'Input': channel}
        )
    for room, source in variables.ROOM_TV_SOURCE.items():
        sourceConfig = variables.DSP_INPUTS[source]
        SetMixpointMute(
            sourceConfig['Type'],
            sourceConfig['Channel'],
            variables.DSP_OUTPUTS[room],
            'On',
        )


def InitializeDSPRouting():
    """Apply safe global mutes and permanent BGM routes after DSP connect."""
    ProtectTVReturns()
    for route in variables.DSP_CONTINUOUS_ROUTES:
        inputType = route['InputType']
        inputChannel = route['Input']
        outputChannel = route['Output']
        SetMixpointLevel(inputType, inputChannel, outputChannel, 0)
        SetMixpointMute(inputType, inputChannel, outputChannel, 'Off')
        devices.dvDSPLevel4.Set(
            'OutputMute', 'Off', {'Output': outputChannel}
        )


def _SilenceManagedRoomAudio(room):
    """Mute every ceiling source for Yoga/Party while TV audio stays local."""
    output = variables.DSP_OUTPUTS[room]
    for sourceConfig in variables.AUDIO_SOURCES[room].values():
        SetMixpointMute(
            sourceConfig['Type'], sourceConfig['Channel'], output, 'On'
        )
    tvSource = variables.ROOM_TV_SOURCE[room]
    tvConfig = variables.DSP_INPUTS[tvSource]
    SetMixpointMute(tvConfig['Type'], tvConfig['Channel'], output, 'On')
    ProtectTVReturns()

def SetAudioSource(room, source):
    """
    Set audio source for a room using DSP mixpoint routing
    Handles both Analog and Dante inputs
    
    Args:
        room: Room name ('PartyRoom', 'YogaStudio')
        source: Source name ('MusicPlayer', 'BTPlate')
    """
    ProgramLog(f'AV: SetAudioSource called - room={room}, source={source}', 'warning')
    if room not in variables.AUDIO_SOURCES:
        ProgramLog(f'AV: Warning - Unknown room {room} for audio source', 'warning')
        return
    
    if source not in variables.AUDIO_SOURCES[room]:
        ProgramLog(f'AV: Warning - Unknown source {source} for room {room}', 'warning')
        return
    
    CurrentAudioSource[room] = source
    output = variables.DSP_OUTPUTS[room]
    
    ProgramLog(f'AV: Setting {room} audio source to {source}', 'warning')
    _NotifyUICallbacks('SourceChanged', room=room, source=source)
    _SendFeedbackToLevel1(
        'SourceFeedback',
        _ZONE_NAME_MAP.get(room, room),
        source=_SOURCE_TO_L1.get(source, source),
    )
    
    # Clear this room's TV routing crosspoint before switching to Music/BT source
    if room in variables.ROOM_TV_SOURCE:
        tvSource = variables.ROOM_TV_SOURCE[room]
        tvConfig = variables.DSP_INPUTS[tvSource]
        ProgramLog(f'AV: Clearing TV crosspoint for {room} ({tvSource}) before source switch', 'warning')
        SetMixpointMute(tvConfig['Type'], tvConfig['Channel'], output, 'On')
    ProtectTVReturns()
    
    # Configure all sources: set level and unmute for selected, just mute for unselected
    for srcName, srcConfig in variables.AUDIO_SOURCES[room].items():
        srcType = srcConfig['Type']
        isSelected = (srcName == source)
        
        if isSelected:
            # Selected source: Set crosspoint level to 0dB (unity gain) and unmute
            ProgramLog(f'AV: Activating {srcType} source {srcName} - Setting level to 0dB and unmuting for {room}', 'warning')
            if 'Channel' in srcConfig:
                if srcType == 'VirtualReceive' and not _IsProtectedVirtualReturn(
                    srcType, srcConfig['Channel']
                ):
                    devices.dvDSPLevel4.Set(
                        'VirtualReturnMute',
                        'Off',
                        {'Input': srcConfig['Channel']},
                    )
                SetMixpointLevel(srcType, srcConfig['Channel'], output, 0)
                SetMixpointMute(srcType, srcConfig['Channel'], output, 'Off')
            elif 'Channels' in srcConfig:
                for channel in srcConfig['Channels']:
                    SetMixpointLevel(srcType, channel, output, 0)
                    SetMixpointMute(srcType, channel, output, 'Off')
        else:
            # Unselected source: Just mute (don't change level)
            ProgramLog(f'AV: Deactivating {srcType} source {srcName} - Muting for {room}', 'warning')
            if 'Channel' in srcConfig:
                SetMixpointMute(srcType, srcConfig['Channel'], output, 'On')
            elif 'Channels' in srcConfig:
                for channel in srcConfig['Channels']:
                    SetMixpointMute(srcType, channel, output, 'On')
    
    ProgramLog(f'AV: Source routing complete for {room} -> {source}', 'warning')

def GetCurrentAudioSource(room):
    """Get current audio source for a room"""
    return CurrentAudioSource.get(room)

def PartyRoomSelectMusicPlayer():
    """Select Music Player as Party Room audio source"""
    SetAudioSource('PartyRoom', 'MusicPlayer')

def PartyRoomSelectBTPlate():
    """Select Bluetooth Plate as Party Room audio source"""
    SetAudioSource('PartyRoom', 'BTPlate')

def PartyRoomSelectHDMI():
    """External HDMI → TV HDMI 1; ceiling stays silent, TV audio stays local."""
    ProgramLog('AV: PartyRoomSelectHDMI', 'warning')
    devices.dvPartyRmDisplay.Set('Power', 'On')
    devices.dvPartyRmDisplay.Set('Input', 'HDMI 1')
    _SilenceManagedRoomAudio('PartyRoom')
    CurrentAudioSource['PartyRoom'] = 'HDMI'
    _emit_tv_power('Party Room TV', 'On')
    _SendFeedbackToLevel1('SourceFeedback', 'Party Room', source='HDMI')
    _NotifyUICallbacks('SourceChanged', room='PartyRoom', source='HDMI')

def PartyRoomSelectRoku():
    """Roku → TV HDMI 2; ceiling stays silent, TV audio stays local."""
    ProgramLog('AV: PartyRoomSelectRoku', 'warning')
    devices.dvPartyRmDisplay.Set('Power', 'On')
    devices.dvPartyRmDisplay.Set('Input', 'HDMI 2')
    _SilenceManagedRoomAudio('PartyRoom')
    CurrentAudioSource['PartyRoom'] = 'Roku'
    _roku_wake(getattr(devices, 'dvPartyRoomRoku', None), 'Party Room Roku')
    _emit_tv_power('Party Room TV', 'On')
    _SendFeedbackToLevel1('SourceFeedback', 'Party Room', source='Roku')
    _NotifyUICallbacks('SourceChanged', room='PartyRoom', source='Roku')

def PartyRoomRokuKey(action):
    roku = getattr(devices, 'dvPartyRoomRoku', None)
    if roku is None:
        ProgramLog('AV: Party Room Roku device missing', 'error')
        return False
    method = getattr(roku, action, None)
    if method is None or not callable(method):
        ProgramLog(f'AV: Party Room Roku has no action {action}', 'error')
        return False
    try:
        return method()
    except Exception as e:
        ProgramLog(f'AV: Party Room Roku {action} failed: {e}', 'error')
        return False

def YogaStudioSelectMusicPlayer():
    """Select Music Player as Yoga Studio audio source"""
    SetAudioSource('YogaStudio', 'MusicPlayer')

def YogaStudioSelectBTPlate():
    """Select Bluetooth Plate as Yoga Studio audio source"""
    SetAudioSource('YogaStudio', 'BTPlate')

def YogaStudioSelectDisplayAV():
    """Power the TV; ceiling stays silent and TV audio stays on the soundbar."""
    ProgramLog('AV: YogaStudioSelectDisplayAV', 'warning')
    devices.dvYogaStudioDisplay.Set('Power', 'On')
    devices.dvYogaStudioDisplay.Set('Input', 'HDMI 1')
    _SilenceManagedRoomAudio('YogaStudio')
    CurrentAudioSource['YogaStudio'] = 'DisplayAV'
    _emit_tv_power('Yoga Studio TV', 'On')
    _SendFeedbackToLevel1('SourceFeedback', 'Yoga Studio', source='Display A/V')
    _NotifyUICallbacks('SourceChanged', room='YogaStudio', source='DisplayAV')

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
        ProgramLog(f'AV: ERROR - Unknown source {source}', 'error')
        return
    
    if zone not in variables.DSP_OUTPUTS:
        ProgramLog(f'AV: ERROR - Unknown zone {zone}', 'error')
        return
    
    sourceConfig = variables.DSP_INPUTS[source]
    outputChannel = variables.DSP_OUTPUTS[zone]
    srcType = sourceConfig['Type']

    if _IsProtectedVirtualReturn(srcType, sourceConfig.get('Channel')):
        ProgramLog(
            f'AV: RouteAudioToZone blocked for protected source {source}',
            'warning',
        )
        ProtectTVReturns()
        return False
    
    ProgramLog(f'AV: RouteAudioToZone - {source} ({srcType}) -> {zone} (Output {outputChannel})', 'warning')
    
    # Mute current audio source crosspoint for this zone (if zone has a managed audio source)
    if zone in variables.AUDIO_SOURCES:
        currentSource = CurrentAudioSource.get(zone)
        if currentSource and currentSource in variables.AUDIO_SOURCES[zone]:
            srcCfg = variables.AUDIO_SOURCES[zone][currentSource]
            ProgramLog(f'AV: Muting current source {currentSource} crosspoint for {zone}', 'warning')
            SetMixpointMute(srcCfg['Type'], srcCfg['Channel'], outputChannel, 'On')
    
    if 'Channel' in sourceConfig:
        SetMixpointLevel(srcType, sourceConfig['Channel'], outputChannel, 0)
        SetMixpointMute(srcType, sourceConfig['Channel'], outputChannel, 'Off')
    elif 'Channels' in sourceConfig:
        for channel in sourceConfig['Channels']:
            SetMixpointLevel(srcType, channel, outputChannel, 0)
            SetMixpointMute(srcType, channel, outputChannel, 'Off')
    return True

def RouteAudioToAllZones(source):
    """Route audio from a source to all zones"""
    if source not in variables.DSP_INPUTS:
        ProgramLog(f'AV: ERROR - Unknown source {source}', 'error')
        return
    
    sourceConfig = variables.DSP_INPUTS[source]
    srcType = sourceConfig['Type']

    if _IsProtectedVirtualReturn(srcType, sourceConfig.get('Channel')):
        ProgramLog(
            f'AV: RouteAudioToAllZones blocked for protected source {source}',
            'warning',
        )
        ProtectTVReturns()
        return False
    
    ProgramLog(f'AV: RouteAudioToAllZones - {source} ({srcType}) -> ALL ZONES', 'warning')
    
    for zoneName, outputChannel in variables.DSP_OUTPUTS.items():
        # Mute current audio source crosspoint for this zone (if zone has a managed audio source)
        if zoneName in variables.AUDIO_SOURCES:
            currentSource = CurrentAudioSource.get(zoneName)
            if currentSource and currentSource in variables.AUDIO_SOURCES[zoneName]:
                srcCfg = variables.AUDIO_SOURCES[zoneName][currentSource]
                ProgramLog(f'AV: Muting current source {currentSource} crosspoint for {zoneName}', 'warning')
                SetMixpointMute(srcCfg['Type'], srcCfg['Channel'], outputChannel, 'On')
        
        if 'Channel' in sourceConfig:
            SetMixpointLevel(srcType, sourceConfig['Channel'], outputChannel, 0)
            SetMixpointMute(srcType, sourceConfig['Channel'], outputChannel, 'Off')
        elif 'Channels' in sourceConfig:
            for channel in sourceConfig['Channels']:
                SetMixpointLevel(srcType, channel, outputChannel, 0)
                SetMixpointMute(srcType, channel, outputChannel, 'Off')
    return True

def ClearAudioRouting(source):
    """Clear all audio routing from a source"""
    if source not in variables.DSP_INPUTS:
        ProgramLog(f'AV: ERROR - Unknown source {source}', 'error')
        return
    
    sourceConfig = variables.DSP_INPUTS[source]
    srcType = sourceConfig['Type']
    
    ProgramLog(f'AV: ClearAudioRouting - Muting all outputs for {source} ({srcType})', 'warning')
    
    for zoneName, outputChannel in variables.DSP_OUTPUTS.items():
        if 'Channel' in sourceConfig:
            SetMixpointMute(srcType, sourceConfig['Channel'], outputChannel, 'On')
        elif 'Channels' in sourceConfig:
            for channel in sourceConfig['Channels']:
                SetMixpointMute(srcType, channel, outputChannel, 'On')
        
        # Restore current audio source crosspoint for this zone (if zone has a managed audio source)
        if zoneName in variables.AUDIO_SOURCES:
            currentSource = CurrentAudioSource.get(zoneName)
            if currentSource and currentSource in variables.AUDIO_SOURCES[zoneName]:
                srcCfg = variables.AUDIO_SOURCES[zoneName][currentSource]
                ProgramLog(f'AV: Restoring current source {currentSource} crosspoint for {zoneName}', 'warning')
                SetMixpointLevel(srcCfg['Type'], srcCfg['Channel'], outputChannel, 0)
                SetMixpointMute(srcCfg['Type'], srcCfg['Channel'], outputChannel, 'Off')

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


def SyncSourceFeedbackToLevel1():
    """Push current audio source selections to Level 1."""
    for room, source in CurrentAudioSource.items():
        if not source:
            continue
        zone = _ZONE_NAME_MAP.get(room, room)
        display = _SOURCE_TO_L1.get(source, source)
        _SendFeedbackToLevel1('SourceFeedback', zone, source=display)


def SyncTVPowerFeedbackToLevel1(label=None):
    """Push tracked TV power state(s) to Level 1 using the existing PowerFeedback
    format. Pass a single zone label (e.g. 'Terrace Gallery TV 1') to push just
    that TV (used on per-device reconnect), or None to push all four TVs (used
    on Level 1 (re)connect / system power-on)."""
    labels = [label] if label else list(TVPowerState.keys())
    for lbl in labels:
        if lbl not in TVPowerState:
            continue
        _SendFeedbackToLevel1('PowerFeedback', lbl, state=TVPowerState[lbl])


def SyncAudioFeedbackToLevel1():
    """Push cached DSP-zone and Party/Yoga TV-local audio state to Level 1.

    Used on cold start / Level 1 (re)connect so the Main TP Audio Zones page is
    populated before the next device change event. Does not replace live
    feedback handlers.
    """
    for room in VolumeLevel:
        level = VolumeLevel.get(room)
        if level is None:
            continue
        _SendFeedbackToLevel1('VolumeFeedback', room, level=int(level))
    for room in AudioMuteState:
        muted = AudioMuteState.get(room, False)
        _SendFeedbackToLevel1(
            'MuteFeedback', room, state='On' if muted else 'Off'
        )
    for tv_key, label in _TV_LOCAL_ZONE_LABELS.items():
        _SendFeedbackToLevel1(
            'VolumeFeedback', label, level=int(TVLocalVolume[tv_key])
        )
        _SendFeedbackToLevel1(
            'MuteFeedback', label,
            state='On' if TVLocalMute[tv_key] else 'Off'
        )


def SyncPowerFeedbackToLevel1():
    """Push all tracked TV power states to Level 1 (Main TP power controls)."""
    SyncTVPowerFeedbackToLevel1()


def HandleSyncFeedbackRequest():
    """Push current source + TV power + audio zone volume/mute to Level 1.
    Called on Level 1 sync request (e.g. system power-on).

    RouteFeedback is intentionally omitted: Level 1 no longer has Party/Yoga
    (or Terrace) TV Send-to toggles on the Main TP.
    """
    SyncSourceFeedbackToLevel1()
    SyncTVPowerFeedbackToLevel1()
    SyncAudioFeedbackToLevel1()
    return True
