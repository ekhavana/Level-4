"""
Remote Control Server - Receives commands from main control processor (Level 1)
and drives the Level 4 system. Uses EthernetServerInterfaceEx on TCP port 5000.

Protocol: Roof-style comma-delimited (primary). Also accepts pipe-delimited for compatibility.
One command per line, newline-terminated.

Commands (case-insensitive):
  POWER,ROOM,ON/OFF        rooms: PARTY, YOGA, TERRACE
  TV,TARGET,ON/OFF         targets: PARTY, YOGA, TERRACE1, TERRACE2
  VOL,ROOM,0-100           rooms: PARTY, YOGA, TERRACE, GYM, COURTYARD
  MUTE,ROOM,ON/OFF/TOGGLE  same rooms as VOL
  SRC,ROOM,MUSIC/BT        rooms: PARTY, YOGA
  ROUTE,SOURCE,DEST        sources: PARTYTV, YOGATV, TERRACETV1, TERRACETV2
                           dest: ALL,GYM,YOGA,TERRACE,PARTY,COURTYARD
  GET,STATE                returns snapshot of key states

Feedback (pushed asynchronously, comma-delimited):
  EVT,POWER,ROOM,ON/OFF
  EVT,MUTE,ROOM,ON/OFF
  EVT,VOLUME,ROOM,value
  EVT,SRC,ROOM,NAME

Notes:
* Inputs may be comma or pipe; outputs are comma-delimited.
"""

import json
from extronlib.interface import EthernetServerInterfaceEx
import control.av as av

SERVER_PORT = 10000

_server = None
_clients = set()

_ZONE_MAP = {
    'party room': 'PartyRoom',
    'party': 'PartyRoom',
    'yoga studio': 'YogaStudio',
    'yoga': 'YogaStudio',
    'terrace gallery': 'TerraceGallery',
    'terrace': 'TerraceGallery',
    'terrace gallery 1': 'TerraceGallery',
    'terrace gallery 2': 'TerraceGallery',
    'terrace tv': 'TerraceGallery',
    'level 4 gym': 'Gym',
    'gym': 'Gym',
    'level 4 courtyard': 'Courtyard',
    'courtyard': 'Courtyard',
}

_POWER_CODE_MAP = {
    'PartyRoom': 'PARTY',
    'YogaStudio': 'YOGA',
    'TerraceGallery': 'TERRACE',
}


def _send(line):
    """Send a line of text (with newline) to all connected clients."""
    msg = (line + '\n').encode()
    for c in list(_clients):
        try:
            c.Send(msg)
        except Exception:
            try:
                _clients.remove(c)
            except Exception:
                pass


def _norm_zone(zone):
    if not zone:
        return None
    return _ZONE_MAP.get(str(zone).strip().lower())


def _norm_source(src):
    if not src:
        return None
    s = str(src).strip().lower()
    if 'music' in s:
        return 'music'
    if 'bt' in s or 'bluetooth' in s:
        return 'bt'
    return None


def _norm_route_source(src):
    if not src:
        return None
    s = str(src).strip().lower()
    if 'party' in s and 'tv' in s:
        return 'PartyRoomTV'
    if 'yoga' in s and 'tv' in s:
        return 'YogaStudioTV'
    if 'terrace' in s and 'tv1' in s:
        return 'TerraceGalleryTV1'
    if 'terrace' in s and 'tv2' in s:
        return 'TerraceGalleryTV2'
    if 'terrace' in s and 'tv' in s:
        return 'TerraceGalleryTV1'
    if 'music' in s:
        return 'MusicPlayer'
    if 'bt' in s or 'bluetooth' in s:
        if 'yoga' in s:
            return 'BTPlate_YogaStudio'
        if 'party' in s:
            return 'BTPlate_PartyRoom'
    return None


def _json_set_source(data):
    room = _norm_zone(data.get('zone'))
    source = _norm_source(data.get('source'))
    if room not in ('PartyRoom', 'YogaStudio') or not source:
        return False
    if source == 'music':
        return _call_source_fn(room, 'MusicPlayer')
    if source == 'bt':
        return _call_source_fn(room, 'BTPlate')
    return False


