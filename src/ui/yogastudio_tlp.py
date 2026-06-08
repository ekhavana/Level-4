"""
Yoga Studio Touch Panel UI Module
* UI object definition
* Event handlers for Yoga Studio control
"""

# Extron Library imports
from extronlib import event
from extronlib.ui import Button, Slider
from extronlib.system import MESet

# Project imports
import devices
import variables
import control.av as av

# Touch Panel Device Reference
dvTLPYogaStudio = devices.dvTLPYogaStudio

# ========================================================================================
# UI Object Definitions
# ========================================================================================

# System Control Buttons
BtnStart = Button(dvTLPYogaStudio, 7000)
BtnSystemPower = Button(dvTLPYogaStudio, 8022)
BtnPowerOffYes = Button(dvTLPYogaStudio, 9028)
BtnPowerOffCancel = Button(dvTLPYogaStudio, 9029)
BtnHelp = Button(dvTLPYogaStudio, 8117)
BtnHelpPageClose = Button(dvTLPYogaStudio, 9057)

# Room Control Buttons
#YogaStudioCancelBtn = Button(dvTLPYogaStudio, 44)
YogaStudioMusicPlayerBtn = Button(dvTLPYogaStudio, 282)
YogaStudioBTPlateBtn = Button(dvTLPYogaStudio, 283)
YogaStudioMuteBtn = Button(dvTLPYogaStudio, 275)
YogaStudioVolumeLvl = Slider(dvTLPYogaStudio, 276)

# TV Power Buttons
YogaStudioTVPowerOnBtn = Button(dvTLPYogaStudio, 266)
YogaStudioTVPowerOffBtn = Button(dvTLPYogaStudio, 267)

# TV Audio Routing Buttons
YogaStudioTVAudioSendToAllBtn = Button(dvTLPYogaStudio, 281)
YogaStudioTVAudioSendToGymBtn = Button(dvTLPYogaStudio, 277)
YogaStudioTVAudioSendToYogaBtn = Button(dvTLPYogaStudio, 278)
YogaStudioTVAudioSendToTerraceBtn = Button(dvTLPYogaStudio, 279)
YogaStudioTVAudioSendToPartyRmBtn = Button(dvTLPYogaStudio, 280)
YogaStudioTVAudioSendToCourtyardBtn = Button(dvTLPYogaStudio, 284)

# Mutually Exclusive Button Sets
YogaStudioAudioSource = MESet([YogaStudioMusicPlayerBtn, YogaStudioBTPlateBtn])
YogaStudioTVPower = MESet([YogaStudioTVPowerOffBtn, YogaStudioTVPowerOnBtn])
YogaStudioSendToMES = MESet([YogaStudioTVAudioSendToAllBtn, YogaStudioTVAudioSendToGymBtn, 
                             YogaStudioTVAudioSendToPartyRmBtn, YogaStudioTVAudioSendToTerraceBtn, 
                             YogaStudioTVAudioSendToYogaBtn, YogaStudioTVAudioSendToCourtyardBtn])

# Register volume slider for DSP feedback (at module load time)
av.RegisterVolumeSlider('YogaStudio', YogaStudioVolumeLvl)

# ========================================================================================
# Event Handlers
# ========================================================================================

# System Control Events -----------------------------------------------------------------

@event(BtnStart, 'Pressed')
def BtnStartPressed(button, state):
    """Start system - navigate to main page and power on"""
    print('Yoga Studio: Start button pressed')
    dvTLPYogaStudio.ShowPage(variables.PAGES['Main'])
    dvTLPYogaStudio.ShowPopup(variables.POPUPS['Starting Up'])
    
    def OnStartupComplete():
        dvTLPYogaStudio.HidePopup(variables.POPUPS['Starting Up'])
        print('Yoga Studio: System startup complete')
    
    av.YogaStudioSystemPowerOn(callback=OnStartupComplete)

@event(BtnSystemPower, 'Pressed')
def BtnSystemPowerPressed(button, state):
    """Show power off confirmation popup"""
    print('Yoga Studio: System Power button pressed')
    dvTLPYogaStudio.ShowPopup(variables.POPUPS['Confirmation'])

@event(BtnPowerOffYes, 'Pressed')
def BtnPowerOffYesPressed(button, state):
    """Confirm system shutdown"""
    print('Yoga Studio: Power Off confirmed')
    dvTLPYogaStudio.HidePopup(variables.POPUPS['Confirmation'])
    dvTLPYogaStudio.ShowPopup(variables.POPUPS['Powering Down'])
    
    def OnShutdownComplete():
        dvTLPYogaStudio.HidePopup(variables.POPUPS['Powering Down'])
        dvTLPYogaStudio.ShowPage(variables.PAGES['Splash'])
        print('Yoga Studio: System shutdown complete')
    
    av.YogaStudioSystemPowerOff(callback=OnShutdownComplete)

@event(BtnPowerOffCancel, 'Pressed')
def BtnPowerOffCancelPressed(button, state):
    """Cancel shutdown"""
    print('Yoga Studio: Power Off cancelled')
    dvTLPYogaStudio.HidePopup(variables.POPUPS['Confirmation'])

@event(BtnHelp, 'Pressed')
def BtnHelpPressed(button, state):
    """Show help popup"""
    print('Yoga Studio: Help button pressed')
    dvTLPYogaStudio.ShowPopup(variables.POPUPS['Help'])

