"""Samsung Tizen Smart TV control via the native WebSocket Remote Control API.

This module controls consumer Samsung Tizen TVs (e.g. The Frame QN..LS03 series)
over their built-in WebSocket remote control endpoint instead of the MDC/Ex-Link
serial protocol. It speaks RFC 6455 WebSocket framing on top of an extronlib
EthernetClientInterface so no external library is required.

Endpoints (set via the constructor):
    * ws  -> port 8001, Protocol='TCP'  (unencrypted, older firmware)
    * wss -> port 8002, Protocol='SSL'  (encrypted + token pairing, modern firmware)

Pairing:
    On the first wss connection the TV shows an "Allow/Deny" prompt. Once allowed
    it returns a token in the ``ms.channel.connect`` event. The token is cached
    (in memory and, if available, on disk) and reused on later connections so the
    prompt is not shown again.

Important limitations of the WebSocket API (by design, not a bug):
    * Power ON cannot be done with a remote key when the TV is fully off, because
      the WebSocket server is not running. Power ON is therefore performed with a
      Wake-on-LAN magic packet, which requires the TV's MAC address and the TV's
      "network standby"/"wake on" setting enabled. Provide ``MACAddress`` to the
      constructor to enable this.
    * KEY_POWER is a toggle; it is used for Power OFF while connected.
    * There is no universal discrete "select HDMI 3" key. ``KEY_HDMI`` jumps to /
      cycles HDMI sources; ``KEY_SOURCE`` opens the source list. Map as needed in
      ``_INPUT_KEY_MAP`` below.
    * The API does not expose absolute volume; audio for these displays is handled
      by the DSP in this system, so only Power/Input are wired by default.
"""

from extronlib.interface import EthernetClientInterface
from extronlib.system import Wait, ProgramLog, Timer
import json
import base64
import struct
import random

try:
    from extronlib.system import File
except Exception:
    File = None


def _rand_bytes(n):
    """Return n pseudo-random bytes (extronlib-safe, no os.urandom dependency)."""
    return bytes(random.getrandbits(8) for _ in range(n))