def _call_source_fn(room, src):
    fn_map = {
        'PartyRoom': {
            'MusicPlayer': av.PartyRoomSelectMusicPlayer,
            'BTPlate': av.PartyRoomSelectBTPlate,
        },
        'YogaStudio': {
            'MusicPlayer': av.YogaStudioSelectMusicPlayer,
            'BTPlate': av.YogaStudioSelectBTPlate,
        },
    }
    fn = fn_map.get(room, {}).get(src)
    if not fn:
        return False
    fn()
    return True


def _json_set_volume(data):
    room = _norm_zone(data.get('zone'))
    if room is None:
        return False
    try:
        level = int(data.get('level'))
    except Exception:
        return False
    try:
        av.SetVolume(room, level)
        return True
    except Exception as e:
        print(f'Remote JSON volume error: {e}')
        return False


def _json_set_mute(data):
    room = _norm_zone(data.get('zone'))
    if room is None:
        return False
    state = data.get('state')
    if isinstance(state, str):
        state = state.strip().lower()
        if state in ('on', 'true', '1'):
            state = True
        elif state in ('off', 'false', '0'):
            state = False
    if not isinstance(state, bool):
        return False
    try:
        av.SetMute(room, state)
        return True
    except Exception as e:
        print(f'Remote JSON mute error: {e}')
        return False


def _json_toggle_mute(data):
    room = _norm_zone(data.get('zone'))
    if room is None:
        return False
    try:
        new_state = av.ToggleMute(room)
    except Exception as e:
        print(f'Remote JSON toggle mute error: {e}')
        return False
    _send(f'EVT,MUTE,{room.upper()},{"ON" if new_state else "OFF"}')
    return True


def _json_set_power(data):
    room = _norm_zone(data.get('zone'))
    state = data.get('state')
    if room is None or state is None:
        return False
    state_str = str(state).strip().upper()
    if state_str not in ('ON', 'OFF'):
        return False
    code = _POWER_CODE_MAP.get(room)
    if not code:
        return False
    return _handle_power(code, state_str)


def _json_route_audio(data):
    src = _norm_route_source(data.get('source_zone') or data.get('source'))
    dest = _norm_zone(data.get('dest_zone') or data.get('zone'))
    if not src or not dest:
        return False
    try:
        av.RouteAudioToZone(src, dest)
        return True
    except Exception as e:
        print(f'Remote JSON route error: {e}')
        return False


def _dispatch_json(cmd, data):
    cmd_key = str(cmd).strip().lower()
    handlers = {
        'setsource': _json_set_source,
        'setvolume': _json_set_volume,
        'setmute': _json_set_mute,
        'togglemute': _json_toggle_mute,
        'setpower': _json_set_power,
        'routeaudio': _json_route_audio,
    }
    handler = handlers.get(cmd_key)
    if not handler:
        return False
    try:
        return handler(data or {})
    except Exception as e:
        print(f'Remote JSON error for {cmd}: {e}')
        return False


def _handle_power(room, state):
    if room == 'PARTY':
        av.PartyRoomSystemPowerOn() if state == 'ON' else av.PartyRoomSystemPowerOff()
    elif room == 'YOGA':
        av.YogaStudioSystemPowerOn() if state == 'ON' else av.YogaStudioSystemPowerOff()
    elif room == 'TERRACE':
        av.TerraceGallerySystemPowerOn() if state == 'ON' else av.TerraceGallerySystemPowerOff()
    else:
        return False
    return True


def _handle_tv(target, state):
    if target == 'PARTY':
        av.PartyRoomTVPowerOn() if state == 'ON' else av.PartyRoomTVPowerOff()
    elif target == 'YOGA':
        av.YogaStudioTVPowerOn() if state == 'ON' else av.YogaStudioTVPowerOff()
    elif target == 'TERRACE1':
        av.TerraceGalleryTV1PowerOn() if state == 'ON' else av.TerraceGalleryTV1PowerOff()
    elif target == 'TERRACE2':
        av.TerraceGalleryTV2PowerOn() if state == 'ON' else av.TerraceGalleryTV2PowerOff()
    else:
        return False
    return True


