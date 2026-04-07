# DSP Volume Feedback Implementation Guide

## Summary
This guide documents the complete implementation of DSP volume feedback with comprehensive logging for Extron control systems.

---

## 1. CRITICAL: Logging System

**Use `ProgramLog()` instead of `print()` in Extron control systems**

```python
# Import
from extronlib.system import Wait, ProgramLog

# Usage
ProgramLog(f'AV: Setting volume to {level}', 'warning')  # Info/debug messages
ProgramLog(f'System: Connection failed: {error}', 'error')  # Error messages
```

---

## 2. CRITICAL: Slider Updates

**Extron Slider objects use direct property assignment, NOT methods**

```python
# CORRECT ✅
slider.Level = ui_level

# WRONG ❌ (these methods don't exist)
slider.SetLevel(ui_level)
slider.SetValue(ui_level)
```

---

## 3. ConnectionHandler Pattern for DSP

**File: `src/devices.py`**

```python
from modules.helper.ConnectionHandler import GetConnectionHandler
import modules.device.extr_dsp_DMP128_FlexPlus_v1_0_9_0 as modDSP

# Create module interface first
moduleInterfaceDSP = modDSP.SSHClass('172.22.10.219', 22023, 
                                      Credentials=('admin', 'extron'), 
                                      Model='DMP 128 FlexPlus C AT')

# Wrap with ConnectionHandler for automatic reconnection
dvDSPLevel3 = GetConnectionHandler(moduleInterfaceDSP, 'PartNumber', pollFrequency=3)
```

**Parameters:**
- `'PartNumber'` = name of Update function (without "Update" prefix) for keep-alive polling
- `pollFrequency=3` = poll every 3 seconds

---

## 4. DSP Connection Event Handler

**File: `src/system.py`**

```python
from extronlib.system import Wait, ProgramLog
import devices

# Connection handler - triggers when DSP connects/disconnects
def _dsp_connection_handler(command, value, qualifier):
    ProgramLog(f'System: DSP connection status changed - {command}: {value}', 'warning')
    if command == 'ConnectionStatus' and value == 'Connected':
        ProgramLog('System: DSP connected, initializing volume feedback', 'warning')
        # Request initial volume levels for all outputs to trigger feedback
        devices.dvDSPLevel3.Update('OutputAttenuation', {'Output': '5'})  # ArtStudio
        devices.dvDSPLevel3.Update('OutputAttenuation', {'Output': '8'})  # GameLounge
        devices.dvDSPLevel3.Update('ExpansionOutputAttenuation', {'Output': '1'})  # BowlingAlley
        ProgramLog('System: Volume feedback initialization complete', 'warning')

# Subscribe to connection status BEFORE connecting
ProgramLog('System: Subscribing to DSP connection status', 'warning')
devices.dvDSPLevel3.SubscribeStatus('ConnectionStatus', None, _dsp_connection_handler)

# Connect DSP (ConnectionHandler manages reconnection automatically)
ProgramLog('System: Connecting to DSP', 'warning')
devices.dvDSPLevel3.Connect()
```

---

## 5. DSP Feedback Handlers

**File: `src/control/av.py`**

