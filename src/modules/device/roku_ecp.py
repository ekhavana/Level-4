"""
Roku ECP (External Control Protocol) Device Module

Provides control of Roku devices via HTTP on port 8060.
API Reference: https://developer.roku.com/docs/developer-program/dev-tools/external-control-api.md

Key commands:
- keypress/<key> - Press and release a key (POST)
- keydown/<key> - Press a key down (POST)
- keyup/<key> - Release a key (POST)
- launch/<appID> - Launch a channel/app (POST)
- query/device-info - Get device info (GET)
- query/active-app - Get current app (GET)

Key names: Home, Rev, Fwd, Play, Select, Left, Right, Up, Down, Back,
          InstantReplay, Info, Backspace, Search, Enter, VolumeDown, VolumeMute, VolumeUp
"""

from extronlib.interface import EthernetClientInterface
from extronlib.system import Wait


class RokuECPDevice:
    """Roku device controlled via External Control Protocol (ECP) over HTTP."""
    
    def __init__(self, ip_address, port=8060):
        self.ip = ip_address
        self.port = port
        self.base_url = f'http://{ip_address}:{port}'
        # Use EthernetClientInterface for HTTP communication
        # Roku ECP uses raw HTTP, we'll construct requests manually
        self._connected = False
        
    def _send_keypress(self, key):
        """Send a keypress command to Roku."""
        try:
            # Roku ECP expects: POST /keypress/<key> with empty body
            url = f'{self.base_url}/keypress/{key}'
            import urllib.request
            req = urllib.request.Request(url, data=b'', method='POST')
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception as e:
            print(f'Roku keypress error ({key}): {e}')
            return False
    
    def _send_launch(self, app_id):
        """Launch a channel/app by ID."""
        try:
            url = f'{self.base_url}/launch/{app_id}'
            import urllib.request
            req = urllib.request.Request(url, data=b'', method='POST')
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except Exception as e:
            print(f'Roku launch error ({app_id}): {e}')
            return False
    
    # Remote control key methods
    def Home(self):
        return self._send_keypress('Home')
    
    def Back(self):
        return self._send_keypress('Back')
    
    def Select(self):
        return self._send_keypress('Select')
    
    def Up(self):
        return self._send_keypress('Up')
    
    def Down(self):
        return self._send_keypress('Down')
    
    def Left(self):
        return self._send_keypress('Left')
    
    def Right(self):
        return self._send_keypress('Right')
    
    def Play(self):
        return self._send_keypress('Play')
    
    def Rev(self):
        return self._send_keypress('Rev')
    
    def Fwd(self):
        return self._send_keypress('Fwd')
    
    def InstantReplay(self):
        return self._send_keypress('InstantReplay')
    
    def Info(self):
        return self._send_keypress('Info')
    
    def Search(self):
        return self._send_keypress('Search')
    
    def Enter(self):
        return self._send_keypress('Enter')
    
    def Backspace(self):
        return self._send_keypress('Backspace')
    
    # Volume control (for Roku TVs)
    def VolumeUp(self):
        return self._send_keypress('VolumeUp')
    
    def VolumeDown(self):
        return self._send_keypress('VolumeDown')
    
    def VolumeMute(self):
        return self._send_keypress('VolumeMute')
    
    # Channel/App launching
    def LaunchChannel(self, app_id):
        """Launch a channel by its app ID."""
        return self._send_launch(app_id)
    
    def LaunchNetflix(self):
        """Launch Netflix (app ID 12)."""
        return self._send_launch('12')
    
    def LaunchHulu(self):
        """Launch Hulu (Roku app ID 2285 — constant across Roku devices)."""
        return self._send_launch('2285')
    
    def LaunchYouTube(self):
        """Launch YouTube (app ID 837)."""
        return self._send_launch('837')
    
    def LaunchRokuMediaPlayer(self):
        """Launch Roku Media Player (app ID 2213)."""
        return self._send_launch('2213')
    
    # Power control (for Roku TVs)
    def PowerOn(self):
        """Send PowerOn command (Roku TV only)."""
        return self._send_keypress('PowerOn')
    
    def PowerOff(self):
        """Send PowerOff command (Roku TV only)."""
        return self._send_keypress('PowerOff')


class EthernetClass(RokuECPDevice):
    """
    Ethernet class wrapper for Roku ECP device.
    This follows the pattern of other device modules in the system.
    """
    
    def __init__(self, Hostname, IPPort=8060, Protocol='TCP', ServicePort=0, Model=None):
        # Model parameter accepted for compatibility but not used
        super().__init__(Hostname, IPPort)
        self.DeviceAlias = f'Roku_{Hostname}'
        self.IPAddress = Hostname
        self.IPPort = IPPort
        
    def Connect(self):
        """Test connectivity to Roku device."""
        try:
            import urllib.request
            url = f'{self.base_url}/query/device-info'
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    self._connected = True
                    print(f'Roku connected: {self.ip}')
                    return True
        except Exception as e:
            print(f'Roku connection failed: {e}')
        return False
    
    def Disconnect(self):
        self._connected = False
        return True
    
    @property
    def Connected(self):
        return self._connected
