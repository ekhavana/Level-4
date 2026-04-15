# Volume Feedback Protocol - Inter-Processor Communication

This document describes the bi-directional feedback protocol for volume and mute updates between Level 1 (Main) processor and remote processors (Level 3 Processor 1, Level 3 Processor 2, Level 4 Processor).

## Overview

**Problem**: Level 1 touchpanel controls zones on remote processors, but sliders don't update when volume changes from DSP or other sources.

**Solution**: Remote processors send feedback messages back to Level 1 when volume/mute changes occur.

---

## Protocol Specification

### Message Format
All messages use JSON over TCP connection (port 10000):

```json
{
  "command": "CommandName",
  "data": {
    "zone": "Zone Name",
    "level": 75,
    "state": "On"
  }
}
```

### Feedback Commands

#### 1. VolumeFeedback
Sent when volume changes on remote processor.

```json
{
  "command": "VolumeFeedback",
  "data": {
    "zone": "Art Studio",
    "level": 75
  }
}
```

**Parameters:**
- `zone` (string): Exact zone name (must match ZONE_PROCESSOR_MAP)
- `level` (int): Volume level 0-100

#### 2. MuteFeedback
Sent when mute state changes on remote processor.

```json
{
  "command": "MuteFeedback",
  "data": {
    "zone": "Art Studio",
    "state": "On"
  }
}
```

**Parameters:**
- `zone` (string): Exact zone name
- `state` (string): "On" (muted) or "Off" (unmuted)

---

## Implementation on Remote Processors

### Step 1: Add DSP Feedback Handlers

In remote processor's `control/av.py`, add DSP feedback handlers that send updates to Level 1:

```python
from extronlib.system import ProgramLog
import devices
import json

# Reference to Level 1 processor client
_Level1Client = devices.dvRemoteLevel1  # EthernetClientInterface to 172.22.10.100:10000

def _SendFeedbackToLevel1(command, zone, **kwargs):
    """Send feedback message to Level 1 processor"""
    try:
        data = {'zone': zone}
        data.update(kwargs)
        message = json.dumps({'command': command, 'data': data}) + '\n'
        _Level1Client.Send(message)
        ProgramLog(f'AV: Sent {command} to Level1 - zone={zone}, data={kwargs}', 'warning')
    except Exception as e:
        ProgramLog(f'AV: Error sending feedback to Level1 - {e}', 'error')

def _dsp_output_attenuation_feedback(command, value, qualifier):
    """Handle DSP output attenuation feedback"""
    ProgramLog(f'AV: DSP feedback - command={command}, value={value}dB, qualifier={qualifier}', 'warning')
    try:
        output = qualifier.get('Output')
        # Convert DSP value (-80 to 0 dB) to UI range (0-100)
        ui_level = int((value + 80) / 80.0 * 100)
        ui_level = max(0, min(100, ui_level))
        
        # Map output to zone name
        zone_mapping = {
            '5': 'Art Studio',
            '8': 'Game Lounge',
            # Add all your output-to-zone mappings
        }
        
        zone = zone_mapping.get(output)
        if zone:
            ProgramLog(f'AV: Updating {zone} volume to {ui_level}', 'warning')
            
            # Update local slider if registered
            slider = _VolumeSliders.get(zone)
            if slider:
                slider.SetFill(ui_level)
            
            # Send feedback to Level 1
            _SendFeedbackToLevel1('VolumeFeedback', zone, level=ui_level)
            
    except Exception as e:
        ProgramLog(f'AV: DSP feedback error - {e}', 'error')

# Subscribe to DSP outputs at module load time
ProgramLog('AV: Subscribing to DSP output attenuation feedback', 'warning')
devices.dvDSPLevel3.SubscribeStatus('OutputAttenuation', {'Output': '5'}, _dsp_output_attenuation_feedback)
devices.dvDSPLevel3.SubscribeStatus('OutputAttenuation', {'Output': '8'}, _dsp_output_attenuation_feedback)
# Add subscriptions for all outputs
```

