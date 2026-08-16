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
            'AudioMute': {'Status': {}},
            'Volume': {'Status': {}},
        }
        self.Subscription = {}

        # WebSocket / connection state.
        self._wsState = 'closed'          # 'closed' | 'connecting' | 'handshaking' | 'open'
        self._rxBuffer = b''
        self._token = None
        self._clientName = 'ExtronControl'
        self._autoReconnect = True
        self._reconnectInterval = 5
        # Some Tizen models (e.g. "The Frame" QN43LS03) ignore WebSocket ping
        # frames for their idle timeout and drop remote-control sessions after
        # ~40s. Keep the interval short and send a real application-level
        # message (see _KeepAliveTick) so the TV's idle timer is reset.
        self._keepAliveInterval = 20
        self._pendingKeys = []            # keys queued while the socket is not open
        self._maxQueued = 16
        # Last power we commanded. KEY_POWER is a toggle — never send Off when
        # already Off (that would turn the TV back on) or On when already On.
        self._commandedPower = None
        # KEY_POWER is toggle-only and the WS API exposes no power feedback, so
        # when the socket first opens we must ASSUME a starting state. Models
        # that keep the socket up in standby/Art Mode (e.g. The Terrace LST)
        # can connect while actually off; assuming 'On' then locks On/Off into
        # anti-phase. Set AssumeStandbyOnConnect=True (via devices.py) for such
        # displays so we seed 'Off' instead. See _OnWsOpen.
        self._assumeStandbyOnConnect = False
        # KEY_MUTE is also a toggle — track commanded mute like Power.
        self._commandedMute = 'Off'
        # Relative volume only; remember last UI level we drove toward.
        self._commandedVolume = 20

        self._ReconnectTimer = Timer(self._reconnectInterval, self._ReconnectTick)
        self._safe_stop_timer(self._ReconnectTimer)
        self._KeepAliveTimer = Timer(self._keepAliveInterval, self._KeepAliveTick)
        self._safe_stop_timer(self._KeepAliveTimer)

        self._wol = None                  # lazily created UDP interface for Wake-on-LAN
        self.MACAddress = None

        # Modern Tizen (Frame LS03 etc.) ignores KEY_HDMI1..4. Use either a
        # SOURCE-menu key sequence (discrete) or KEY_HDMI (cycles connected HDMI).
        self._INPUT_KEY_MAP = {
            'HDMI 1': 'KEY_HDMI',
            'HDMI 2': 'KEY_HDMI',
            'HDMI 3': 'KEY_HDMI',
            'HDMI 4': 'KEY_HDMI',
            'TV': 'KEY_TV',
            'Source': 'KEY_SOURCE',
        }
        # Modern Tizen ignores KEY_HDMI1..4. Fixed Source-strip indexes also fail:
        # disconnected HDMI ports are hidden. KEY_HDMI cycles connected HDMI only.
        self._INPUT_KEY_MAP = {
            'HDMI 1': 'KEY_HDMI',
            'HDMI 2': 'KEY_HDMI',
            'HDMI 3': 'KEY_HDMI',
            'HDMI 4': 'KEY_HDMI',
            'TV': 'KEY_TV',
            'Source': 'KEY_SOURCE',
        }
        self._INPUT_KEY_SEQUENCES = {}
        self._inputKeyInterval = 0.45
        self._commandedInput = None
        self._inputSeqId = 0
        self._volumeScale = 100
        self._volumeFloorSteps = 100
        self._volumeKeyInterval = 0.05
        self._volumeTick = None
        self._volumeRampBusy = False
        self._pendingVolumeTick = None

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
        # is a no-op. Connection liveness is maintained by a periodic
        # application-level keep-alive message (see _KeepAliveTick).
        method = getattr(self, 'Update%s' % command, None)
        if method is not None and callable(method):
            method(None, qualifier)

    def SetPower(self, value, qualifier):
        """Discrete On/Off on top of Samsung's toggle-only KEY_POWER.

        On  → WOL (always, if MAC set). If WS is up and we last commanded Off,
              also send KEY_POWER once to wake Art Mode / network-standby.
        Off → send KEY_POWER only if we believe the TV is On. Skip if already Off
              so a second Off press does not toggle the TV back on.
        """
        if value == 'On':
            # Only skip when we already commanded On *and* the socket is live
            # (panel almost certainly displaying). Fully Off → WS closed → WOL.
            if self._commandedPower == 'On' and self._wsState == 'open':
                ProgramLog('Tizen WS [{}]: Power On — already On, skip toggle.'
                           .format(self._host()), 'warning')
                self.WriteStatus('Power', 'On', None)
                return
            ProgramLog('Tizen WS [{}]: Power On requested (WOL'
                       '{}); commanded was {}, wsState={}.'
                       .format(self._host(),
                               '' if self.MACAddress else ' skipped — no MAC',
                               self._commandedPower, self._wsState),
                       'warning')
            if self.MACAddress:
                self._send_wol()
            else:
                ProgramLog('Tizen WS [{}]: Power On — no MACAddress for WOL.'
                           .format(self._host()), 'warning')
            # Network standby / Art Mode: WS may stay up after Off — KEY_POWER wakes.
            if self._wsState == 'open' and self._commandedPower == 'Off':
                ProgramLog('Tizen WS [{}]: Power On — WS up after Off; sending '
                           'KEY_POWER once to wake.'.format(self._host()),
                           'warning')
                self._send_key('KEY_POWER')
            elif self._wsState != 'open':
                try:
                    Wait(1.5, self.Connect)
                except Exception:
                    pass
            self._commandedPower = 'On'
            self.WriteStatus('Power', 'On', None)
        elif value == 'Off':
            if self._commandedPower == 'Off':
                ProgramLog('Tizen WS [{}]: Power Off — already Off, skip '
                           'KEY_POWER (prevents toggle ON).'
                           .format(self._host()), 'warning')
                self.WriteStatus('Power', 'Off', None)
                return
            ProgramLog('Tizen WS [{}]: Power Off requested (KEY_POWER); '
                       'wsState={} commanded was {}.'.format(
                           self._host(), self._wsState, self._commandedPower),
                       'warning')
            self._send_key('KEY_POWER')
            self._commandedPower = 'Off'
            self.WriteStatus('Power', 'Off', None)
        else:
            self.Discard('Invalid Command for SetPower')

    def UpdatePower(self, value, qualifier):
        pass

    def NotePowerOn(self, reason='external'):
        """Public: ground the assumed power model to 'On' without sending a key.

        Selecting a source/input proves the TV is on, so callers (e.g. the Roku
        source-select in av.py) call this first. It prevents SetPower('On') from
        firing the toggle-only KEY_POWER "wake", which would turn an already-on
        TV OFF when the connect-time assumption was 'Off'. Same self-heal the
        driver already applies inside SetInput.
        """
        self._note_tv_on(reason)

    def WakeOnLan(self):
        """Public: send a Wake-on-LAN magic packet (harmless if already on).

        Lets a source-select wake a genuinely-off TV without relying on the
        KEY_POWER toggle, which is unsafe when we cannot read real power state.
        """
        if self.MACAddress:
            self._send_wol()
        else:
            ProgramLog('Tizen WS [{}]: WakeOnLan skipped — no MACAddress.'
                       .format(self._host()), 'warning')

    def _note_tv_on(self, reason):
        """Resync the assumed power model to 'On'.

        KEY_POWER is toggle-only with no state feedback, so the connect-time
        assumption can be wrong (see _OnWsOpen). Any command that only makes
        sense on a powered TV — e.g. selecting an input — is authoritative
        proof the TV is on, so we correct the model here. This self-heals the
        On/Off anti-phase without needing to guess the boot state.
        """
        if self._commandedPower != 'On':
            ProgramLog('Tizen WS [{}]: resync power=On ({}).'.format(
                self._host(), reason), 'warning')
        self._commandedPower = 'On'
        self.WriteStatus('Power', 'On', None)

    def SetInput(self, value, qualifier):
        # Selecting an input only makes sense on a powered TV — treat it as
        # ground truth and correct any wrong power assumption.
        self._note_tv_on('input {}'.format(value))
        if value in ('HDMI 1', 'HDMI 2', 'HDMI 3', 'HDMI 4'):
            self._select_hdmi(value)
            return
        seq = getattr(self, '_INPUT_KEY_SEQUENCES', {}).get(value)
        if seq:
            self._inputSeqId += 1
            sid = self._inputSeqId
            ProgramLog('Tizen WS [{}]: SetInput {} seq#{} keys={}'.format(
                self._host(), value, sid, seq), 'warning')
            self._send_key_sequence(list(seq), seq_id=sid)
            self._commandedInput = value
            self.WriteStatus('Input', value, None)
            return
        key = self._INPUT_KEY_MAP.get(value)
        if key:
            ProgramLog('Tizen WS [{}]: SetInput {} via {}.'.format(
                self._host(), value, key), 'warning')
            self._send_key(key)
            self._commandedInput = value
            self.WriteStatus('Input', value, None)
        else:
            self.Discard('Invalid Command for SetInput: {}'.format(value))

    def _select_hdmi(self, value):
        """Select HDMI via KEY_HDMI within the Frame cycle.

        On these sets KEY_HDMI walks: HDMI 1 → HDMI 2 → Antenna/Cable → …
        Discrete buttons must compute how many presses move from the last known
        point to the target — never "always press once" (that just advances).
        """
        cycle = ('HDMI 1', 'HDMI 2', 'TV')  # TV = Antenna / Cable in the loop
        if value not in ('HDMI 1', 'HDMI 2'):
            self.Discard('Invalid Command for SetInput: {}'.format(value))
            return

        target_idx = cycle.index(value)

        cur = self._commandedInput
        if cur in ('Antenna', 'Cable', 'Antenna/Cable', 'TV'):
            cur = 'TV'
        if cur in cycle:
            cur_idx = cycle.index(cur)
        else:
            cur_idx = cycle.index('TV')
            ProgramLog('Tizen WS [{}]: SetInput {} — assuming cycle pos Antenna/TV.'
                       .format(self._host(), value), 'warning')

        presses = (target_idx - cur_idx) % len(cycle)
        if presses == 0:
            ProgramLog('Tizen WS [{}]: SetInput {} — already there, skip KEY_HDMI.'
                       .format(self._host(), value), 'warning')
            self._commandedInput = value
            self.WriteStatus('Input', value, None)
            return

        self._inputSeqId += 1
        sid = self._inputSeqId
        ProgramLog('Tizen WS [{}]: SetInput {} from {} — KEY_HDMI x{}.'
                   .format(self._host(), value, cycle[cur_idx], presses),
                   'warning')
        keys = ['KEY_HDMI'] * presses
        self._send_key_sequence(keys, seq_id=sid)
        self._commandedInput = value
        self.WriteStatus('Input', value, None)

    def _send_key_sequence(self, keys, interval=None, seq_id=None):
        """Send remote keys with delay. New seq_id cancels an in-flight sequence."""
        if not keys:
            return
        if seq_id is not None and seq_id != self._inputSeqId:
            return
        if interval is None:
            interval = getattr(self, '_inputKeyInterval', 0.45)
        key = keys[0]
        rest = keys[1:]
        ProgramLog('Tizen WS [{}]: seq key {}'.format(self._host(), key), 'warning')
        self._send_key(key)
        if not rest:
            return
        Wait(interval,
             lambda r=rest, i=interval, s=seq_id: self._send_key_sequence(r, i, s))

    def SetAudioMute(self, value, qualifier):
        """Discrete mute On/Off using toggle-only KEY_MUTE."""
        if value not in ('On', 'Off'):
            self.Discard('Invalid Command for SetAudioMute')
            return
        if self._commandedMute == value:
            ProgramLog('Tizen WS [{}]: AudioMute {} — already {}, skip KEY_MUTE.'
                       .format(self._host(), value, value), 'warning')
            self.WriteStatus('AudioMute', value, None)
            return
        ProgramLog('Tizen WS [{}]: AudioMute {} (KEY_MUTE); was {}.'.format(
            self._host(), value, self._commandedMute), 'warning')
        self._send_key('KEY_MUTE')
        self._commandedMute = value
        self.WriteStatus('AudioMute', value, None)

    def SetVolume(self, value, qualifier):
        """Set volume by flooring then ramping up (absolute).

        Relative KEY_VOL tracking drifts vs the real TV level. Absolute path:
        VOLDOWN × floor, then VOLUP × (UI/100 * scale) so TP 0 → TV 0 and
        TP 100 → TV max.
        """
        try:
            target_ui = int(value)
        except (TypeError, ValueError):
            self.Discard('Invalid Command for SetVolume')
            return
        target_ui = max(0, min(100, target_ui))
        scale = int(getattr(self, '_volumeScale', 100))
        target_tick = int(round(target_ui * scale / 100.0))
        self._commandedVolume = target_ui
        self._volumeTick = target_tick
        self.WriteStatus('Volume', target_ui, None)
        if self._volumeRampBusy:
            ProgramLog('Tizen WS [{}]: Volume ramp busy — queueing retarget {}.'
                       .format(self._host(), target_ui), 'warning')
            self._pendingVolumeTick = target_tick
            return
        self._pendingVolumeTick = None
        ProgramLog('Tizen WS [{}]: Volume absolute UI {} → floor then {} UP.'
                   .format(self._host(), target_ui, target_tick), 'warning')
        self._start_volume_ramp(target_tick)

    def _start_volume_ramp(self, target_tick):
        self._volumeRampBusy = True
        floor = int(getattr(self, '_volumeFloorSteps', 100))
        self._send_volume_steps(
            'KEY_VOLDOWN', floor, 0,
            on_done=lambda t=target_tick: self._after_volume_floor(t))

    def _after_volume_floor(self, target_tick):
        pending = getattr(self, '_pendingVolumeTick', None)
        if pending is not None:
            target_tick = pending
            self._pendingVolumeTick = None
        if target_tick <= 0:
            self._volumeRampBusy = False
            self._volumeTick = 0
            return
        self._send_volume_steps(
            'KEY_VOLUP', target_tick, 0,
            on_done=self._volume_ramp_finished)

    def _volume_ramp_finished(self):
        pending = getattr(self, '_pendingVolumeTick', None)
        self._volumeRampBusy = False
        if pending is not None:
            self._pendingVolumeTick = None
            ProgramLog('Tizen WS [{}]: Volume retarget after ramp → {}.'
                       .format(self._host(), pending), 'warning')
            self._start_volume_ramp(pending)

    def _send_volume_steps(self, key, steps, index=0, on_done=None):
        if steps <= 0 or index >= steps:
            if on_done:
                on_done()
            return
        self._send_key(key)
        if index + 1 < steps:
            interval = getattr(self, '_volumeKeyInterval', 0.05)
            Wait(interval,
                 lambda k=key, s=steps, i=index + 1, d=on_done:
                 self._send_volume_steps(k, s, i, d))
        elif on_done:
            Wait(0.15, on_done)

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
        # Modern Samsungs require TLS on 8002; plaintext WS there is dropped immediately.
        port = int(getattr(self, 'IPPort', 8001) or 8001)
        if port == 8002 and not getattr(self, '_useTLS', False):
            ProgramLog('Tizen WS [{}]: refusing plaintext connect to :8002 (TLS '
                       'required). SSLWrap failed on this firmware.'
                       .format(self._host()), 'error')
            self._wsState = 'closed'
            self._scheduleReconnect()
            return
        # Restore configured token if a prior unauthorized cleared _token
        if self._configuredToken and not self._token:
            self._token = self._configuredToken
        self._wsState = 'connecting'
        self._rxBuffer = b''
        token_status = 'with token' if self._token else 'without token (fresh pairing)'
        tls_status = 'wss' if getattr(self, '_useTLS', False) else 'ws'
        ProgramLog('Tizen WS [{}]: attempting TCP connection to {}:{} ({}, {})...'.format(
            self._host(), getattr(self, 'IPAddress', '?'), port,
            token_status, tls_status),
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
        self._safe_stop_timer(self._KeepAliveTimer)
        self.WriteStatus('ConnectionStatus', 'Disconnected', None)
        if self._autoReconnect:
            self._scheduleReconnect()

    @staticmethod
    def _safe_stop_timer(timer):
        """Stop a Timer only if it is running.

        Extron's Timer.Stop() logs a noisy ERROR ('Failed to run Stop method,
        already stopped.') when the timer is already stopped. Guarding on State
        (and swallowing any error) keeps the program log clean during the normal
        connect/disconnect churn.
        """
        try:
            if timer is not None and timer.State == 'Running':
                timer.Stop()
        except Exception:
            pass

    def _scheduleReconnect(self):
        self._wsState = 'closed'
        if self._autoReconnect and self._ReconnectTimer.State != 'Running':
            self._ReconnectTimer.Restart()

    def _ReconnectTick(self, timer, count):
        if self._wsState == 'closed' and self._autoReconnect:
            self.Connect()
        else:
            self._safe_stop_timer(timer)

    def _KeepAliveTick(self, timer, count):
        if self._wsState != 'open':
            self._safe_stop_timer(timer)
            return
        # Send a real application-level message rather than a WebSocket ping
        # frame. "The Frame" firmware does not reset its idle timeout on ping
        # frames, so it would drop the session after ~40s. Requesting the
        # installed-app list is benign (no visible effect) but generates TV
        # activity/response, resetting the idle timer and keeping the socket up.
        try:
            payload = json.dumps({
                'method': 'ms.channel.emit',
                'params': {
                    'event': 'ed.installedApp.get',
                    'to': 'host',
                },
            }).encode('utf-8')
            self._ws_send(payload, opcode=0x1)
        except Exception as e:
            ProgramLog('Tizen WS [{}]: keep-alive send failed: {}'.format(
                self._host(), e), 'warning')
            # Fall back to a ping frame if the app-level message could not be
            # sent, so we still attempt to hold the connection.
            try:
                self._ws_send(b'', opcode=0x9)
            except Exception:
                pass

    def _stopTimers(self):
        self._safe_stop_timer(self._ReconnectTimer)
        self._safe_stop_timer(self._KeepAliveTimer)

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
        # WS is accepting us. We cannot read real power state, so seed an
        # assumption for the very first command. Displays that stay connected
        # in standby/Art Mode (AssumeStandbyOnConnect=True) are seeded 'Off';
        # all others default to 'On' (socket up usually means the panel is on).
        if self._commandedPower is None:
            assumed = 'Off' if self._assumeStandbyOnConnect else 'On'
            self._commandedPower = assumed
            self.WriteStatus('Power', assumed, None)
            ProgramLog('Tizen WS [{}]: assuming power={} on connect.'.format(
                self._host(), assumed), 'warning')
        # Reset HDMI cycle tracking — cold assume Antenna/Cable.
        self._commandedInput = 'TV'
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
            code, reason = None, ''
            try:
                if len(payload) >= 2:
                    code = struct.unpack('>H', payload[:2])[0]
                    reason = payload[2:].decode('utf-8', 'replace')
            except Exception:
                pass
            ProgramLog('Tizen WS [{}]: received CLOSE frame from TV '
                       '(code={}, reason={!r}) — TV initiated the disconnect.'
                       .format(self._host(), code, reason), 'warning')
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
            ProgramLog('Tizen WS [{}]: full unauthorized msg: {}'.format(
                self._host(), json.dumps(msg)), 'warning')
            # Do NOT clear Token= from devices.py. WSS-paired tokens are often
            # rejected on plaintext 8001; clearing causes a reconnect storm.
            if self._configuredToken:
                self._token = self._configuredToken
                ProgramLog('Tizen WS [{}]: keeping configured Token= {}; if this is '
                           'port 8001, switch to 8002+SSL — ws often rejects wss tokens.'
                           .format(self._host(), self._configuredToken), 'warning')
                # Slow reconnect storm while operator switches / tests TLS
                self._reconnectInterval = 30
                try:
                    self._safe_stop_timer(self._ReconnectTimer)
                    self._ReconnectTimer = Timer(self._reconnectInterval, self._ReconnectTick)
                    self._safe_stop_timer(self._ReconnectTimer)
                except Exception:
                    pass
            elif self._token:
                ProgramLog('Tizen WS [{}]: clearing file token, will retry without '
                           'token.'.format(self._host()), 'warning')
                self._token = None
                try:
                    import os
                    token_file = self._token_filename()
                    if os.path.exists(token_file):
                        os.remove(token_file)
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
        if self._token:
            return  # already set via Token= constructor arg
        if File is None:
            ProgramLog('Tizen WS [{}]: File API unavailable; no token file load.'
                       .format(self._host()), 'warning')
            return
        try:
            fname = self._token_filename()
            f = File(fname, 'r')
            data = f.read()
            f.close()
            data = data.decode() if isinstance(data, (bytes, bytearray)) else data
            data = (data or '').strip()
            if data:
                self._token = data
                ProgramLog('Tizen WS [{}]: loaded token from {}'.format(
                    self._host(), fname), 'warning')
            else:
                ProgramLog('Tizen WS [{}]: token file {} empty'.format(
                    self._host(), fname), 'warning')
        except Exception as e:
            ProgramLog('Tizen WS [{}]: no token file ({}): {}'.format(
                self._host(), self._token_filename(), e), 'warning')

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
    :param Token: optional pre-paired Samsung token (from laptop wss pairing).
                  Preferred over File() on the processor — Extron File storage is
                  easy to miss when pairing off-box.
    :param AssumeStandbyOnConnect: set True for displays that keep the WebSocket
                  open while in standby/Art Mode (e.g. The Terrace LST). KEY_POWER
                  is toggle-only with no state feedback, so on connect we must
                  assume a starting power state; True seeds 'Off' (standby) so
                  On/Off don't get locked in anti-phase. Default False seeds 'On'.
    """

    def __init__(self, Hostname, IPPort=8001, Protocol='TCP', Model=None,
                 MACAddress=None, Name='ExtronControl', Token=None,
                 AssumeStandbyOnConnect=False):
        secure = str(Protocol).upper() in ('SSL', 'TLS', 'WSS')
        # extronlib only accepts 'TCP'/'UDP'/'SSH' here; TLS is applied via
        # SSLWrap() below (never by passing 'SSL' to the base interface).
        EthernetClientInterface.__init__(self, Hostname, IPPort, 'TCP')
        DeviceClass.__init__(self)
        self.MACAddress = MACAddress
        self._clientName = Name or 'ExtronControl'
        self._assumeStandbyOnConnect = bool(AssumeStandbyOnConnect)
        self._useTLS = False
        if secure:
            self._enable_tls()
        self._token = None
        self._configuredToken = None  # Token= from devices.py — never auto-clear
        if Token:
            self._token = str(Token).strip() or None
            self._configuredToken = self._token
            if self._token:
                ProgramLog('Tizen WS [{}]: using Token= from devices.py'.format(
                    getattr(self, 'IPAddress', '?')), 'warning')
        self._load_token()  # file token fills in if Token not provided
        if self._token and not self._configuredToken:
            self._configuredToken = self._token
        if secure and not self._useTLS:
            ProgramLog('Tizen WS [{}]: Protocol requested SSL but TLS wrap failed — '
                       'will not open plaintext to port {}. Fix SSLWrap or use 8001 '
                       'only if the TV accepts ws tokens.'
                       .format(getattr(self, 'IPAddress', '?'), IPPort), 'error')
        if Model and len(self.Models) > 0:
            if Model not in self.Models:
                print('Model mismatch')
            else:
                self.Models[Model]()
        # Force our Connect wrapper to override base class method
        self.Connect = self._connect_wrapper

    def _enable_tls(self):
        """Best-effort TLS upgrade for wss, tolerant of firmware differences.

        On IPCP firmware that cannot SSLWrap, do NOT pretend TLS succeeded —
        leave _useTLS False so callers know wss is unavailable (plaintext on
        port 8002 will be dropped by modern Samsung TVs).
        """
        wrap = getattr(self, 'SSLWrap', None)
        if not callable(wrap):
            ProgramLog('Tizen WS [{}]: SSLWrap not available on this firmware; '
                       'wss unavailable — pair from a laptop and use port 8001 + token.'
                       .format(getattr(self, 'IPAddress', '?')), 'warning')
            return
        attempts = (
            lambda: wrap(),
            lambda: wrap(False),
            lambda: wrap(verify=False),
            lambda: wrap(cert_reqs=0),
            lambda: wrap(cert_reqs='CERT_NONE'),
            lambda: wrap(cert_reqs='none'),
        )
        last_err = None
        for attempt in attempts:
            try:
                attempt()
                self._useTLS = True
                ProgramLog('Tizen WS [{}]: TLS enabled (wss).'.format(
                    getattr(self, 'IPAddress', '?')), 'warning')
                return
            except TypeError as e:
                last_err = e
                continue
            except Exception as e:
                last_err = e
                ProgramLog('Tizen WS [{}]: SSLWrap failed ({}); trying next signature.'
                           .format(getattr(self, 'IPAddress', '?'), e), 'warning')
                continue
        ProgramLog('Tizen WS [{}]: SSLWrap unavailable ({}); wss disabled — '
                   'use port 8001 after laptop pairing (see pair_samsung_tizen.py).'
                   .format(getattr(self, 'IPAddress', '?'), last_err), 'warning')

    def Error(self, message):
        portInfo = 'IP Address/Host: {0}:{1}'.format(self.IPAddress, self.IPPort)
        print('Module: {}'.format(__name__), portInfo,
              'Error Message: {}'.format(message[0]), sep='\r\n')

    def Discard(self, message):
        self.Error([message])