```python
from extronlib.system import Wait, ProgramLog
import devices

# Slider registry
_VolumeSliders = {}

def RegisterVolumeSlider(room, slider):
    """Register a slider to receive volume feedback for a room"""
    ProgramLog(f'AV: Registering volume slider for {room}', 'warning')
    _VolumeSliders[room] = slider
    ProgramLog(f'AV: Slider registered for {room}, total sliders: {len(_VolumeSliders)}', 'warning')

# Feedback handler for standard DMP outputs
def _dsp_output_attenuation_feedback(command, value, qualifier):
    """Handle DSP output attenuation feedback and update sliders"""
    ProgramLog(f'AV: DSP output attenuation feedback - command={command}, value={value}dB, qualifier={qualifier}', 'warning')
    try:
        output = qualifier.get('Output')
        # Convert DSP value (-80 to 0 dB) to UI range (0-100)
        ui_level = int((value + 80) / 80.0 * 100)
        ui_level = max(0, min(100, ui_level))
        ProgramLog(f'AV: Converted {value}dB to UI level {ui_level} for output {output}', 'warning')
        
        # Find which room uses this output
        for room, out in [('ArtStudio', ('DMP', '5')), ('GameLounge', ('DMP', '8'))]:
            if out[1] == output:
                ProgramLog(f'AV: Updating {room} volume to {ui_level}', 'warning')
                VolumeLevel[room] = ui_level
                slider = _VolumeSliders.get(room)
                if slider:
                    ProgramLog(f'AV: Setting slider for {room} to {ui_level}', 'warning')
                    slider.Level = ui_level  # CRITICAL: Use .Level property
                else:
                    ProgramLog(f'AV: Warning - No slider registered for {room}', 'warning')
                break
    except Exception as e:
        ProgramLog(f'AV: DSP feedback error - {e}', 'error')

# Feedback handler for expansion outputs (AXI)
def _dsp_expansion_output_attenuation_feedback(command, value, qualifier):
    """Handle DSP expansion output attenuation feedback and update sliders"""
    ProgramLog(f'AV: DSP expansion output attenuation feedback - command={command}, value={value}dB, qualifier={qualifier}', 'warning')
    try:
        output = qualifier.get('Output')
        # Convert DSP value (-80 to 0 dB) to UI range (0-100)
        ui_level = int((value + 80) / 80.0 * 100)
        ui_level = max(0, min(100, ui_level))
        ProgramLog(f'AV: Converted {value}dB to UI level {ui_level} for expansion output {output}', 'warning')
        
        # Find which room uses this expansion output
        for room, out in [('BowlingAlley', ('AXI', 'Exp. 1'))]:
            if out[0] == 'AXI' and out[1].split(' ')[1] == output:
                ProgramLog(f'AV: Updating {room} volume to {ui_level}', 'warning')
                VolumeLevel[room] = ui_level
                slider = _VolumeSliders.get(room)
                if slider:
                    ProgramLog(f'AV: Setting slider for {room} to {ui_level}', 'warning')
                    slider.Level = ui_level  # CRITICAL: Use .Level property
                else:
                    ProgramLog(f'AV: Warning - No slider registered for {room}', 'warning')
                break
    except Exception as e:
        ProgramLog(f'AV: DSP expansion feedback error - {e}', 'error')

# Subscribe to DSP output changes at MODULE LOAD TIME (not in Initialize)
ProgramLog('AV: Subscribing to DSP output attenuation feedback', 'warning')
devices.dvDSPLevel3.SubscribeStatus('OutputAttenuation', {'Output': '5'}, _dsp_output_attenuation_feedback)
ProgramLog('AV: Subscribed to OutputAttenuation for output 5 (ArtStudio)', 'warning')
devices.dvDSPLevel3.SubscribeStatus('OutputAttenuation', {'Output': '8'}, _dsp_output_attenuation_feedback)
ProgramLog('AV: Subscribed to OutputAttenuation for output 8 (GameLounge)', 'warning')
devices.dvDSPLevel3.SubscribeStatus('ExpansionOutputAttenuation', {'Output': '1'}, _dsp_expansion_output_attenuation_feedback)
ProgramLog('AV: Subscribed to ExpansionOutputAttenuation for output 1 (BowlingAlley)', 'warning')
ProgramLog('AV: All DSP subscriptions registered', 'warning')
```

---

## 6. Slider Registration in UI Files

**Files: `src/ui/artstudio_tlp.py`, `src/ui/bowlingalley_tlp.py`, `src/ui/gamelounge_tlp.py`**

```python
import control.av as av

# Define slider
ArtStudioVolumeLvl = Slider(dvTLPArtStudio, 122)

# Register slider for DSP feedback (at module load time)
av.RegisterVolumeSlider('ArtStudio', ArtStudioVolumeLvl)
```

---

## 7. Comprehensive Logging for Volume/Mute Operations

**File: `src/control/av.py`**