### Step 2: Add Mute Feedback Handler

```python
def _dsp_output_mute_feedback(command, value, qualifier):
    """Handle DSP output mute feedback"""
    ProgramLog(f'AV: DSP mute feedback - command={command}, value={value}, qualifier={qualifier}', 'warning')
    try:
        output = qualifier.get('Output')
        
        # Map output to zone name (same mapping as volume)
        zone_mapping = {
            '5': 'Art Studio',
            '8': 'Game Lounge',
        }
        
        zone = zone_mapping.get(output)
        if zone:
            ProgramLog(f'AV: Updating {zone} mute to {value}', 'warning')
            
            # Update local mute button if registered
            button = _MuteButtons.get(zone)
            if button:
                button.SetState(1 if value == 'On' else 0)
            
            # Send feedback to Level 1
            _SendFeedbackToLevel1('MuteFeedback', zone, state=value)
            
    except Exception as e:
        ProgramLog(f'AV: DSP mute feedback error - {e}', 'error')

# Subscribe to mute status
devices.dvDSPLevel3.SubscribeStatus('OutputMute', {'Output': '5'}, _dsp_output_mute_feedback)
devices.dvDSPLevel3.SubscribeStatus('OutputMute', {'Output': '8'}, _dsp_output_mute_feedback)
```

### Step 3: Add Level 1 Client Connection

In remote processor's `devices.py`:

```python
from modules.helper.ConnectionHandler import GetConnectionHandler
from extronlib.interface import EthernetClientInterface

# Keep-alive function for raw TCP connections
def _remote_processor_keepalive(handler):
    try:
        handler.Send('\n')
    except:
        pass

# Create connection to Level 1 processor
rawRemoteLevel1 = EthernetClientInterface('172.22.10.100', 10000, 
                                          Credentials=('admin', 'extron'), 
                                          Protocol='TCP')

# Wrap with ConnectionHandler for automatic reconnection
dvRemoteLevel1 = GetConnectionHandler(rawRemoteLevel1, _remote_processor_keepalive, pollFrequency=10)
```

### Step 4: Connect to Level 1

In remote processor's `system.py`:

```python
def Initialize():
    # Connect to DSP
    devices.dvDSPLevel3.Connect()
    
    # Connect to Level 1 processor for feedback
    ProgramLog('System: Connecting to Level 1 processor', 'warning')
    devices.dvRemoteLevel1.Connect()
    
    # ... rest of initialization
```

---

## Zone Name Mappings

**CRITICAL**: Zone names must match exactly between processors.

### Level 3 Processor 1 Zones
- Art Studio
- Bowling Alley
- Conference Room A
- Conference Room B
- Coworking
- Game Lounge
- Level 3 Relaxation
- Level 3 Garden
- Level 3 Reading
- Art Room

### Level 3 Processor 2 Zones
- Karaoke A
- Karaoke B
- Management Office
- Screening Room
- Speakeasy
- VR Sports
- Level 3 Corridor

### Level 4 Processor Zones
- Party Room
- Terrace Gallery
- Yoga Studio
- Level 4 Gym
- Level 4 Courtyard

---

## Testing the Protocol

### Expected Log Output on Remote Processor

When DSP volume changes:
```
AV: DSP feedback - command=OutputAttenuation, value=-20.0dB, qualifier={'Output': '5'}
AV: Updating Art Studio volume to 75
AV: Sent VolumeFeedback to Level1 - zone=Art Studio, data={'level': 75}
```

### Expected Log Output on Level 1 Processor

When feedback is received:
```
System: Received volume feedback - zone=Art Studio, level=75
AV: UpdateRemoteVolumeSlider - zone=Art Studio, level=75
AV: Setting slider for Art Studio to 75
```

---

## Troubleshooting

### Sliders Don't Update

