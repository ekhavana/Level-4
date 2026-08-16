"""
Yoga Studio Touch Panel — Music / BT / Display A/V sources.
ShowPopup for sources (Screening Room style). Shutdown mutes Yoga zone only.
"""

from extronlib import event
from extronlib.ui import Button, Slider
from extronlib.system import MESet

import devices
import variables
import control.av as av

dvTLPYogaStudio = devices.dvTLPYogaStudio

BtnStart = Button(dvTLPYogaStudio, 7000)
BtnSystemPower = Button(dvTLPYogaStudio, 8022)
BtnPowerOffYes = Button(dvTLPYogaStudio, 9028)
BtnPowerOffCancel = Button(dvTLPYogaStudio, 9029)
BtnHelp = Button(dvTLPYogaStudio, 8117)
BtnHelpPageClose = Button(dvTLPYogaStudio, 9057)

YogaStudioMusicPlayerBtn = Button(dvTLPYogaStudio, 282)
YogaStudioBTPlateBtn = Button(dvTLPYogaStudio, 283)
YogaStudioDisplayAVBtn = Button(dvTLPYogaStudio, 6)
# Program Volume on Main / Splash drives the DSP Yoga Studio zone (output 2).
YogaStudioMuteBtn = Button(dvTLPYogaStudio, 275)
YogaStudioVolumeLvl = Slider(dvTLPYogaStudio, 276)

# TV Volume on the Display popup drives the Samsung display's own audio.
YogaStudioTVMuteBtn = Button(dvTLPYogaStudio, 605)
YogaStudioTVVolumeLvl = Slider(dvTLPYogaStudio, 604)

YogaStudioTVPowerOnBtn = Button(dvTLPYogaStudio, 266)
YogaStudioTVPowerOffBtn = Button(dvTLPYogaStudio, 267)

YogaStudioAudioSource = MESet([
    YogaStudioMusicPlayerBtn, YogaStudioBTPlateBtn, YogaStudioDisplayAVBtn
])
YogaStudioTVPower = MESet([YogaStudioTVPowerOffBtn, YogaStudioTVPowerOnBtn])

av.RegisterVolumeSlider('YogaStudio', YogaStudioVolumeLvl)
av.RegisterMuteButton('YogaStudio', YogaStudioMuteBtn)
av.RegisterTVLocalVolumeSlider('YogaStudioTV', YogaStudioTVVolumeLvl)
av.RegisterTVLocalMuteButton('YogaStudioTV', YogaStudioTVMuteBtn)


def _select_music():
    YogaStudioAudioSource.SetCurrent(YogaStudioMusicPlayerBtn)
    av.YogaStudioSelectMusicPlayer()
    dvTLPYogaStudio.ShowPopup(variables.POPUPS['Music Player'])


def _select_bluetooth():
    YogaStudioAudioSource.SetCurrent(YogaStudioBTPlateBtn)
    av.YogaStudioSelectBTPlate()
    dvTLPYogaStudio.ShowPopup(variables.POPUPS['Bluetooth'])


def _select_display_av():
    YogaStudioAudioSource.SetCurrent(YogaStudioDisplayAVBtn)
    YogaStudioTVPower.SetCurrent(YogaStudioTVPowerOnBtn)
    av.YogaStudioSelectDisplayAV()
    dvTLPYogaStudio.ShowPopup(variables.POPUPS['Display'])
    av.RefreshTVLocalVolumeUI('YogaStudioTV')


@event(dvTLPYogaStudio, 'Online')
def TLPOnline(device, state):
    if av.YogaStudioGetSystemPowerState():
        dvTLPYogaStudio.ShowPage(variables.PAGES['Main'])
        av.RefreshLocalVolumeUI(['YogaStudio'])
        av.RefreshTVLocalVolumeUI('YogaStudioTV')
    else:
        dvTLPYogaStudio.ShowPage(variables.PAGES['Splash'])