@event(BtnHelpPageClose, 'Pressed')
def BtnHelpPageClosePressed(button, state):
    """Close help popup"""
    print('Yoga Studio: Help page closed')
    dvTLPYogaStudio.HidePopup(variables.POPUPS['Help'])

#@event(YogaStudioCancelBtn, 'Pressed')
#def YogaStudioCancelBtnPressed(button, state):
#    """Handle cancel/back navigation"""
#    print('Yoga Studio: Cancel button pressed')

# Audio Source Selection Events ---------------------------------------------------------

@event(YogaStudioMusicPlayerBtn, 'Pressed')
def YogaStudioMusicPlayerBtnPressed(button, state):
    """Select Music Player as audio source"""
    print('Yoga Studio: Music Player selected')
    YogaStudioAudioSource.SetCurrent(YogaStudioMusicPlayerBtn)
    av.YogaStudioSelectMusicPlayer()

@event(YogaStudioBTPlateBtn, 'Pressed')
def YogaStudioBTPlateBtnPressed(button, state):
    """Select Bluetooth Plate as audio source"""
    print('Yoga Studio: Bluetooth Plate selected')
    YogaStudioAudioSource.SetCurrent(YogaStudioBTPlateBtn)
    av.YogaStudioSelectBTPlate()

# Volume Control Events -----------------------------------------------------------------

@event(YogaStudioMuteBtn, 'Pressed')
def YogaStudioMuteBtnPressed(button, state):
    """Toggle mute state"""
    print('Yoga Studio: Mute button pressed')
    newState = av.YogaStudioToggleMute()
    YogaStudioMuteBtn.SetState(1 if newState else 0)

@event(YogaStudioVolumeLvl, 'Changed')
def YogaStudioVolumeLvlChanged(slider, state, value):
    """Handle volume slider change"""
    print(f'Yoga Studio: Volume changed to {value}')
    av.YogaStudioSetVolume(value)

# TV Power Control Events ---------------------------------------------------------------

@event(YogaStudioTVPowerOnBtn, 'Pressed')
def YogaStudioTVPowerOnBtnPressed(button, state):
    """Turn TV on"""
    print('Yoga Studio: TV Power On pressed')
    YogaStudioTVPower.SetCurrent(YogaStudioTVPowerOnBtn)
    av.YogaStudioTVPowerOn()

@event(YogaStudioTVPowerOffBtn, 'Pressed')
def YogaStudioTVPowerOffBtnPressed(button, state):
    """Turn TV off"""
    print('Yoga Studio: TV Power Off pressed')
    YogaStudioTVPower.SetCurrent(YogaStudioTVPowerOffBtn)
    av.YogaStudioTVPowerOff()

# TV Audio Routing Events ---------------------------------------------------------------

@event(YogaStudioTVAudioSendToAllBtn, 'Pressed')
def YogaStudioTVAudioSendToAllBtnPressed(button, state):
    """Route TV audio to all zones"""
    print('Yoga Studio: Send TV Audio to All Zones')
    YogaStudioSendToMES.SetCurrent(YogaStudioTVAudioSendToAllBtn)
    av.YogaStudioTVRouteToAll()

@event(YogaStudioTVAudioSendToGymBtn, 'Pressed')
def YogaStudioTVAudioSendToGymBtnPressed(button, state):
    """Route TV audio to Gym"""
    print('Yoga Studio: Send TV Audio to Gym')
    YogaStudioSendToMES.SetCurrent(YogaStudioTVAudioSendToGymBtn)
    av.YogaStudioTVRouteToGym()

@event(YogaStudioTVAudioSendToYogaBtn, 'Pressed')
def YogaStudioTVAudioSendToYogaBtnPressed(button, state):
    """Route TV audio to Yoga Studio only"""
    print('Yoga Studio: Send TV Audio to Yoga Studio')
    YogaStudioSendToMES.SetCurrent(YogaStudioTVAudioSendToYogaBtn)
    av.YogaStudioTVRouteToYogaStudio()

@event(YogaStudioTVAudioSendToTerraceBtn, 'Pressed')
def YogaStudioTVAudioSendToTerraceBtnPressed(button, state):
    """Route TV audio to Terrace Gallery"""
    print('Yoga Studio: Send TV Audio to Terrace')
    YogaStudioSendToMES.SetCurrent(YogaStudioTVAudioSendToTerraceBtn)
    av.YogaStudioTVRouteToTerrace()

@event(YogaStudioTVAudioSendToPartyRmBtn, 'Pressed')
def YogaStudioTVAudioSendToPartyRmBtnPressed(button, state):
    """Route TV audio to Party Room"""
    print('Yoga Studio: Send TV Audio to Party Room')
    YogaStudioSendToMES.SetCurrent(YogaStudioTVAudioSendToPartyRmBtn)
    av.YogaStudioTVRouteToPartyRoom()

@event(YogaStudioTVAudioSendToCourtyardBtn, 'Pressed')
def YogaStudioTVAudioSendToCourtyardBtnPressed(button, state):
    """Route TV audio to Courtyard"""
    print('Yoga Studio: Send TV Audio to Courtyard')
    YogaStudioSendToMES.SetCurrent(YogaStudioTVAudioSendToCourtyardBtn)
    av.YogaStudioTVRouteToCourtyard()