class DeviceClass:
    def __init__(self):
        self.Models = {}
        self.ConnectionType = 'Ethernet'

        # Status surface compatible with the other display modules in this project.
        self.Commands = {
            'ConnectionStatus': {'Status': {}},
            'Power': {'Status': {}},
            'Input': {'Status': {}},
        }
        self.Subscription = {}

        # WebSocket / connection state.
        self._wsState = 'closed'          # 'closed' | 'connecting' | 'handshaking' | 'open'
        self._rxBuffer = b''
        self._token = None
        self._clientName = 'ExtronControl'
        self._autoReconnect = True
        self._reconnectInterval = 5
        self._keepAliveInterval = 30
        self._pendingKeys = []            # keys queued while the socket is not open
        self._maxQueued = 16

        self._ReconnectTimer = Timer(self._reconnectInterval, self._ReconnectTick)
        self._ReconnectTimer.Stop()
        self._KeepAliveTimer = Timer(self._keepAliveInterval, self._KeepAliveTick)
        self._KeepAliveTimer.Stop()

        self._wol = None                  # lazily created UDP interface for Wake-on-LAN
        self.MACAddress = None

        # Map UI input names to Tizen remote keys. KEY_HDMI is best-effort; adjust
        # to KEY_SOURCE + navigation if discrete selection is required.
        self._INPUT_KEY_MAP = {
            'HDMI 1': 'KEY_HDMI',
            'HDMI 2': 'KEY_HDMI',
            'HDMI 3': 'KEY_HDMI',
            'HDMI 4': 'KEY_HDMI',
            'TV': 'KEY_TV',
            'Source': 'KEY_SOURCE',
        }

    # ------------------------------------------------------------------ #
    # Public control API (mirrors the other display modules)
    # ------------------------------------------------------------------ #
    def Set(self, command, value, qualifier=None):
        method = getattr(self, 'Set%s' % command, None)
        if method is not None and callable(method):
            method(value, qualifier)
        else:
            raise AttributeError(command + ' does not support Set.')

    def Update(self, command, qualifier=None):
        # The WebSocket remote API has no readable power/input state, so polling
        # is a no-op. Connection liveness is maintained by WebSocket ping frames.
        method = getattr(self, 'Update%s' % command, None)
        if method is not None and callable(method):
            method(None, qualifier)

    def SetPower(self, value, qualifier):
        if value == 'On':
            # The WebSocket server is unavailable while the TV is off, so wake it
            # with a Wake-on-LAN magic packet. KEY_POWER is NOT sent here because
            # it would toggle a TV that is already on back off.
            ProgramLog('Tizen WS [{}]: Power On requested (WOL will be sent).'.format(
                self._host()), 'warning')
            if self.MACAddress:
                self._send_wol()
            else:
                ProgramLog('Tizen WS [{}]: Power On requested but no MACAddress '
                           'configured for Wake-on-LAN.'.format(self._host()),
                           'warning')
            self.WriteStatus('Power', 'On', None)
        elif value == 'Off':
            ProgramLog('Tizen WS [{}]: Power Off requested (sending KEY_POWER).'
                       ' WebSocket state: {}'.format(self._host(), self._wsState),
                       'warning')
            self._send_key('KEY_POWER')
            self.WriteStatus('Power', 'Off', None)
        else:
            self.Discard('Invalid Command for SetPower')

    def UpdatePower(self, value, qualifier):
        pass

    def SetInput(self, value, qualifier):
        key = self._INPUT_KEY_MAP.get(value)
        if key:
            self._send_key(key)
            self.WriteStatus('Input', value, None)
        else:
            self.Discard('Invalid Command for SetInput: {}'.format(value))

    def SetVolume(self, value, qualifier):
        # Not supported as an absolute value over the remote API.
        self.Discard('SetVolume (absolute) is not supported via WebSocket')

    def SetKey(self, value, qualifier):
        """Send an arbitrary Tizen remote key, e.g. 'KEY_VOLUP', 'KEY_MUTE'."""
        self._send_key(value)

    # ------------------------------------------------------------------ #
    # Connection management
    # ------------------------------------------------------------------ #
    def _connect_wrapper(self, timeout=None):
        """Wrapper around base Connect that adds WebSocket handshake handling."""
        ProgramLog('Tizen WS [{}]: Connect() called, current wsState: {}'.format(
            self._host(), self._wsState), 'warning')
        if self._wsState in ('connecting', 'handshaking', 'open'):
            ProgramLog('Tizen WS [{}]: Connect() returning early, already in state: {}'.format(
                self._host(), self._wsState), 'warning')
            return
        self._wsState = 'connecting'
        self._rxBuffer = b''
        token_status = 'with token' if self._token else 'without token (fresh pairing)'
        ProgramLog('Tizen WS [{}]: attempting TCP connection to {}:{} ({})...'.format(
            self._host(), getattr(self, 'IPAddress', '?'), getattr(self, 'IPPort', 8001),
            token_status),
            'warning')

        # Capture the underlying interface events.
        self.Connected = self._OnEthernetConnected
        self.Disconnected = self._OnEthernetDisconnected
        self.ReceiveData = self._OnReceiveData

        try:
            result = EthernetClientInterface.Connect(self, timeout)
        except Exception as e:
            result = 'ConnectError: {}'.format(e)

        if result not in ('Connected', 'ConnectedAlready'):
            ProgramLog('Tizen WS [{}]: TCP connect FAILED: {}'.format(
                self._host(), result), 'warning')
            self._scheduleReconnect()
        else:
            ProgramLog('Tizen WS [{}]: TCP connect immediate result: {}'.format(
                self._host(), result), 'warning')

    def Disconnect(self):
        self._autoReconnect = False
        self._stopTimers()
        self._wsState = 'closed'
        try:
            EthernetClientInterface.Disconnect(self)
        except Exception:
            pass
        self.WriteStatus('ConnectionStatus', 'Disconnected', None)

    def _OnEthernetConnected(self, interface, state):
        # TCP/TLS is up; now perform the WebSocket upgrade handshake.
        self._wsState = 'handshaking'
        self._rxBuffer = b''
        ProgramLog('Tizen WS [{}]: TCP connected, starting WebSocket handshake.'.format(
            self._host()), 'warning')
        self._send_handshake()

    def _OnEthernetDisconnected(self, interface, state):
        ProgramLog('Tizen WS [{}]: TCP disconnected.'.format(self._host()), 'warning')
        self._wsState = 'closed'
        self._KeepAliveTimer.Stop()
        self.WriteStatus('ConnectionStatus', 'Disconnected', None)
        if self._autoReconnect:
            self._scheduleReconnect()

    def _scheduleReconnect(self):
        self._wsState = 'closed'
        if self._autoReconnect and self._ReconnectTimer.State != 'Running':
            self._ReconnectTimer.Restart()

    def _ReconnectTick(self, timer, count):
        if self._wsState == 'closed' and self._autoReconnect:
            self.Connect()
        else:
            timer.Stop()

    def _KeepAliveTick(self, timer, count):
        if self._wsState == 'open':
            self._ws_send(b'', opcode=0x9)   # WebSocket ping
        else:
            timer.Stop()

    def _stopTimers(self):
        self._ReconnectTimer.Stop()
        self._KeepAliveTimer.Stop()

    # ------------------------------------------------------------------ #
    # WebSocket handshake + framing
    # ------------------------------------------------------------------ #
    def _ws_path(self):
        name_b64 = base64.b64encode(self._clientName.encode('utf-8')).decode('ascii')
        path = '/api/v2/channels/samsung.remote.control?name={}'.format(name_b64)
        if self._token:
            path += '&token={}'.format(self._token)
        return path

    def _send_handshake(self):
        key = base64.b64encode(_rand_bytes(16)).decode('ascii')
        request = (
            'GET {path} HTTP/1.1\r\n'
            'Host: {host}:{port}\r\n'
            'Upgrade: websocket\r\n'
            'Connection: Upgrade\r\n'
            'Sec-WebSocket-Key: {key}\r\n'
            'Sec-WebSocket-Version: 13\r\n'
            '\r\n'
        ).format(path=self._ws_path(), host=self._host(),
                 port=self.IPPort, key=key)
        try:
            EthernetClientInterface.Send(self, request.encode('utf-8'))
        except Exception as e:
            ProgramLog('Tizen WS [{}]: handshake send error: {}'.format(
                self._host(), e), 'error')
            self._scheduleReconnect()

    def _OnReceiveData(self, interface, data):
        self._rxBuffer += data

        if self._wsState == 'handshaking':
            if b'\r\n\r\n' not in self._rxBuffer:
                return
            header, _, rest = self._rxBuffer.partition(b'\r\n\r\n')
            status_line = header.split(b'\r\n', 1)[0]
            if b'101' in status_line:
                self._wsState = 'open'
                self._rxBuffer = rest
                self._OnWsOpen()
            else:
                # Log full response headers for debugging
                headers = header.decode('latin-1', 'replace').replace('\r\n', ' | ')
                ProgramLog('Tizen WS [{}]: handshake rejected: {}'.format(
                    self._host(), status_line.decode('latin-1', 'replace')),
                    'warning')
                ProgramLog('Tizen WS [{}]: full response: {}'.format(
                    self._host(), headers[:500]), 'warning')  # truncate if very long
                self._rxBuffer = b''
                try:
                    EthernetClientInterface.Disconnect(self)
                except Exception:
                    pass
                self._scheduleReconnect()
                return

        if self._wsState == 'open':
            self._parse_frames()

    def _OnWsOpen(self):
        ProgramLog('Tizen WS [{}]: WebSocket open, remote control ready.'.format(
            self._host()), 'warning')
        self.WriteStatus('ConnectionStatus', 'Connected', None)
        if self._KeepAliveTimer.State != 'Running':
            self._KeepAliveTimer.Restart()
        # Flush any keys queued while the socket was down.
        queued, self._pendingKeys = self._pendingKeys, []
        for key in queued:
            self._send_key(key)

    def _parse_frames(self):
        buf = self._rxBuffer
        while True:
            if len(buf) < 2:
                break
            b0, b1 = buf[0], buf[1]
            opcode = b0 & 0x0F
            masked = b1 & 0x80
            length = b1 & 0x7F
            idx = 2
            if length == 126:
                if len(buf) < 4:
                    break
                length = struct.unpack('>H', buf[2:4])[0]
                idx = 4
            elif length == 127:
                if len(buf) < 10:
                    break
                length = struct.unpack('>Q', buf[2:10])[0]
                idx = 10
            mask = b''
            if masked:
                if len(buf) < idx + 4:
                    break
                mask = buf[idx:idx + 4]
                idx += 4
            if len(buf) < idx + length:
                break
            payload = buf[idx:idx + length]
            if masked:
                payload = bytes(payload[i] ^ mask[i % 4] for i in range(length))
            buf = buf[idx + length:]
            self._handle_frame(opcode, payload)
        self._rxBuffer = buf

    def _handle_frame(self, opcode, payload):
        if opcode == 0x8:                 # close
            try:
                EthernetClientInterface.Disconnect(self)
            except Exception:
                pass
            self._scheduleReconnect()
        elif opcode == 0x9:               # ping -> pong
            self._ws_send(payload, opcode=0xA)
        elif opcode == 0xA:               # pong
            pass
        elif opcode in (0x1, 0x2):        # text / binary
            self._handle_message(payload)

    def _handle_message(self, payload):
        try:
            msg = json.loads(payload.decode('utf-8'))
        except Exception:
            return
        event = msg.get('event')
        if event == 'ms.channel.connect':
            token = msg.get('data', {}).get('token')
            if token:
                self._token = str(token)
                self._save_token()
                ProgramLog('Tizen WS [{}]: paired, token stored.'.format(
                    self._host()), 'warning')
        elif event == 'ms.channel.unauthorized':
            ProgramLog('Tizen WS [{}]: unauthorized - approve the prompt on the '
                       'TV (Allow this device).'.format(self._host()), 'warning')
            # Log the full message to see what TV is telling us
            ProgramLog('Tizen WS [{}]: full unauthorized msg: {}'.format(
                self._host(), json.dumps(msg)), 'warning')
            # Clear any stale token to force fresh pairing on next connect
            if self._token:
                ProgramLog('Tizen WS [{}]: clearing stale token, will retry without '
                           'token to trigger prompt.'.format(self._host()), 'warning')
                self._token = None
                try:
                    # Delete the token file
                    import os
                    token_file = self._token_filename()
                    if os.path.exists(token_file):
                        os.remove(token_file)
                        ProgramLog('Tizen WS [{}]: deleted token file.'.format(
                            self._host()), 'warning')
                except Exception as e:
                    ProgramLog('Tizen WS [{}]: failed to delete token file: {}'.format(
                        self._host(), e), 'warning')

    # ------------------------------------------------------------------ #
    # Frame encoder + senders
    # ------------------------------------------------------------------ #
    def _ws_send(self, payload, opcode=0x1):
        if self._wsState != 'open':
            return False
        header = bytearray()
        header.append(0x80 | (opcode & 0x0F))
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header += struct.pack('>H', length)
        else:
            header.append(0x80 | 127)
            header += struct.pack('>Q', length)
        mask = _rand_bytes(4)
        header += mask
        masked = bytes(payload[i] ^ mask[i % 4] for i in range(length))
        try:
            EthernetClientInterface.Send(self, bytes(header) + masked)
            return True
        except Exception as e:
            ProgramLog('Tizen WS [{}]: send error: {}'.format(self._host(), e),
                       'error')
            return False

    def _send_key(self, key):
        if self._wsState != 'open':
            # Queue the key (bounded) and ensure we are trying to connect.
            if len(self._pendingKeys) < self._maxQueued:
                self._pendingKeys.append(key)
                ProgramLog('Tizen WS [{}]: key {} queued (wsState: {}, queue: {}/{}).'
                           .format(self._host(), key, self._wsState,
                                   len(self._pendingKeys), self._maxQueued),
                           'warning')
            if self._wsState == 'closed':
                ProgramLog('Tizen WS [{}]: auto-connecting to send queued key.'.format(
                    self._host()), 'warning')
                ProgramLog('Tizen WS [{}]: about to call Connect()...'.format(
                    self._host()), 'warning')
                try:
                    self.Connect()
                    ProgramLog('Tizen WS [{}]: Connect() returned.'.format(
                        self._host()), 'warning')
                except Exception as e:
                    ProgramLog('Tizen WS [{}]: Connect() raised exception: {}'.format(
                        self._host(), e), 'error')
            return
        # WebSocket is open, send the key immediately
        ProgramLog('Tizen WS [{}]: sending key {}.'.format(self._host(), key),
                   'warning')
        payload = json.dumps({
            'method': 'ms.remote.control',
            'params': {
                'Cmd': 'Click',
                'DataOfCmd': key,
                'Option': 'false',
                'TypeOfRemote': 'SendRemoteKey',
            },
        }).encode('utf-8')
        self._ws_send(payload, opcode=0x1)

    # ------------------------------------------------------------------ #
    # Wake-on-LAN (Power On)
    # ------------------------------------------------------------------ #
    def _send_wol(self):
        mac = ''.join(c for c in str(self.MACAddress) if c in '0123456789abcdefABCDEF')
        if len(mac) != 12:
            ProgramLog('Tizen WS [{}]: invalid MACAddress for WOL: {}'.format(
                self._host(), self.MACAddress), 'warning')
            return
        try:
            mac_bytes = bytes(bytearray.fromhex(mac))
        except Exception:
            ProgramLog('Tizen WS [{}]: could not parse MACAddress.'.format(
                self._host()), 'warning')
            return
        packet = b'\xff' * 6 + mac_bytes * 16
        try:
            if self._wol is None:
                # Directed Wake-on-LAN to the TV's IP on the discard/WOL port.
                # UDP is connectionless - no Connect() needed, just Send()
                self._wol = EthernetClientInterface(self.IPAddress, 9, 'UDP')
            self._wol.Send(packet)
            ProgramLog('Tizen WS [{}]: sent Wake-on-LAN magic packet.'.format(
                self._host()), 'warning')
        except Exception as e:
            ProgramLog('Tizen WS [{}]: WOL send error: {}'.format(
                self._host(), e), 'error')

    # ------------------------------------------------------------------ #
    # Token persistence
    # ------------------------------------------------------------------ #
    def _token_filename(self):
        return 'tizen_token_{}.txt'.format(str(self.IPAddress).replace('.', '_'))

    def _load_token(self):
        if File is None:
            return
        try:
            f = File(self._token_filename(), 'r')
            data = f.read()
            f.close()
            data = data.decode() if isinstance(data, (bytes, bytearray)) else data
            data = (data or '').strip()
            if data:
                self._token = data
        except Exception:
            pass

    def _save_token(self):
        if File is None or not self._token:
            return
        try:
            f = File(self._token_filename(), 'w')
            f.write(self._token)
            f.close()
        except Exception:
            pass

    def _host(self):
        return getattr(self, 'IPAddress', '?')

    # ------------------------------------------------------------------ #
    # Status helpers (subset of the standard module pattern)
    # ------------------------------------------------------------------ #
    def SubscribeStatus(self, command, qualifier, callback):
        Command = self.Commands.get(command, None)
        if Command:
            if command not in self.Subscription:
                self.Subscription[command] = {'method': {}}
            Method = self.Subscription[command]['method']
            Method['callback'] = callback
            Method['qualifier'] = qualifier
        else:
            raise KeyError('Invalid command for SubscribeStatus ' + command)

    def NewStatus(self, command, value, qualifier):
        if command in self.Subscription:
            Method = self.Subscription[command]['method']
            if 'callback' in Method and Method['callback']:
                Method['callback'](command, value, qualifier)

    def WriteStatus(self, command, value, qualifier=None):
        Command = self.Commands.get(command)
        if not Command:
            return
        Status = Command['Status']
        if Status.get('Live') != value:
            Status['Live'] = value
            self.NewStatus(command, value, qualifier)

    def ReadStatus(self, command, qualifier=None):
        Command = self.Commands.get(command, None)
        if Command:
            return Command['Status'].get('Live')
        raise KeyError('Invalid command for ReadStatus: ' + command)


