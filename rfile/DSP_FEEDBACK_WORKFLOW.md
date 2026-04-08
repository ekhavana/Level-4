---
description: Implement DSP volume feedback with slider updates and comprehensive logging
---

# DSP Volume Feedback Implementation Workflow

This workflow implements DSP volume feedback so UI sliders automatically update when volume changes from the DSP or other sources.

## Prerequisites
- DSP device module installed in `src/modules/device/`
- ConnectionHandler.py module in `src/modules/helper/`
- UI files with volume sliders defined

---

## Step 1: Update devices.py - Wrap DSP with ConnectionHandler

**File: `src/devices.py`**

Add imports and wrap DSP device:

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

**Note:** 
- `'PartNumber'` = name of Update function (without "Update" prefix) for keep-alive
- `pollFrequency=3` = poll every 3 seconds

---

## Step 2: Update system.py - Add DSP Connection Handler

**File: `src/system.py`**

Add ProgramLog import and DSP connection handler:

```python
from extronlib.system import Wait, ProgramLog
import devices

# DSP Connection Handler - triggers when DSP connects
def _dsp_connection_handler(command, value, qualifier):
    ProgramLog(f'System: DSP connection status changed - {command}: {value}', 'warning')
    if command == 'ConnectionStatus' and value == 'Connected':
        ProgramLog('System: DSP connected, initializing volume feedback', 'warning')
        # Request initial volume levels for all outputs to trigger feedback
        devices.dvDSPLevel3.Update('OutputAttenuation', {'Output': '5'})  # Example: ArtStudio
        devices.dvDSPLevel3.Update('OutputAttenuation', {'Output': '8'})  # Example: GameLounge
        devices.dvDSPLevel3.Update('ExpansionOutputAttenuation', {'Output': '1'})  # Example: BowlingAlley
        ProgramLog('System: Volume feedback initialization complete', 'warning')

# Subscribe to connection status BEFORE connecting
ProgramLog('System: Subscribing to DSP connection status', 'warning')
devices.dvDSPLevel3.SubscribeStatus('ConnectionStatus', None, _dsp_connection_handler)

# Connect DSP
ProgramLog('System: Connecting to DSP', 'warning')
devices.dvDSPLevel3.Connect()
```

**Customize:** Update the output channels to match your DSP configuration.

---

## Step 3: Update av.py - Add Slider Registry and Feedback Handlers

**File: `src/control/av.py`**

### 3a. Add ProgramLog import at top:

```python
from extronlib.system import Wait, ProgramLog
```

### 3b. Add slider registry (after state variables):

```python
# Slider references for feedback
_VolumeSliders = {}

def RegisterVolumeSlider(room, slider):
    """Register a slider to receive volume feedback for a room"""
    ProgramLog(f'AV: Registering volume slider for {room}', 'warning')
    _VolumeSliders[room] = slider
    ProgramLog(f'AV: Slider registered for {room}, total sliders: {len(_VolumeSliders)}', 'warning')
```

### 3c. Add DSP feedback handlers (at module level, before function definitions):

```python
# DSP Feedback Handlers
def _dsp_output_attenuation_feedback(command, value, qualifier):
    """Handle DSP output attenuation feedback and update sliders"""
    ProgramLog(f'AV: DSP output attenuation feedback - command={command}, value={value}dB, qualifier={qualifier}', 'warning')
    try:
        output = qualifier.get('Output')
        # Convert DSP value (-80 to 0 dB) to UI range (0-100)
        ui_level = int((value + 80) / 80.0 * 100)
        ui_level = max(0, min(100, ui_level))
        ProgramLog(f'AV: Converted {value}dB to UI level {ui_level} for output {output}', 'warning')
        
        # Find which room uses this output - CUSTOMIZE THIS MAPPING
        for room, out in [('ArtStudio', ('DMP', '5')), ('GameLounge', ('DMP', '8'))]:
            if out[1] == output:
                ProgramLog(f'AV: Updating {room} volume to {ui_level}', 'warning')
                VolumeLevel[room] = ui_level
                slider = _VolumeSliders.get(room)
                if slider:
                    ProgramLog(f'AV: Setting slider for {room} to {ui_level}', 'warning')
                    slider.SetFill(ui_level)  # CRITICAL: Use SetFill() method
                else:
                    ProgramLog(f'AV: Warning - No slider registered for {room}', 'warning')
                break
    except Exception as e:
        ProgramLog(f'AV: DSP feedback error - {e}', 'error')

def _dsp_expansion_output_attenuation_feedback(command, value, qualifier):
    """Handle DSP expansion output attenuation feedback and update sliders"""
    ProgramLog(f'AV: DSP expansion output attenuation feedback - command={command}, value={value}dB, qualifier={qualifier}', 'warning')
    try:
        output = qualifier.get('Output')
        ui_level = int((value + 80) / 80.0 * 100)
        ui_level = max(0, min(100, ui_level))
        ProgramLog(f'AV: Converted {value}dB to UI level {ui_level} for expansion output {output}', 'warning')
        
        # Find which room uses this expansion output - CUSTOMIZE THIS MAPPING
        for room, out in [('BowlingAlley', ('AXI', 'Exp. 1'))]:
            if out[0] == 'AXI' and out[1].split(' ')[1] == output:
                ProgramLog(f'AV: Updating {room} volume to {ui_level}', 'warning')
                VolumeLevel[room] = ui_level
                slider = _VolumeSliders.get(room)
                if slider:
                    ProgramLog(f'AV: Setting slider for {room} to {ui_level}', 'warning')
                    slider.SetFill(ui_level)  # CRITICAL: Use SetFill() method
                else:
                    ProgramLog(f'AV: Warning - No slider registered for {room}', 'warning')
                break
    except Exception as e:
        ProgramLog(f'AV: DSP expansion feedback error - {e}', 'error')

# Subscribe to DSP output changes at MODULE LOAD TIME
ProgramLog('AV: Subscribing to DSP output attenuation feedback', 'warning')
devices.dvDSPLevel3.SubscribeStatus('OutputAttenuation', {'Output': '5'}, _dsp_output_attenuation_feedback)
ProgramLog('AV: Subscribed to OutputAttenuation for output 5 (ArtStudio)', 'warning')
devices.dvDSPLevel3.SubscribeStatus('OutputAttenuation', {'Output': '8'}, _dsp_output_attenuation_feedback)
ProgramLog('AV: Subscribed to OutputAttenuation for output 8 (GameLounge)', 'warning')
devices.dvDSPLevel3.SubscribeStatus('ExpansionOutputAttenuation', {'Output': '1'}, _dsp_expansion_output_attenuation_feedback)
ProgramLog('AV: Subscribed to ExpansionOutputAttenuation for output 1 (BowlingAlley)', 'warning')
ProgramLog('AV: All DSP subscriptions registered', 'warning')
```