def _handle_vol(room, value):
    try:
        v = int(value)
    except ValueError:
        return False
    room_map = {
        'PARTY': av.PartyRoomSetVolume,
        'YOGA': av.YogaStudioSetVolume,
        'TERRACE': av.TerraceGallerySetVolume,
        'GYM': av.GymSetVolume,
        'COURTYARD': av.CourtyardSetVolume,
    }
    fn = room_map.get(room)
    if not fn:
        return False
    fn(v)
    return True


def _handle_mute(room, mode):
    room_map_toggle = {
        'PARTY': av.PartyRoomToggleMute,
        'YOGA': av.YogaStudioToggleMute,
        'TERRACE': av.TerraceGalleryToggleMute,
        'GYM': av.GymToggleMute,
        'COURTYARD': av.CourtyardToggleMute,
    }
    room_map_set = {
        'PARTY': av.PartyRoomSetMute,
        'YOGA': av.YogaStudioSetMute,
        'TERRACE': av.TerraceGallerySetMute,
        'GYM': av.GymSetMute,
        'COURTYARD': av.CourtyardSetMute,
    }
    if mode == 'TOGGLE':
        fn = room_map_toggle.get(room)
        if not fn:
            return False
        new_state = fn()
        _send(f'EVT,MUTE,{room},{"ON" if new_state else "OFF"}')
        return True
    elif mode in ('ON', 'OFF'):
        fn = room_map_set.get(room)
        if not fn:
            return False
        fn(mode == 'ON')
        return True
    return False


def _handle_src(room, src):
    if room == 'PARTY':
        if src == 'MUSIC':
            av.PartyRoomSelectMusicPlayer()
        elif src == 'BT':
            av.PartyRoomSelectBTPlate()
        else:
            return False
    elif room == 'YOGA':
        if src == 'MUSIC':
            av.YogaStudioSelectMusicPlayer()
        elif src == 'BT':
            av.YogaStudioSelectBTPlate()
        else:
            return False
    else:
        return False
    return True


def _handle_route(source, dest):
    # normalize
    if source == 'PARTYTV':
        if dest == 'ALL':
            av.PartyRoomTVRouteToAll()
        elif dest == 'GYM':
            av.PartyRoomTVRouteToGym()
        elif dest == 'YOGA':
            av.PartyRoomTVRouteToYogaStudio()
        elif dest == 'TERRACE':
            av.PartyRoomTVRouteToTerrace()
        elif dest == 'PARTY':
            av.PartyRoomTVRouteToPartyRoom()
        elif dest == 'COURTYARD':
            av.PartyRoomTVRouteToCourtyard()
        else:
            return False
    elif source == 'YOGATV':
        if dest == 'ALL':
            av.YogaStudioTVRouteToAll()
        elif dest == 'GYM':
            av.YogaStudioTVRouteToGym()
        elif dest == 'YOGA':
            av.YogaStudioTVRouteToYogaStudio()
        elif dest == 'TERRACE':
            av.YogaStudioTVRouteToTerrace()
        elif dest == 'PARTY':
            av.YogaStudioTVRouteToPartyRoom()
        elif dest == 'COURTYARD':
            av.YogaStudioTVRouteToCourtyard()
        else:
            return False
    elif source == 'TERRACETV1':
        if dest == 'ALL':
            av.TerraceGalleryTV1RouteToAll()
        elif dest == 'GYM':
            av.TerraceGalleryTV1RouteToGym()
        elif dest == 'YOGA':
            av.TerraceGalleryTV1RouteToYogaStudio()
        elif dest == 'TERRACE':
            av.TerraceGalleryTV1RouteToTerrace()
        elif dest == 'PARTY':
            av.TerraceGalleryTV1RouteToPartyRoom()
        elif dest == 'COURTYARD':
            av.TerraceGalleryTV1RouteToCourtyard()
        else:
            return False
    elif source == 'TERRACETV2':
        if dest == 'ALL':
            av.TerraceGalleryTV2RouteToAll()
        elif dest == 'GYM':
            av.TerraceGalleryTV2RouteToGym()
        elif dest == 'YOGA':
            av.TerraceGalleryTV2RouteToYogaStudio()
        elif dest == 'TERRACE':
            av.TerraceGalleryTV2RouteToTerrace()
        elif dest == 'PARTY':
            av.TerraceGalleryTV2RouteToPartyRoom()
        elif dest == 'COURTYARD':
            av.TerraceGalleryTV2RouteToCourtyard()
        else:
            return False
    else:
        return False
    return True