1. **Check Level 1 logs** for "Received volume feedback" messages
   - If missing: Remote processor not sending feedback
   - Check remote processor connection to Level 1

2. **Check remote processor logs** for "Sent VolumeFeedback" messages
   - If missing: DSP feedback not triggering
   - Verify DSP subscriptions are registered
   - Check DSP connection status

3. **Verify zone names match exactly**
   - Case-sensitive
   - Check ZONE_PROCESSOR_MAP on Level 1
   - Check zone_mapping on remote processors

4. **Check slider registration**
   - Level 1 logs should show "Slider registered for [zone]"
   - Verify RegisterVolumeSlider() calls in tlp.py

### Connection Issues

1. **Verify IP addresses**
   - Level 1: 172.22.10.100
   - Level 3 Processor 1: 172.22.10.101
   - Level 3 Processor 2: 172.22.10.102
   - Level 4 Processor: 172.22.10.103

2. **Check ConnectionHandler logs**
   - Should see "Connected" messages
   - If "Disconnected", check network and credentials

---

## Summary of Changes

### Level 1 Processor (Already Implemented ✅)

**`src/system.py`:**
- Added `VolumeFeedback` and `MuteFeedback` handlers in `_DispatchRemoteCommand()`

**`src/control/av.py`:**
- Added `_MuteButtons` registry
- Added `RegisterMuteButton()` function
- Added `UpdateRemoteVolumeSlider()` function
- Added `UpdateRemoteMuteButton()` function

**`src/ui/tlp.py`:**
- Added `RegisterVolumeSlider()` calls for all zones

### Remote Processors (To Be Implemented)

**`src/devices.py`:**
- Add EthernetClientInterface to Level 1 (172.22.10.100:10000)
- Wrap with ConnectionHandler

**`src/system.py`:**
- Connect to Level 1 processor in Initialize()

**`src/control/av.py`:**
- Add `_SendFeedbackToLevel1()` function
- Add DSP feedback handlers that call `_SendFeedbackToLevel1()`
- Subscribe to DSP OutputAttenuation and OutputMute

---

## Next Steps

1. **Implement on Level 3 Processor 1** (controls most zones)
2. **Test with one zone** (e.g., Art Studio)
3. **Verify feedback works** both directions
4. **Implement on Level 3 Processor 2**
5. **Implement on Level 4 Processor**
6. **Add mute button registrations** on Level 1 if needed

---

## Network Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Level 1 Processor                        │
│                   (172.22.10.100:10000)                     │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │   system.py  │────────▶│    av.py     │                 │
│  │              │         │              │                 │
│  │ Receives:    │         │ Updates:     │                 │
│  │ - Volume     │         │ - Sliders    │                 │
│  │ - Mute       │         │ - Buttons    │                 │
│  └──────────────┘         └──────────────┘                 │
│         ▲                                                   │
└─────────┼───────────────────────────────────────────────────┘
          │
          │ TCP JSON Messages
          │ VolumeFeedback / MuteFeedback
          │
    ┌─────┴─────┬──────────────┬──────────────┐
    │           │              │              │
    ▼           ▼              ▼              ▼
┌───────┐  ┌───────┐      ┌───────┐      ┌───────┐
│ L3P1  │  │ L3P2  │      │ L4P   │      │ Roof  │
│ .101  │  │ .102  │      │ .103  │      │ .104  │
└───┬───┘  └───┬───┘      └───┬───┘      └───┬───┘
    │          │              │              │
    ▼          ▼              ▼              ▼
┌───────┐  ┌───────┐      ┌───────┐      ┌───────┐
│  DSP  │  │  DSP  │      │  DSP  │      │  DSP  │
│Feedback│ │Feedback│     │Feedback│     │Feedback│
└───────┘  └───────┘      └───────┘      └───────┘
```

---

**Document Version**: 1.0  
**Date**: April 10, 2026  
**Author**: System Implementation  
**Status**: Level 1 Complete, Remote Processors Pending