```python
def SetVolume(room, level):
    level = max(0, min(100, int(level)))
    ProgramLog(f'AV: SetVolume called - room={room}, level={level}', 'warning')
    VolumeLevel[room] = level
    if room in ('ConferenceRoomA', 'ConferenceRoomB'):
        ProgramLog(f'AV: Setting TV volume for {room} to {level}', 'warning')
        tv = devices.dvConferenceRoomA if room == 'ConferenceRoomA' else devices.dvConferenceRoomB
        tv.Set('Volume', level)
    else:
        out = _dsp_output(room)
        if not out:
            ProgramLog(f'AV: Warning - No DSP output defined for {room}', 'warning')
            return
        output_type, output_channel = out
        # Map 0-100 UI to -80..0 dB approx
        dsp = int((level / 100.0) * 80 - 80)
        ProgramLog(f'AV: Converted UI level {level} to DSP value {dsp}dB', 'warning')
        # Use ExpansionOutputAttenuation for AXI outputs, OutputAttenuation for DMP outputs
        if output_type == 'AXI':
            channel_num = output_channel.split(' ')[1]
            ProgramLog(f'AV: Setting ExpansionOutputAttenuation for channel {channel_num} to {dsp}dB', 'warning')
            devices.dvDSPLevel3.Set('ExpansionOutputAttenuation', dsp, {'Output': channel_num})
        else:
            ProgramLog(f'AV: Setting OutputAttenuation for channel {output_channel} to {dsp}dB', 'warning')
            devices.dvDSPLevel3.Set('OutputAttenuation', dsp, {'Output': output_channel})
    _notify('VolumeChanged', room=room, level=level)

def SetMute(room, state):
    ProgramLog(f'AV: SetMute called - room={room}, state={state}', 'warning')
    AudioMuteState[room] = state
    if room in ('ConferenceRoomA', 'ConferenceRoomB'):
        ProgramLog(f'AV: Setting TV mute for {room} to {"On" if state else "Off"}', 'warning')
        tv = devices.dvConferenceRoomA if room == 'ConferenceRoomA' else devices.dvConferenceRoomB
        tv.Set('AudioMute', 'On' if state else 'Off')
    else:
        out = _dsp_output(room)
        if not out:
            ProgramLog(f'AV: Warning - No DSP output defined for {room}', 'warning')
            return
        output_type, output_channel = out
        if output_type == 'AXI':
            channel_num = output_channel.split(' ')[1]
            ProgramLog(f'AV: Setting ExpansionOutputMute for channel {channel_num} to {"On" if state else "Off"}', 'warning')
            devices.dvDSPLevel3.Set('ExpansionOutputMute', 'On' if state else 'Off', {'Output': channel_num})
        else:
            ProgramLog(f'AV: Setting OutputMute for channel {output_channel} to {"On" if state else "Off"}', 'warning')
            devices.dvDSPLevel3.Set('OutputMute', 'On' if state else 'Off', {'Output': output_channel})
    _notify('MuteChanged', room=room, muted=state)
```

---

## 8. TV Power Logging

**File: `src/control/av.py`**

```python
def BowlingAlleyTVPowerOn():
    ProgramLog('AV: BowlingAlley TV Power ON', 'warning')
    devices.dvBowlingAlleyDisplay.Set('Power', 'On')

def BowlingAlleyTVPowerOff():
    ProgramLog('AV: BowlingAlley TV Power OFF', 'warning')
    devices.dvBowlingAlleyDisplay.Set('Power', 'Off')

# Repeat for all TVs: GameLounge, ConferenceRoomA, ConferenceRoomB
```

---

## 9. LAN Device Connection Handlers

**File: `src/system.py`**

```python
# Connection event handlers for LAN devices
def _ssp200_connected(interface, state):
    ProgramLog(f'System: SSP 200 connection status: {state}', 'warning')

def _ssp200_disconnected(interface, state):
    ProgramLog(f'System: SSP 200 disconnected: {state}', 'error')

def _gamelounge_connected(interface, state):
    ProgramLog(f'System: Game Lounge Display connection status: {state}', 'warning')

def _gamelounge_disconnected(interface, state):
    ProgramLog(f'System: Game Lounge Display disconnected: {state}', 'error')

# Register connection event handlers (at module load time)
ProgramLog('System: Registering device connection handlers', 'warning')
devices.dvSSP200.Connected = _ssp200_connected
devices.dvSSP200.Disconnected = _ssp200_disconnected
devices.dvGameLoungeDisplay.Connected = _gamelounge_connected
devices.dvGameLoungeDisplay.Disconnected = _gamelounge_disconnected
# ... repeat for all LAN devices
ProgramLog('System: Device connection handlers registered', 'warning')
```

