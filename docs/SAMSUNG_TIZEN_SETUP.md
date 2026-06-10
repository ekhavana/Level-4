# Samsung Tizen TV WebSocket Control Setup

## Overview
This workspace uses native Samsung Tizen WebSocket API (port 8001) for controlling Frame/LST series displays instead of Ex-Link/RS-232.

## Module Location
```
src/modules/device/smsg_display_Tizen_WebSocket_v1_0_0_0.py
```

## Device Configuration (devices.py)

### Required Imports
```python
from modules.device import smsg_display_Tizen_WebSocket_v1_0_0_0 as SamsungTizenWS
```

### Device Definition
```python
dvTerraceGallery1 = SamsungTizenWS.EthernetClass(
    Hostname='172.22.10.54',  # TV IP address
    IPPort=8001,               # 8001 for ws (plaintext), 8002 for wss (TLS)
    Protocol='TCP',            # Use 'TCP' - TLS is auto-applied if available
    MACAddress='B0:F2:F6:8B:34:05',  # Required for Wake-on-LAN power on
    Name='ExtronControl'       # Name shown on TV during pairing
)
```

### Key Parameters
- **Hostname**: TV's IP address on the network
- **IPPort**: 8001 for plaintext WebSocket, 8002 for TLS (not recommended due to SSLWrap issues)
- **MACAddress**: Required for Wake-on-LAN functionality (power on when TV is off)
- **Name**: The client name displayed on the TV pairing prompt

## How It Works

### Connection Flow
1. Module establishes TCP connection to TV on port 8001
2. Performs WebSocket RFC 6455 handshake
3. TV responds with either:
   - `ms.channel.connect` - Connection accepted (with token if pairing successful)
   - `ms.channel.unauthorized` - Connection rejected, pairing required

### Token-Based Pairing
- Tokens are stored in: `tizen_token_<IP>.txt` files
- First connection without token triggers pairing prompt on TV
- User must approve "Allow this device" on TV screen
- Token is saved and reused for subsequent connections
- If unauthorized, token is automatically cleared to force re-pairing

### Power Control
- **Power On**: Sends Wake-on-LAN magic packet (requires MACAddress)
- **Power Off**: Sends `KEY_POWER` via WebSocket
- **Input Selection**: Sends corresponding Tizen key codes (KEY_HDMI1, KEY_HDMI2, etc.)

## TV-Side Configuration Required

### Settings to Enable
1. **Settings** → **General** → **External Device Manager** → **Device Connect Manager**
   - Set to **"Allow"** (not "Ask" or "Deny")

2. **Settings** → **General** → **Smart Features**
   - **Allow Remote Control from Mobile Devices** → **On**

3. **Settings** → **Network** → **Expert Settings**
   - **Remote Control** → **On**

### If Pairing Prompt Doesn't Appear
1. **Use Samsung SmartThings mobile app**:
   - Add TV to SmartThings
   - Go to TV settings in app
   - Look for "ExtronControl" in device list and approve

2. **Power cycle the TV**:
   - Unplug TV for 30 seconds
   - Plug back in and try connection again

3. **Manual token entry** (advanced):
   - Obtain token via SmartThings CLI or network debugging
   - Create `tizen_token_<IP>.txt` file with token value

## Integration with ConnectionHandler (Optional)

Unlike other devices, the Tizen module manages its own reconnection. If you want ConnectionHandler wrapping:

```python
dvTerraceGallery1 = GetConnectionHandler(
    SamsungTizenWS.EthernetClass(
        Hostname='172.22.10.54',
        IPPort=8001,
        Protocol='TCP',
        MACAddress='B0:F2:F6:8B:34:05',
        Name='ExtronControl'
    ),
    DisconnectLimit=30
)
```

**Note**: The module has built-in auto-reconnect (5 second delay), so ConnectionHandler is optional.

## Troubleshooting

### "unauthorized" message in logs
- TV is rejecting the connection
- Check TV settings above
- Try SmartThings app approval method
- Clear token file to force fresh pairing

### "No route to host" for .56 TV
- TV is offline or on different network
- Check network connectivity
- Verify IP address

### Wake-on-LAN not working
- Verify MACAddress is correct in configuration
- Check TV supports WOL (usually requires TV to be in standby, not fully off)
- Some TVs require "Wake on WLAN" enabled in network settings

### Module logs to watch for
```
Tizen WS [IP]: Connect() called, current wsState: closed
Tizen WS [IP]: attempting TCP connection to IP:8001 (without token (fresh pairing))...
Tizen WS [IP]: TCP connect immediate result: Connected
Tizen WS [IP]: WebSocket open, remote control ready.
Tizen WS [IP]: unauthorized - approve the prompt on the TV (Allow this device).
```

## Files to Copy to Other Workspaces

1. `src/modules/device/smsg_display_Tizen_WebSocket_v1_0_0_0.py` - The module itself
2. Update `src/devices.py` with device definitions
3. Update `src/ui/devices.py` if UI references exist

## Model Reference

This setup has been tested with:
- **Model**: QN65LST7DAFXZA (65" The Terrace Outdoor TV)
- **Port**: 8001 (plaintext WebSocket)
- **Protocol**: TCP with auto-reconnect

For Frame TVs (indoor), same configuration applies but may use different model numbers (e.g., QN43LS03DAFXZA).

## Important Notes

1. **No SSL/TLS**: Port 8002 with SSLWrap has issues on extronlib - use port 8001
2. **Token persistence**: Tokens survive reboots, stored in text files
3. **Auto-reconnect**: Built-in 5-second reconnect on disconnect
4. **MAC required for WOL**: Without MACAddress, Power On won't work
5. **First pairing**: Must be done with TV on and user approval
