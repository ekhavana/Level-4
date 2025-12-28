"""
Party Room Touch Panel UI Module
* UI object definition
* Event handlers for Party Room control
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
dvPartyRoomTLP = devices.dvPartyRoomTLP

# ========================================================================================
# UI Object Definitions
# ========================================================================================

# System Control Buttons
BtnStart = Button(dvPartyRoomTLP, 8000)
BtnSystemPower = Button(dvPartyRoomTLP, 8022)
BtnPowerOffYes = Button(dvPartyRoomTLP, 9028)
BtnPowerOffCancel = Button(dvPartyRoomTLP, 9029)
BtnHelp = Button(dvPartyRoomTLP, 8117)
BtnHelpPageClose = Button(dvPartyRoomTLP, 9057)

# Room Control Buttons
PartyRoomCancelBtn = Button(dvPartyRoomTLP, 42)
PartyRoomMusicPlayerBtn = Button(dvPartyRoomTLP, 254)
PartyRoomBTPlateBtn = Button(dvPartyRoomTLP, 255)
PartyRoomMuteBtn = Button(dvPartyRoomTLP, 247)
PartyRoomVolumeLvl = Slider(dvPartyRoomTLP, 248)

# TV Power Buttons
PartyRoomTVPowerOnBtn = Button(dvPartyRoomTLP, 245)
PartyRoomTVPowerOffBtn = Button(dvPartyRoomTLP, 246)

# TV Audio Routing Buttons
PartyRoomTVAudioSendToAllBtn = Button(dvPartyRoomTLP, 253)
PartyRoomTVAudioSendToGymBtn = Button(dvPartyRoomTLP, 250)
PartyRoomTVAudioSendToYogaBtn = Button(dvPartyRoomTLP, 249)
PartyRoomTVAudioSendToTerraceBtn = Button(dvPartyRoomTLP, 251)
PartyRoomTVAudioSendToPartyRmBtn = Button(dvPartyRoomTLP, 252)
PartyRoomTVAudioSendToCourtyardBtn = Button(dvPartyRoomTLP, 256)

# Mutually Exclusive Button Sets
PartyRmAudioSource = MESet([PartyRoomMusicPlayerBtn, PartyRoomBTPlateBtn])
PartyRmTVPower = MESet([PartyRoomTVPowerOffBtn, PartyRoomTVPowerOnBtn])
PartyRmSendToMES = MESet([PartyRoomTVAudioSendToAllBtn, PartyRoomTVAudioSendToGymBtn, 
                          PartyRoomTVAudioSendToPartyRmBtn, PartyRoomTVAudioSendToTerraceBtn, 
                          PartyRoomTVAudioSendToYogaBtn, PartyRoomTVAudioSendToCourtyardBtn])

# ========================================================================================
# Event Handlers
# ========================================================================================

# System Control Events -----------------------------------------------------------------

@event(BtnStart, 'Pressed')
def BtnStartPressed(button, state):
    """Start system - navigate to main page and power on"""
    print('Party Room: Start button pressed')
    dvPartyRoomTLP.ShowPage(variables.PAGES['Main'])
    dvPartyRoomTLP.ShowPopup(variables.POPUPS['Starting Up'])
    
    def OnStartupComplete():
        dvPartyRoomTLP.HidePopup(variables.POPUPS['Starting Up'])
        print('Party Room: System startup complete')
    
    av.PartyRoomSystemPowerOn(callback=OnStartupComplete)

@event(BtnSystemPower, 'Pressed')
def BtnSystemPowerPressed(button, state):
    """Show power off confirmation popup"""
    print('Party Room: System Power button pressed')
    dvPartyRoomTLP.ShowPopup(variables.POPUPS['Confirmation'])

@event(BtnPowerOffYes, 'Pressed')
def BtnPowerOffYesPressed(button, state):
    """Confirm system shutdown"""
    print('Party Room: Power Off confirmed')
    dvPartyRoomTLP.HidePopup(variables.POPUPS['Confirmation'])
    dvPartyRoomTLP.ShowPopup(variables.POPUPS['Powering Down'])
    
    def OnShutdownComplete():
        dvPartyRoomTLP.HidePopup(variables.POPUPS['Powering Down'])
        dvPartyRoomTLP.ShowPage(variables.PAGES['Splash'])
        print('Party Room: System shutdown complete')
    
    av.PartyRoomSystemPowerOff(callback=OnShutdownComplete)

@event(BtnPowerOffCancel, 'Pressed')
def BtnPowerOffCancelPressed(button, state):
    """Cancel shutdown"""
    print('Party Room: Power Off cancelled')
    dvPartyRoomTLP.HidePopup(variables.POPUPS['Confirmation'])

@event(BtnHelp, 'Pressed')
def BtnHelpPressed(button, state):
    """Show help popup"""
    print('Party Room: Help button pressed')
    dvPartyRoomTLP.ShowPopup(variables.POPUPS['Help'])

@event(BtnHelpPageClose, 'Pressed')
def BtnHelpPageClosePressed(button, state):
    """Close help popup"""
    print('Party Room: Help page closed')
    dvPartyRoomTLP.HidePopup(variables.POPUPS['Help'])

@event(PartyRoomCancelBtn, 'Pressed')
def PartyRoomCancelBtnPressed(button, state):
    """Handle cancel/back navigation"""
    print('Party Room: Cancel button pressed')

# Audio Source Selection Events ---------------------------------------------------------

@event(PartyRoomMusicPlayerBtn, 'Pressed')
def PartyRoomMusicPlayerBtnPressed(button, state):
    """Select Music Player as audio source"""
    print('Party Room: Music Player selected')
    PartyRmAudioSource.SetCurrent(PartyRoomMusicPlayerBtn)
    av.PartyRoomSelectMusicPlayer()

@event(PartyRoomBTPlateBtn, 'Pressed')
def PartyRoomBTPlateBtnPressed(button, state):
    """Select Bluetooth Plate as audio source"""
    print('Party Room: Bluetooth Plate selected')
    PartyRmAudioSource.SetCurrent(PartyRoomBTPlateBtn)
    av.PartyRoomSelectBTPlate()

# Volume Control Events -----------------------------------------------------------------

@event(PartyRoomMuteBtn, 'Pressed')
def PartyRoomMuteBtnPressed(button, state):
    """Toggle mute state"""
    print('Party Room: Mute button pressed')
    newState = av.PartyRoomToggleMute()
    PartyRoomMuteBtn.SetState(1 if newState else 0)

@event(PartyRoomVolumeLvl, 'Changed')
def PartyRoomVolumeLvlChanged(slider, state, value):
    """Handle volume slider change"""
    print(f'Party Room: Volume changed to {value}')
    av.PartyRoomSetVolume(value)

# TV Power Control Events ---------------------------------------------------------------

@event(PartyRoomTVPowerOnBtn, 'Pressed')
def PartyRoomTVPowerOnBtnPressed(button, state):
    """Turn TV on"""
    print('Party Room: TV Power On pressed')
    PartyRmTVPower.SetCurrent(PartyRoomTVPowerOnBtn)
    av.PartyRoomTVPowerOn()

@event(PartyRoomTVPowerOffBtn, 'Pressed')
def PartyRoomTVPowerOffBtnPressed(button, state):
    """Turn TV off"""
    print('Party Room: TV Power Off pressed')
    PartyRmTVPower.SetCurrent(PartyRoomTVPowerOffBtn)
    av.PartyRoomTVPowerOff()

# TV Audio Routing Events ---------------------------------------------------------------

@event(PartyRoomTVAudioSendToAllBtn, 'Pressed')
def PartyRoomTVAudioSendToAllBtnPressed(button, state):
    """Route TV audio to all zones"""
    print('Party Room: Send TV Audio to All Zones')
    PartyRmSendToMES.SetCurrent(PartyRoomTVAudioSendToAllBtn)
    av.PartyRoomTVRouteToAll()

@event(PartyRoomTVAudioSendToGymBtn, 'Pressed')
def PartyRoomTVAudioSendToGymBtnPressed(button, state):
    """Route TV audio to Gym"""
    print('Party Room: Send TV Audio to Gym')
    PartyRmSendToMES.SetCurrent(PartyRoomTVAudioSendToGymBtn)
    av.PartyRoomTVRouteToGym()

@event(PartyRoomTVAudioSendToYogaBtn, 'Pressed')
def PartyRoomTVAudioSendToYogaBtnPressed(button, state):
    """Route TV audio to Yoga Studio"""
    print('Party Room: Send TV Audio to Yoga Studio')
    PartyRmSendToMES.SetCurrent(PartyRoomTVAudioSendToYogaBtn)
    av.PartyRoomTVRouteToYogaStudio()

@event(PartyRoomTVAudioSendToTerraceBtn, 'Pressed')
def PartyRoomTVAudioSendToTerraceBtnPressed(button, state):
    """Route TV audio to Terrace Gallery"""
    print('Party Room: Send TV Audio to Terrace')
    PartyRmSendToMES.SetCurrent(PartyRoomTVAudioSendToTerraceBtn)
    av.PartyRoomTVRouteToTerrace()

@event(PartyRoomTVAudioSendToPartyRmBtn, 'Pressed')
def PartyRoomTVAudioSendToPartyRmBtnPressed(button, state):
    """Route TV audio to Party Room only"""
    print('Party Room: Send TV Audio to Party Room')
    PartyRmSendToMES.SetCurrent(PartyRoomTVAudioSendToPartyRmBtn)
    av.PartyRoomTVRouteToPartyRoom()

@event(PartyRoomTVAudioSendToCourtyardBtn, 'Pressed')
def PartyRoomTVAudioSendToCourtyardBtnPressed(button, state):
    """Route TV audio to Courtyard"""
    print('Party Room: Send TV Audio to Courtyard')
    PartyRmSendToMES.SetCurrent(PartyRoomTVAudioSendToCourtyardBtn)
    av.PartyRoomTVRouteToCourtyard()