def _snapshot():
    parts = []
    rooms = ['PartyRoom', 'YogaStudio', 'TerraceGallery', 'Gym', 'Courtyard']
    for r in rooms:
        ui_room = r.upper()
        power = av.SystemPowerState.get(r, False)
        mute = av.AudioMuteState.get(r, False)
        vol = av.VolumeLevel.get(r, 50)
        src = av.CurrentAudioSource.get(r, '')
        parts.append(f'{ui_room}:POWER={"ON" if power else "OFF"},MUTE={"ON" if mute else "OFF"},VOL={vol},SRC={src}')
    return 'STATE,' + ';'.join(parts)


def _process_command(cmd):
    delim = ',' if ',' in cmd else '|'
    tokens = [t.strip() for t in cmd.split(delim)]
    if not tokens or not tokens[0]:
        return
    op = tokens[0].upper()

    if op == 'POWER' and len(tokens) == 3:
        ok = _handle_power(tokens[1].upper(), tokens[2].upper())
    elif op == 'TV' and len(tokens) == 3:
        ok = _handle_tv(tokens[1].upper(), tokens[2].upper())
    elif op == 'VOL' and len(tokens) == 3:
        ok = _handle_vol(tokens[1].upper(), tokens[2])
    elif op == 'MUTE' and len(tokens) == 3:
        ok = _handle_mute(tokens[1].upper(), tokens[2].upper())
    elif op == 'SRC' and len(tokens) == 3:
        ok = _handle_src(tokens[1].upper(), tokens[2].upper())
    elif op == 'ROUTE' and len(tokens) == 3:
        ok = _handle_route(tokens[1].upper(), tokens[2].upper())
    elif op == 'GET' and len(tokens) == 2 and tokens[1].upper() == 'STATE':
        _send(_snapshot())
        ok = True
    else:
        ok = False

    if ok is False:
        _send(f'ERR,{cmd}')
    elif ok is True and op != 'GET':
        _send(f'OK,{cmd}')


def _on_connect(interface, client, state):
    if state == 'Connected':
        _clients.add(client)
        _send('EVT,STATUS,CONNECTED')
    elif state == 'Disconnected':
        try:
            _clients.remove(client)
        except Exception:
            pass


def _on_receive(interface, client, data):
    try:
        text = data.decode()
    except Exception:
        return
    lines = text.replace('\r', '').split('\n')
    for line in lines:
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            payload = None

        if isinstance(payload, dict) and 'command' in payload:
            ok = _dispatch_json(payload.get('command'), payload.get('data') if isinstance(payload.get('data'), dict) else {})
            if ok is False:
                _send(f'ERR,{payload.get("command")}')
            elif ok is True:
                _send(f'OK,{payload.get("command")}')
            continue

        _process_command(line)


def Start():
    """Start the Ethernet server (idempotent)."""
    global _server
    if _server:
        return
    _server = EthernetServerInterfaceEx(SERVER_PORT, 'TCP', 'Any')
    # extronlib runtime exposes these handlers; pylance type stubs omit them
    _server.SetConnectionHandler(_on_connect)  # type: ignore[attr-defined]
    _server.SetReceiveDataHandler(_on_receive)  # type: ignore[attr-defined]
    print(f'Remote Control: Listening on TCP {SERVER_PORT}')

    # Register for AV state changes to push feedback
    av.RegisterUICallback('VolumeChanged', lambda room, level: _send(f'EVT,VOLUME,{room.upper()},{level}'))
    av.RegisterUICallback('MuteChanged', lambda room, muted: _send(f'EVT,MUTE,{room.upper()},{"ON" if muted else "OFF"}'))
    av.RegisterUICallback('PowerChanged', lambda room, power: _send(f'EVT,POWER,{room.upper()},{"ON" if power else "OFF"}'))
    av.RegisterUICallback('SourceChanged', lambda room, source: _send(f'EVT,SRC,{room.upper()},{source.upper()}'))