@event(BtnStart, 'Pressed')
def BtnStartPressed(button, state):
    dvTLPYogaStudio.ShowPage(variables.PAGES['Main'])
    dvTLPYogaStudio.ShowPopup(variables.POPUPS['Starting Up'])

    def OnStartupComplete():
        dvTLPYogaStudio.HidePopup(variables.POPUPS['Starting Up'])
        _select_music()
        av.RefreshLocalVolumeUI(['YogaStudio'])
        av.RefreshTVLocalVolumeUI('YogaStudioTV')

    av.YogaStudioSystemPowerOn(callback=OnStartupComplete)


@event(BtnSystemPower, 'Pressed')
def BtnSystemPowerPressed(button, state):
    dvTLPYogaStudio.ShowPopup(variables.POPUPS['Confirmation'])


@event(BtnPowerOffYes, 'Pressed')
def BtnPowerOffYesPressed(button, state):
    dvTLPYogaStudio.HidePopup(variables.POPUPS['Confirmation'])
    dvTLPYogaStudio.ShowPopup(variables.POPUPS['Powering Down'])

    def OnShutdownComplete():
        dvTLPYogaStudio.HidePopup(variables.POPUPS['Powering Down'])
        dvTLPYogaStudio.ShowPage(variables.PAGES['Splash'])

    av.YogaStudioSystemPowerOff(callback=OnShutdownComplete)


@event(BtnPowerOffCancel, 'Pressed')
def BtnPowerOffCancelPressed(button, state):
    dvTLPYogaStudio.HidePopup(variables.POPUPS['Confirmation'])


@event(BtnHelp, 'Pressed')
def BtnHelpPressed(button, state):
    dvTLPYogaStudio.ShowPopup(variables.POPUPS['Help'])


@event(BtnHelpPageClose, 'Pressed')
def BtnHelpPageClosePressed(button, state):
    dvTLPYogaStudio.HidePopup(variables.POPUPS['Help'])


@event(YogaStudioMusicPlayerBtn, 'Pressed')
def YogaStudioMusicPlayerBtnPressed(button, state):
    _select_music()


@event(YogaStudioBTPlateBtn, 'Pressed')
def YogaStudioBTPlateBtnPressed(button, state):
    _select_bluetooth()


@event(YogaStudioDisplayAVBtn, 'Pressed')
def YogaStudioDisplayAVBtnPressed(button, state):
    _select_display_av()


@event(YogaStudioMuteBtn, 'Pressed')
def YogaStudioMuteBtnPressed(button, state):
    newState = av.YogaStudioToggleMute()
    YogaStudioMuteBtn.SetState(1 if newState else 0)


@event(YogaStudioVolumeLvl, 'Changed')
def YogaStudioVolumeLvlChanged(slider, state, value):
    av.YogaStudioSetVolume(int(value))


@event(YogaStudioTVMuteBtn, 'Pressed')
def YogaStudioTVMuteBtnPressed(button, state):
    newState = av.ToggleTVLocalMute('YogaStudioTV')
    YogaStudioTVMuteBtn.SetState(1 if newState else 0)


@event(YogaStudioTVVolumeLvl, 'Changed')
def YogaStudioTVVolumeLvlChanged(slider, state, value):
    av.PreviewTVLocalVolume('YogaStudioTV', value)


@event(YogaStudioTVVolumeLvl, 'Released')
def YogaStudioTVVolumeLvlReleased(slider, state, value):
    av.SetTVLocalVolume('YogaStudioTV', value)


@event(YogaStudioTVPowerOnBtn, 'Pressed')
def YogaStudioTVPowerOnBtnPressed(button, state):
    YogaStudioTVPower.SetCurrent(YogaStudioTVPowerOnBtn)
    av.YogaStudioTVPowerOn()


@event(YogaStudioTVPowerOffBtn, 'Pressed')
def YogaStudioTVPowerOffBtnPressed(button, state):
    YogaStudioTVPower.SetCurrent(YogaStudioTVPowerOffBtn)
    av.YogaStudioTVPowerOff()