---

## 10. Source Routing Logging

**File: `src/control/av.py`**

```python
def _route_source(room, source):
    ProgramLog(f'AV: _route_source called - room={room}, source={source}', 'warning')
    out = _dsp_output(room)
    if not out:
        ProgramLog(f'AV: Warning - No DSP output defined for {room}', 'warning')
        return
    output_type, output_channel = out
    ProgramLog(f'AV: Output for {room}: type={output_type}, channel={output_channel}', 'warning')
    # mute all first
    mus_type, mus_ch = _music_input()
    ProgramLog(f'AV: Muting music input ({mus_type} {mus_ch})', 'warning')
    _set_mix_mute(mus_type, mus_ch, output_type, output_channel, 'On')
    bt_list = _bt_inputs(room)
    if bt_list:
        ProgramLog(f'AV: Muting BT inputs for {room}: {bt_list}', 'warning')
        for ch in bt_list:
            _set_mix_mute('VirtualReturn', ch, output_type, output_channel, 'On')
    if source == 'Music':
        ProgramLog(f'AV: Unmuting music input ({mus_type} {mus_ch})', 'warning')
        _set_mix_mute(mus_type, mus_ch, output_type, output_channel, 'Off')
    elif source == 'BT' and bt_list:
        ProgramLog(f'AV: Unmuting BT inputs for {room}: {bt_list}', 'warning')
        for ch in bt_list:
            _set_mix_mute('VirtualReturn', ch, output_type, output_channel, 'Off')
    CurrentAudioSource[room] = source
    ProgramLog(f'AV: Source routing complete for {room} -> {source}', 'warning')
    _notify('SourceChanged', room=room, source=source)
```

---

## Complete Logging Coverage

✅ System initialization steps  
✅ DSP connection status changes  
✅ Volume feedback initialization  
✅ LAN device connections/disconnections  
✅ Volume/mute operations with dB conversions  
✅ Source routing with mixpoint operations  
✅ DSP feedback with slider updates  
✅ TV power commands  
✅ Slider registrations  

---

## Files Modified Summary

1. **`src/devices.py`**: Added ConnectionHandler wrapper for DSP
2. **`src/system.py`**: Added ProgramLog import, DSP connection handler, LAN device connection handlers, comprehensive logging
3. **`src/control/av.py`**: Added ProgramLog import, comprehensive logging to all functions, DSP feedback handlers with slider.Level updates
4. **`src/ui/*_tlp.py`**: Added slider registration calls

---

## Expected Log Output

When system starts:
```
System: Imports completed
AV: Subscribing to DSP output attenuation feedback
AV: Subscribed to OutputAttenuation for output 5 (ArtStudio)
System: Subscribing to DSP connection status
System: Connecting to DSP
AV: Registering volume slider for ArtStudio
System: DSP connection status changed - ConnectionStatus: Connected
System: DSP connected, initializing volume feedback
AV: DSP output attenuation feedback - command=OutputAttenuation, value=-20.0dB, qualifier={'Output': '5'}
AV: Converted -20.0dB to UI level 75 for output 5
AV: Updating ArtStudio volume to 75
AV: Setting slider for ArtStudio to 75
```

When user adjusts volume:
```
AV: SetVolume called - room=ArtStudio, level=60
AV: Converted UI level 60 to DSP value -32dB
AV: Setting OutputAttenuation for channel 5 to -32dB
AV: DSP output attenuation feedback - command=OutputAttenuation, value=-32.0dB, qualifier={'Output': '5'}
AV: Converted -32.0dB to UI level 60 for output 5
AV: Updating ArtStudio volume to 60
AV: Setting slider for ArtStudio to 60
```