**Customize:** Update room-to-output mappings and subscription channels to match your configuration.

---

## Step 4: Update UI files - Register Sliders

**Files: `src/ui/*_tlp.py`** (for each room with a volume slider)

Add slider registration at module load time:

```python
import control.av as av

# After slider is defined (e.g., ArtStudioVolumeLvl = Slider(...))
av.RegisterVolumeSlider('ArtStudio', ArtStudioVolumeLvl)
```

**Repeat for each room** that has a volume slider.

---

## Step 5: Add Comprehensive Logging to Volume/Mute Functions

**File: `src/control/av.py`**

Update SetVolume and SetMute functions with logging:

```python
def SetVolume(room, level):
    level = max(0, min(100, int(level)))
    ProgramLog(f'AV: SetVolume called - room={room}, level={level}', 'warning')
    VolumeLevel[room] = level
    # ... existing volume setting code ...
    if output_type == 'AXI':
        channel_num = output_channel.split(' ')[1]
        ProgramLog(f'AV: Setting ExpansionOutputAttenuation for channel {channel_num} to {dsp}dB', 'warning')
        devices.dvDSPLevel3.Set('ExpansionOutputAttenuation', dsp, {'Output': channel_num})
    else:
        ProgramLog(f'AV: Setting OutputAttenuation for channel {output_channel} to {dsp}dB', 'warning')
        devices.dvDSPLevel3.Set('OutputAttenuation', dsp, {'Output': output_channel})

def SetMute(room, state):
    ProgramLog(f'AV: SetMute called - room={room}, state={state}', 'warning')
    # ... existing mute code with logging ...
```

---

## Step 6: Add LAN Device Connection Logging (Optional)

**File: `src/system.py`**

Add connection handlers for network devices:

```python
def _device_connected(interface, state):
    ProgramLog(f'System: Device connection status: {state}', 'warning')

def _device_disconnected(interface, state):
    ProgramLog(f'System: Device disconnected: {state}', 'error')

# Register handlers
devices.dvSSP200.Connected = _device_connected
devices.dvSSP200.Disconnected = _device_disconnected
# Repeat for all LAN devices
```

---

## CRITICAL NOTES

### ⚠️ Slider Update Method
**ONLY `slider.SetFill(ui_level)` works for Extron sliders!**

DO NOT USE:
- ❌ `slider.SetLevel(ui_level)` - doesn't exist
- ❌ `slider.SetValue(ui_level)` - doesn't exist
- ❌ `slider.Level = ui_level` - doesn't work

### ⚠️ Logging
Always use `ProgramLog()` instead of `print()` in Extron systems:
```python
ProgramLog(f'Message here', 'warning')  # Info/debug
ProgramLog(f'Error here', 'error')      # Errors
```

### ⚠️ Subscription Timing
- Subscribe to DSP outputs at **module load time** (not in Initialize())
- Subscribe to ConnectionStatus **before** calling Connect()

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

---

## Files Modified Summary

1. **`src/devices.py`**: Add ConnectionHandler wrapper for DSP
2. **`src/system.py`**: Add DSP connection handler, LAN device logging
3. **`src/control/av.py`**: Add feedback handlers, slider registry, comprehensive logging
4. **`src/ui/*_tlp.py`**: Add slider registration calls

---

## Troubleshooting

If sliders don't update:
1. Check logs for "AV: Registering volume slider" - sliders must be registered
2. Check logs for "System: DSP connected" - DSP must be connected
3. Check logs for "AV: DSP output attenuation feedback" - feedback must be received
4. Verify `slider.SetFill()` is used (not SetLevel or SetValue)
5. Verify room-to-output mappings match your DSP configuration
