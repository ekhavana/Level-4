"""
Terrace Gallery 2 Touch Panel — Roku source, local Frame TV volume, TV2 power.
Audio stays on the TV (no DSP Send-to).
"""

from extronlib import event
from extronlib.ui import Button, Slider
from extronlib.system import MESet, Wait

import devices
import variables
import control.av as av

dvTLP = devices.dvTerraceGalleryTLP2

BtnStart = Button(dvTLP, 7002)
BtnSystemPower = Button(dvTLP, 8022)
BtnPowerOffYes = Button(dvTLP, 9028)
BtnPowerOffCancel = Button(dvTLP, 9029)
BtnHelp = Button(dvTLP, 8117)
BtnHelpPageClose = Button(dvTLP, 9057)

BtnSourceRoku = Button(dvTLP, 1018)
# GUI IDs were reversed vs TV1 naming — On=270, Off=269 on this panel
BtnTVPowerOn = Button(dvTLP, 270)
BtnTVPowerOff = Button(dvTLP, 269)
BtnMute = Button(dvTLP, 1020)
VolumeSlider = Slider(dvTLP, 1019)

TVPowerBtns = MESet([BtnTVPowerOff, BtnTVPowerOn])
SourceBtns = MESet([BtnSourceRoku])

BtnRokuRev = Button(dvTLP, 1021)
BtnRokuPlay = Button(dvTLP, 1022)
BtnRokuFwd = Button(dvTLP, 1023)
BtnRokuLeft = Button(dvTLP, 1025)
BtnRokuUp = Button(dvTLP, 1026)
BtnRokuRight = Button(dvTLP, 1027)
BtnRokuDown = Button(dvTLP, 1028)
BtnRokuSelect = Button(dvTLP, 1029)
# Former Netflix button (join 1030) — layout relabeled to Hulu.
BtnRokuHulu = Button(dvTLP, 1030)
BtnRokuHome = Button(dvTLP, 1031)
BtnRokuBack = Button(dvTLP, 1033)
BtnRokuYoutube = Button(dvTLP, 1034)

av.RegisterTVLocalVolumeSlider('TerraceTV2', VolumeSlider)


def _show_roku_popup():
    SourceBtns.SetCurrent(BtnSourceRoku)
    TVPowerBtns.SetCurrent(BtnTVPowerOn)
    dvTLP.ShowPopup(variables.POPUPS['Roku TV 2'])
    av.RefreshTVLocalVolumeUI('TerraceTV2')


def _select_roku():
    SourceBtns.SetCurrent(BtnSourceRoku)
    TVPowerBtns.SetCurrent(BtnTVPowerOn)
    av.TerraceSelectRoku2()
    # ShowPage can clear popups — delay ShowPopup slightly
    Wait(0.3, _show_roku_popup)


@event(dvTLP, 'Online')
def TLPOnline(device, state):
    if av.TerraceGalleryGetSystemPowerState():
        dvTLP.ShowPage(variables.PAGES['Main'])
        Wait(0.3, _show_roku_popup)
    else:
        dvTLP.ShowPage(variables.PAGES['Splash'])


@event(BtnStart, 'Pressed')
def BtnStartPressed(button, state):
    dvTLP.ShowPage(variables.PAGES['Main'])
    dvTLP.ShowPopup(variables.POPUPS['Starting Up'])

    def OnStartupComplete():
        dvTLP.HidePopup(variables.POPUPS['Starting Up'])
        _select_roku()

    av.TerraceGallerySystemPowerOn(callback=OnStartupComplete)


@event(BtnSystemPower, 'Pressed')
def BtnSystemPowerPressed(button, state):
    dvTLP.ShowPopup(variables.POPUPS['Confirmation'])


@event(BtnPowerOffYes, 'Pressed')
def BtnPowerOffYesPressed(button, state):
    dvTLP.HidePopup(variables.POPUPS['Confirmation'])
    dvTLP.ShowPopup(variables.POPUPS['Powering Down'])

    def OnShutdownComplete():
        dvTLP.HidePopup(variables.POPUPS['Powering Down'])
        dvTLP.ShowPage(variables.PAGES['Splash'])

    av.TerraceGallerySystemPowerOff(callback=OnShutdownComplete)


@event(BtnPowerOffCancel, 'Pressed')
def BtnPowerOffCancelPressed(button, state):
    dvTLP.HidePopup(variables.POPUPS['Confirmation'])


@event(BtnHelp, 'Pressed')
def BtnHelpPressed(button, state):
    dvTLP.ShowPopup(variables.POPUPS['Help'])


@event(BtnHelpPageClose, 'Pressed')
def BtnHelpPageClosePressed(button, state):
    dvTLP.HidePopup(variables.POPUPS['Help'])


@event(BtnSourceRoku, 'Pressed')
def BtnSourceRokuPressed(button, state):
    _select_roku()


@event(BtnTVPowerOn, 'Pressed')
def BtnTVPowerOnPressed(button, state):
    TVPowerBtns.SetCurrent(BtnTVPowerOn)
    av.TerraceGalleryTV2PowerOn()


@event(BtnTVPowerOff, 'Pressed')
def BtnTVPowerOffPressed(button, state):
    TVPowerBtns.SetCurrent(BtnTVPowerOff)
    av.TerraceGalleryTV2PowerOff()


@event(BtnMute, 'Pressed')
def BtnMutePressed(button, state):
    muted = av.ToggleTVLocalMute('TerraceTV2')
    BtnMute.SetState(1 if muted else 0)


@event(VolumeSlider, 'Changed')
def VolumeChanged(slider, state, value):
    av.PreviewTVLocalVolume('TerraceTV2', value)


@event(VolumeSlider, 'Released')
def VolumeReleased(slider, state, value):
    av.SetTVLocalVolume('TerraceTV2', value)


def _roku(action):
    av.TerraceRokuKey2(action)


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
