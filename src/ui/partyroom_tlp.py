"""
Party Room Touch Panel — Music / BT / HDMI / Roku sources + Roku keys.
ShowPopup for sources (Screening Room style). Shutdown mutes Party zone only.
"""

from extronlib import event
from extronlib.ui import Button, Slider
from extronlib.system import MESet

import devices
import variables
import control.av as av

dvPartyRoomTLP = devices.dvPartyRoomTLP

# System Control
BtnStart = Button(dvPartyRoomTLP, 7001)
BtnSystemPower = Button(dvPartyRoomTLP, 8022)
BtnPowerOffYes = Button(dvPartyRoomTLP, 9028)
BtnPowerOffCancel = Button(dvPartyRoomTLP, 9029)
BtnHelp = Button(dvPartyRoomTLP, 8117)
BtnHelpPageClose = Button(dvPartyRoomTLP, 9057)

# Sources
PartyRoomMusicPlayerBtn = Button(dvPartyRoomTLP, 254)
PartyRoomBTPlateBtn = Button(dvPartyRoomTLP, 255)
PartyRoomRokuBtn = Button(dvPartyRoomTLP, 252)
PartyRoomHDMIBtn = Button(dvPartyRoomTLP, 4)
# Program Volume on Main / Splash drives the DSP Party Room zone (output 4).
PartyRoomMuteBtn = Button(dvPartyRoomTLP, 247)
PartyRoomVolumeLvl = Slider(dvPartyRoomTLP, 248)

# TV Volume on the Roku / HDMI popups drives the Samsung display's own audio.
PartyRoomTVMuteBtn = Button(dvPartyRoomTLP, 601)
PartyRoomTVVolumeLvl = Slider(dvPartyRoomTLP, 600)

PartyRoomTVPowerOnBtn = Button(dvPartyRoomTLP, 245)
PartyRoomTVPowerOffBtn = Button(dvPartyRoomTLP, 246)

PartyRmAudioSource = MESet([
    PartyRoomMusicPlayerBtn, PartyRoomBTPlateBtn, PartyRoomRokuBtn, PartyRoomHDMIBtn
])
PartyRmTVPower = MESet([PartyRoomTVPowerOffBtn, PartyRoomTVPowerOnBtn])

# Roku remote
BtnRokuHome = Button(dvPartyRoomTLP, 300)
BtnRokuBack = Button(dvPartyRoomTLP, 301)
BtnRokuUp = Button(dvPartyRoomTLP, 302)
BtnRokuDown = Button(dvPartyRoomTLP, 303)
BtnRokuLeft = Button(dvPartyRoomTLP, 304)
BtnRokuRight = Button(dvPartyRoomTLP, 305)
BtnRokuSelect = Button(dvPartyRoomTLP, 306)
BtnRokuPlay = Button(dvPartyRoomTLP, 307)
BtnRokuRev = Button(dvPartyRoomTLP, 308)
BtnRokuFwd = Button(dvPartyRoomTLP, 309)
# Former Netflix button (join 312) — layout relabeled to Hulu.
BtnRokuHulu = Button(dvPartyRoomTLP, 312)
BtnRokuYoutube = Button(dvPartyRoomTLP, 313)

av.RegisterVolumeSlider('PartyRoom', PartyRoomVolumeLvl)
av.RegisterMuteButton('PartyRoom', PartyRoomMuteBtn)
av.RegisterTVLocalVolumeSlider('PartyRoomTV', PartyRoomTVVolumeLvl)
av.RegisterTVLocalMuteButton('PartyRoomTV', PartyRoomTVMuteBtn)


def _select_music():
    PartyRmAudioSource.SetCurrent(PartyRoomMusicPlayerBtn)
    av.PartyRoomSelectMusicPlayer()
    dvPartyRoomTLP.ShowPopup(variables.POPUPS['Music Player'])


def _select_bluetooth():
    PartyRmAudioSource.SetCurrent(PartyRoomBTPlateBtn)
    av.PartyRoomSelectBTPlate()
    dvPartyRoomTLP.ShowPopup(variables.POPUPS['Bluetooth'])


def _select_hdmi():
    PartyRmAudioSource.SetCurrent(PartyRoomHDMIBtn)
    PartyRmTVPower.SetCurrent(PartyRoomTVPowerOnBtn)
    av.PartyRoomSelectHDMI()
    dvPartyRoomTLP.ShowPopup(variables.POPUPS['HDMI'])
    av.RefreshTVLocalVolumeUI('PartyRoomTV')


def _select_roku():
    PartyRmAudioSource.SetCurrent(PartyRoomRokuBtn)
    PartyRmTVPower.SetCurrent(PartyRoomTVPowerOnBtn)
    av.PartyRoomSelectRoku()
    dvPartyRoomTLP.ShowPopup(variables.POPUPS['Roku'])
    av.RefreshTVLocalVolumeUI('PartyRoomTV')


@event(dvPartyRoomTLP, 'Online')
def TLPOnline(device, state):
    if av.PartyRoomGetSystemPowerState():
        dvPartyRoomTLP.ShowPage(variables.PAGES['Main'])
        av.RefreshLocalVolumeUI(['PartyRoom'])
        av.RefreshTVLocalVolumeUI('PartyRoomTV')
    else:
        dvPartyRoomTLP.ShowPage(variables.PAGES['Splash'])