class EthernetClass(EthernetClientInterface, DeviceClass):
    """Tizen WebSocket display interface.

    :param Hostname: TV IP address or hostname.
    :param IPPort: 8001 for ws (plaintext) or 8002 for wss (TLS, see Protocol).
    :param Protocol: 'TCP' for ws (port 8001). Pass 'SSL'/'TLS'/'wss' to request
                     a TLS-wrapped wss connection (port 8002) -- this is applied
                     via the interface's SSLWrap() method when the firmware
                     supports it, and falls back to plaintext with a log warning
                     otherwise. NOTE: extronlib's EthernetClientInterface itself
                     only accepts 'TCP'/'UDP'/'SSH', so 'SSL' is never passed to
                     the base class.
    :param Model: optional model string for parity with other modules.
    :param MACAddress: TV MAC (e.g. 'AA:BB:CC:DD:EE:FF') to enable Wake-on-LAN
                       power-on. Without it, Power On cannot wake a TV that is off.
    :param Name: friendly controller name presented to the TV during pairing.
    """

    def __init__(self, Hostname, IPPort=8001, Protocol='TCP', Model=None,
                 MACAddress=None, Name='ExtronControl'):
        secure = str(Protocol).upper() in ('SSL', 'TLS', 'WSS')
        # extronlib only accepts 'TCP'/'UDP'/'SSH' here; TLS is applied via
        # SSLWrap() below (never by passing 'SSL' to the base interface).
        EthernetClientInterface.__init__(self, Hostname, IPPort, 'TCP')
        DeviceClass.__init__(self)
        self.MACAddress = MACAddress
        self._clientName = Name or 'ExtronControl'
        self._useTLS = False
        if secure:
            self._enable_tls()
        self._load_token()
        if Model and len(self.Models) > 0:
            if Model not in self.Models:
                print('Model mismatch')
            else:
                self.Models[Model]()
        # Force our Connect wrapper to override base class method
        self.Connect = self._connect_wrapper

    def _enable_tls(self):
        """Best-effort TLS upgrade for wss, tolerant of firmware differences."""
        wrap = getattr(self, 'SSLWrap', None)
        if not callable(wrap):
            ProgramLog('Tizen WS [{}]: SSLWrap not available on this firmware; '
                       'using plaintext ws. Configure port 8001 / Protocol="TCP".'
                       .format(getattr(self, 'IPAddress', '?')), 'warning')
            return
        for kwargs in ({'cert_reqs': 'none'}, {}):
            try:
                wrap(**kwargs)
                self._useTLS = True
                ProgramLog('Tizen WS [{}]: TLS enabled (wss).'.format(
                    getattr(self, 'IPAddress', '?')), 'warning')
                return
            except TypeError:
                continue
            except Exception as e:
                ProgramLog('Tizen WS [{}]: SSLWrap failed ({}); using plaintext.'
                           .format(getattr(self, 'IPAddress', '?'), e), 'warning')
                return
        ProgramLog('Tizen WS [{}]: SSLWrap signature unsupported; using plaintext.'
                   .format(getattr(self, 'IPAddress', '?')), 'warning')

    def Error(self, message):
        portInfo = 'IP Address/Host: {0}:{1}'.format(self.IPAddress, self.IPPort)
        print('Module: {}'.format(__name__), portInfo,
              'Error Message: {}'.format(message[0]), sep='\r\n')

    def Discard(self, message):
        self.Error([message])