@event(BtnStart, 'Pressed')
def BtnStartPressed(button, state):
    dvPartyRoomTLP.ShowPage(variables.PAGES['Main'])
    dvPartyRoomTLP.ShowPopup(variables.POPUPS['Starting Up'])

    def OnStartupComplete():
        dvPartyRoomTLP.HidePopup(variables.POPUPS['Starting Up'])
        _select_music()
        av.RefreshLocalVolumeUI(['PartyRoom'])
        av.RefreshTVLocalVolumeUI('PartyRoomTV')

    av.PartyRoomSystemPowerOn(callback=OnStartupComplete)


@event(BtnSystemPower, 'Pressed')
def BtnSystemPowerPressed(button, state):
    dvPartyRoomTLP.ShowPopup(variables.POPUPS['Confirmation'])


@event(BtnPowerOffYes, 'Pressed')
def BtnPowerOffYesPressed(button, state):
    dvPartyRoomTLP.HidePopup(variables.POPUPS['Confirmation'])
    dvPartyRoomTLP.ShowPopup(variables.POPUPS['Powering Down'])

    def OnShutdownComplete():
        dvPartyRoomTLP.HidePopup(variables.POPUPS['Powering Down'])
        dvPartyRoomTLP.ShowPage(variables.PAGES['Splash'])

    av.PartyRoomSystemPowerOff(callback=OnShutdownComplete)


@event(BtnPowerOffCancel, 'Pressed')
def BtnPowerOffCancelPressed(button, state):
    dvPartyRoomTLP.HidePopup(variables.POPUPS['Confirmation'])


@event(BtnHelp, 'Pressed')
def BtnHelpPressed(button, state):
    dvPartyRoomTLP.ShowPopup(variables.POPUPS['Help'])


@event(BtnHelpPageClose, 'Pressed')
def BtnHelpPageClosePressed(button, state):
    dvPartyRoomTLP.HidePopup(variables.POPUPS['Help'])


@event(PartyRoomMusicPlayerBtn, 'Pressed')
def PartyRoomMusicPlayerBtnPressed(button, state):
    _select_music()


@event(PartyRoomBTPlateBtn, 'Pressed')
def PartyRoomBTPlateBtnPressed(button, state):
    _select_bluetooth()


@event(PartyRoomHDMIBtn, 'Pressed')
def PartyRoomHDMIBtnPressed(button, state):
    _select_hdmi()


@event(PartyRoomRokuBtn, 'Pressed')
def PartyRoomRokuBtnPressed(button, state):
    _select_roku()


@event(PartyRoomMuteBtn, 'Pressed')
def PartyRoomMuteBtnPressed(button, state):
    newState = av.PartyRoomToggleMute()
    PartyRoomMuteBtn.SetState(1 if newState else 0)


@event(PartyRoomVolumeLvl, 'Changed')
def PartyRoomVolumeLvlChanged(slider, state, value):
    av.PartyRoomSetVolume(int(value))


@event(PartyRoomTVMuteBtn, 'Pressed')
def PartyRoomTVMuteBtnPressed(button, state):
    newState = av.ToggleTVLocalMute('PartyRoomTV')
    PartyRoomTVMuteBtn.SetState(1 if newState else 0)


@event(PartyRoomTVVolumeLvl, 'Changed')
def PartyRoomTVVolumeLvlChanged(slider, state, value):
    av.PreviewTVLocalVolume('PartyRoomTV', value)


@event(PartyRoomTVVolumeLvl, 'Released')
def PartyRoomTVVolumeLvlReleased(slider, state, value):
    av.SetTVLocalVolume('PartyRoomTV', value)


@event(PartyRoomTVPowerOnBtn, 'Pressed')
def PartyRoomTVPowerOnBtnPressed(button, state):
    PartyRmTVPower.SetCurrent(PartyRoomTVPowerOnBtn)
    av.PartyRoomTVPowerOn()


@event(PartyRoomTVPowerOffBtn, 'Pressed')
def PartyRoomTVPowerOffBtnPressed(button, state):
    PartyRmTVPower.SetCurrent(PartyRoomTVPowerOffBtn)
    av.PartyRoomTVPowerOff()


def _roku(action):
    av.PartyRoomRokuKey(action)


@event(BtnRokuHome, 'Pressed')
def _(button, state):
    _roku('Home')


@event(BtnRokuBack, 'Pressed')
def _(button, state):
    _roku('Back')


@event(BtnRokuUp, 'Pressed')
def _(button, state):
    _roku('Up')


@event(BtnRokuDown, 'Pressed')
def _(button, state):
    _roku('Down')


@event(BtnRokuLeft, 'Pressed')
def _(button, state):
    _roku('Left')


@event(BtnRokuRight, 'Pressed')
def _(button, state):
    _roku('Right')


@event(BtnRokuSelect, 'Pressed')
def _(button, state):
    _roku('Select')


@event(BtnRokuPlay, 'Pressed')
def _(button, state):
    _roku('Play')


@event(BtnRokuRev, 'Pressed')
def _(button, state):
    _roku('Rev')


@event(BtnRokuFwd, 'Pressed')
def _(button, state):
    _roku('Fwd')


@event(BtnRokuHulu, 'Pressed')
def _(button, state):
    _roku('LaunchHulu')


@event(BtnRokuYoutube, 'Pressed')
def _(button, state):
    _roku('LaunchYouTube')
