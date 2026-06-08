"""
This is the place to put the modules for each UI in the system.  One module for each unique ui --
mirrored panels should be in the same file.
* UI object definition
* UI navigation

This file handles BOTH Terrace Gallery touch panels (mirrored configuration).
Both panels control the same devices and stay synchronized.
"""

# Extron Library imports
from extronlib import event
from extronlib.ui import Button, Slider

# Project imports
import devices
import variables
import control.av as av

# ========================================================================================
# Touch Panel Device Definitions (Mirrored Panels)
# ========================================================================================

dvTLP1 = devices.dvTerraceGalleryTLP1  # Terrace Gallery Touch Panel 1
dvTLP2 = devices.dvTerraceGalleryTLP2  # Terrace Gallery Touch Panel 2

# List of all mirrored touch panels for easy iteration
AllTouchPanels = [dvTLP1, dvTLP2]

# ========================================================================================
# UI Object Definitions - Panel 1
# ========================================================================================

#Main Control Buttons - Panel 1 --------------------------------------------------------

TLP1_BtnStart = Button(dvTLP1, 7002)
TLP1_BtnSystemPower = Button(dvTLP1, 8022)
TLP1_BtnPowerOffYes = Button(dvTLP1, 9028)
TLP1_BtnPowerOffCancel = Button(dvTLP1, 9029)
TLP1_BtnHelp = Button(dvTLP1, 8117)
TLP1_BtnHelpPageClose = Button(dvTLP1, 9057)

# Volume Control - Panel 1
TLP1_BtnMute = Button(dvTLP1, 4)
TLP1_VolumeSlider = Slider(dvTLP1, 5)

#TLP1_TerraceGalleryCancelBtn = Button(dvTLP1, 43)
TLP1_TerraceGalleryTV1PowerOnBtn = Button(dvTLP1, 257)
TLP1_TerraceGalleryTV1PowerOffBtn = Button(dvTLP1, 258)
TLP1_TerraceGalleryTV2PowerOnBtn = Button(dvTLP1, 269)
TLP1_TerraceGalleryTV2PowerOffBtn = Button(dvTLP1, 270)
TLP1_TerraceGalleryTV1AudioSendToAllBtn = Button(dvTLP1, 265)
TLP1_TerraceGalleryTV1AudioSendToGymBtn = Button(dvTLP1, 261)
TLP1_TerraceGalleryTV1AudioSendToYogaBtn = Button(dvTLP1, 262)
TLP1_TerraceGalleryTV1AudioSendToTerraceBtn = Button(dvTLP1, 263)
TLP1_TerraceGalleryTV1AudioSendToPartyRmBtn = Button(dvTLP1, 264)
TLP1_TerraceGalleryTV1AudioSendToCourtyardBtn = Button(dvTLP1, 268)
TLP1_TerraceGalleryTV2AudioSendToAllBtn = Button(dvTLP1, 273)
TLP1_TerraceGalleryTV2AudioSendToGymBtn = Button(dvTLP1, 259)
TLP1_TerraceGalleryTV2AudioSendToYogaBtn = Button(dvTLP1, 260)
TLP1_TerraceGalleryTV2AudioSendToTerraceBtn = Button(dvTLP1, 271)
TLP1_TerraceGalleryTV2AudioSendToPartyRmBtn = Button(dvTLP1, 272)
TLP1_TerraceGalleryTV2AudioSendToCourtyardBtn = Button(dvTLP1, 274)

# ========================================================================================
# UI Object Definitions - Panel 2
# ========================================================================================

#Main Control Buttons - Panel 2 --------------------------------------------------------

TLP2_BtnStart = Button(dvTLP2, 7002)
TLP2_BtnSystemPower = Button(dvTLP2, 8022)
TLP2_BtnPowerOffYes = Button(dvTLP2, 9028)
TLP2_BtnPowerOffCancel = Button(dvTLP2, 9029)
TLP2_BtnHelp = Button(dvTLP2, 8117)
TLP2_BtnHelpPageClose = Button(dvTLP2, 9057)

# Volume Control - Panel 2
TLP2_BtnMute = Button(dvTLP2, 4)
TLP2_VolumeSlider = Slider(dvTLP2, 5)

#TLP2_TerraceGalleryCancelBtn = Button(dvTLP2, 43)
TLP2_TerraceGalleryTV1PowerOnBtn = Button(dvTLP2, 257)
TLP2_TerraceGalleryTV1PowerOffBtn = Button(dvTLP2, 258)
TLP2_TerraceGalleryTV2PowerOnBtn = Button(dvTLP2, 269)
TLP2_TerraceGalleryTV2PowerOffBtn = Button(dvTLP2, 270)
TLP2_TerraceGalleryTV1AudioSendToAllBtn = Button(dvTLP2, 265)
TLP2_TerraceGalleryTV1AudioSendToGymBtn = Button(dvTLP2, 261)
TLP2_TerraceGalleryTV1AudioSendToYogaBtn = Button(dvTLP2, 262)
TLP2_TerraceGalleryTV1AudioSendToTerraceBtn = Button(dvTLP2, 263)
TLP2_TerraceGalleryTV1AudioSendToPartyRmBtn = Button(dvTLP2, 264)
TLP2_TerraceGalleryTV1AudioSendToCourtyardBtn = Button(dvTLP2, 268)
TLP2_TerraceGalleryTV2AudioSendToAllBtn = Button(dvTLP2, 273)
TLP2_TerraceGalleryTV2AudioSendToGymBtn = Button(dvTLP2, 259)
TLP2_TerraceGalleryTV2AudioSendToYogaBtn = Button(dvTLP2, 260)
TLP2_TerraceGalleryTV2AudioSendToTerraceBtn = Button(dvTLP2, 271)
TLP2_TerraceGalleryTV2AudioSendToPartyRmBtn = Button(dvTLP2, 272)
TLP2_TerraceGalleryTV2AudioSendToCourtyardBtn = Button(dvTLP2, 274)

# ========================================================================================
# Button Groups for Mirrored Panel Synchronization
# ========================================================================================

# Dictionary mapping button IDs to button pairs for synchronization
# Format: {button_id: (TLP1_button, TLP2_button)}
MirroredButtonPairs = {
    7002: (TLP1_BtnStart, TLP2_BtnStart),
    8022: (TLP1_BtnSystemPower, TLP2_BtnSystemPower),
    9028: (TLP1_BtnPowerOffYes, TLP2_BtnPowerOffYes),
    9029: (TLP1_BtnPowerOffCancel, TLP2_BtnPowerOffCancel),
    8117: (TLP1_BtnHelp, TLP2_BtnHelp),
    9057: (TLP1_BtnHelpPageClose, TLP2_BtnHelpPageClose),
    4: (TLP1_BtnMute, TLP2_BtnMute),
    #43: (TLP1_TerraceGalleryCancelBtn, TLP2_TerraceGalleryCancelBtn),
    257: (TLP1_TerraceGalleryTV1PowerOnBtn, TLP2_TerraceGalleryTV1PowerOnBtn),
    258: (TLP1_TerraceGalleryTV1PowerOffBtn, TLP2_TerraceGalleryTV1PowerOffBtn),
    269: (TLP1_TerraceGalleryTV2PowerOnBtn, TLP2_TerraceGalleryTV2PowerOnBtn),
    270: (TLP1_TerraceGalleryTV2PowerOffBtn, TLP2_TerraceGalleryTV2PowerOffBtn),
    265: (TLP1_TerraceGalleryTV1AudioSendToAllBtn, TLP2_TerraceGalleryTV1AudioSendToAllBtn),
    261: (TLP1_TerraceGalleryTV1AudioSendToGymBtn, TLP2_TerraceGalleryTV1AudioSendToGymBtn),
    262: (TLP1_TerraceGalleryTV1AudioSendToYogaBtn, TLP2_TerraceGalleryTV1AudioSendToYogaBtn),
    263: (TLP1_TerraceGalleryTV1AudioSendToTerraceBtn, TLP2_TerraceGalleryTV1AudioSendToTerraceBtn),
    264: (TLP1_TerraceGalleryTV1AudioSendToPartyRmBtn, TLP2_TerraceGalleryTV1AudioSendToPartyRmBtn),
    268: (TLP1_TerraceGalleryTV1AudioSendToCourtyardBtn, TLP2_TerraceGalleryTV1AudioSendToCourtyardBtn),
    273: (TLP1_TerraceGalleryTV2AudioSendToAllBtn, TLP2_TerraceGalleryTV2AudioSendToAllBtn),
    259: (TLP1_TerraceGalleryTV2AudioSendToGymBtn, TLP2_TerraceGalleryTV2AudioSendToGymBtn),
    260: (TLP1_TerraceGalleryTV2AudioSendToYogaBtn, TLP2_TerraceGalleryTV2AudioSendToYogaBtn),
    271: (TLP1_TerraceGalleryTV2AudioSendToTerraceBtn, TLP2_TerraceGalleryTV2AudioSendToTerraceBtn),
    272: (TLP1_TerraceGalleryTV2AudioSendToPartyRmBtn, TLP2_TerraceGalleryTV2AudioSendToPartyRmBtn),
    274: (TLP1_TerraceGalleryTV2AudioSendToCourtyardBtn, TLP2_TerraceGalleryTV2AudioSendToCourtyardBtn),
}

# Button lists for combined event handling
AllStartBtns = [TLP1_BtnStart, TLP2_BtnStart]
AllSystemPowerBtns = [TLP1_BtnSystemPower, TLP2_BtnSystemPower]
AllPowerOffYesBtns = [TLP1_BtnPowerOffYes, TLP2_BtnPowerOffYes]
AllPowerOffCancelBtns = [TLP1_BtnPowerOffCancel, TLP2_BtnPowerOffCancel]
AllHelpBtns = [TLP1_BtnHelp, TLP2_BtnHelp]
AllHelpPageCloseBtns = [TLP1_BtnHelpPageClose, TLP2_BtnHelpPageClose]
AllMuteBtns = [TLP1_BtnMute, TLP2_BtnMute]
AllVolumeSliders = [TLP1_VolumeSlider, TLP2_VolumeSlider]
#AllCancelBtns = [TLP1_TerraceGalleryCancelBtn, TLP2_TerraceGalleryCancelBtn]

# Register volume slider for DSP feedback (at module load time)
# Only register TLP1 - TLP2 will be synced via callbacks
av.RegisterVolumeSlider('TerraceGallery', TLP1_VolumeSlider)

# ========================================================================================
# Feedback Callbacks for Multi-Panel Synchronization
# ========================================================================================

def OnVolumeChanged(room, level):
    """Callback when volume changes from DSP feedback or other source"""
    if room == 'TerraceGallery':
        print(f'Terrace Gallery: Volume feedback - {level}')
        # Update TLP2 slider (TLP1 is updated by DSP feedback handler)
        TLP2_VolumeSlider.SetFill(level)

def OnMuteChanged(room, muted):
    """Callback when mute state changes from DSP feedback or other source"""
    if room == 'TerraceGallery':
        print(f'Terrace Gallery: Mute feedback - {muted}')
        # Update both mute buttons
        SyncButtonState(4, 1 if muted else 0)

# Register callbacks for state change notifications
av.RegisterUICallback('VolumeChanged', OnVolumeChanged)
av.RegisterUICallback('MuteChanged', OnMuteChanged)

AllTV1PowerOnBtns = [TLP1_TerraceGalleryTV1PowerOnBtn, TLP2_TerraceGalleryTV1PowerOnBtn]
AllTV1PowerOffBtns = [TLP1_TerraceGalleryTV1PowerOffBtn, TLP2_TerraceGalleryTV1PowerOffBtn]
AllTV2PowerOnBtns = [TLP1_TerraceGalleryTV2PowerOnBtn, TLP2_TerraceGalleryTV2PowerOnBtn]
AllTV2PowerOffBtns = [TLP1_TerraceGalleryTV2PowerOffBtn, TLP2_TerraceGalleryTV2PowerOffBtn]

AllTV1SendToAllBtns = [TLP1_TerraceGalleryTV1AudioSendToAllBtn, TLP2_TerraceGalleryTV1AudioSendToAllBtn]
AllTV1SendToGymBtns = [TLP1_TerraceGalleryTV1AudioSendToGymBtn, TLP2_TerraceGalleryTV1AudioSendToGymBtn]
AllTV1SendToYogaBtns = [TLP1_TerraceGalleryTV1AudioSendToYogaBtn, TLP2_TerraceGalleryTV1AudioSendToYogaBtn]
AllTV1SendToTerraceBtns = [TLP1_TerraceGalleryTV1AudioSendToTerraceBtn, TLP2_TerraceGalleryTV1AudioSendToTerraceBtn]
AllTV1SendToPartyRmBtns = [TLP1_TerraceGalleryTV1AudioSendToPartyRmBtn, TLP2_TerraceGalleryTV1AudioSendToPartyRmBtn]
AllTV1SendToCourtyardBtns = [TLP1_TerraceGalleryTV1AudioSendToCourtyardBtn, TLP2_TerraceGalleryTV1AudioSendToCourtyardBtn]

AllTV2SendToAllBtns = [TLP1_TerraceGalleryTV2AudioSendToAllBtn, TLP2_TerraceGalleryTV2AudioSendToAllBtn]
AllTV2SendToGymBtns = [TLP1_TerraceGalleryTV2AudioSendToGymBtn, TLP2_TerraceGalleryTV2AudioSendToGymBtn]
AllTV2SendToYogaBtns = [TLP1_TerraceGalleryTV2AudioSendToYogaBtn, TLP2_TerraceGalleryTV2AudioSendToYogaBtn]
AllTV2SendToTerraceBtns = [TLP1_TerraceGalleryTV2AudioSendToTerraceBtn, TLP2_TerraceGalleryTV2AudioSendToTerraceBtn]
AllTV2SendToPartyRmBtns = [TLP1_TerraceGalleryTV2AudioSendToPartyRmBtn, TLP2_TerraceGalleryTV2AudioSendToPartyRmBtn]
AllTV2SendToCourtyardBtns = [TLP1_TerraceGalleryTV2AudioSendToCourtyardBtn, TLP2_TerraceGalleryTV2AudioSendToCourtyardBtn]

# ========================================================================================
# Helper Functions for Mirrored Panel Synchronization
# ========================================================================================

def SyncButtonState(buttonId, state):
    """Synchronize button state across all mirrored panels"""
    if buttonId in MirroredButtonPairs:
        for btn in MirroredButtonPairs[buttonId]:
            btn.SetState(state)

def SyncAllPanelsShowPage(pageName):
    """Show the same page on all mirrored panels"""
    for tlp in AllTouchPanels:
        tlp.ShowPage(pageName)

def SyncAllPanelsShowPopup(popupName):
    """Show the same popup on all mirrored panels"""
    for tlp in AllTouchPanels:
        tlp.ShowPopup(popupName)

def SyncAllPanelsHidePopup(popupName):
    """Hide the same popup on all mirrored panels"""
    for tlp in AllTouchPanels:
        tlp.HidePopup(popupName)

def SyncTV1PowerButtons(activeBtn):
    """Sync TV1 power button states across both panels"""
    for btn in AllTV1PowerOnBtns:
        btn.SetState(1 if activeBtn in AllTV1PowerOnBtns else 0)
    for btn in AllTV1PowerOffBtns:
        btn.SetState(1 if activeBtn in AllTV1PowerOffBtns else 0)

def SyncTV2PowerButtons(activeBtn):
    """Sync TV2 power button states across both panels"""
    for btn in AllTV2PowerOnBtns:
        btn.SetState(1 if activeBtn in AllTV2PowerOnBtns else 0)
    for btn in AllTV2PowerOffBtns:
        btn.SetState(1 if activeBtn in AllTV2PowerOffBtns else 0)

def SyncTV1SendToButtons(activeBtnList):
    """Sync TV1 Send To button states across both panels"""
    allTV1SendToLists = [AllTV1SendToAllBtns, AllTV1SendToGymBtns, AllTV1SendToYogaBtns, 
                         AllTV1SendToTerraceBtns, AllTV1SendToPartyRmBtns, AllTV1SendToCourtyardBtns]
    for btnList in allTV1SendToLists:
        state = 1 if btnList == activeBtnList else 0
        for btn in btnList:
            btn.SetState(state)

def SyncTV2SendToButtons(activeBtnList):
    """Sync TV2 Send To button states across both panels"""
    allTV2SendToLists = [AllTV2SendToAllBtns, AllTV2SendToGymBtns, AllTV2SendToYogaBtns, 
                         AllTV2SendToTerraceBtns, AllTV2SendToPartyRmBtns, AllTV2SendToCourtyardBtns]
    for btnList in allTV2SendToLists:
        state = 1 if btnList == activeBtnList else 0
        for btn in btnList:
            btn.SetState(state)

# ========================================================================================
# Event Handlers
# ========================================================================================

# System Control Events -----------------------------------------------------------------

@event(AllStartBtns, 'Pressed')
def BtnStartPressed(button, state):
    """Start system - navigate to main page and power on both TVs"""
    print('Terrace Gallery: Start button pressed')
    SyncAllPanelsShowPage(variables.PAGES['Main'])
    SyncAllPanelsShowPopup(variables.POPUPS['Starting Up'])
    
    def OnStartupComplete():
        SyncAllPanelsHidePopup(variables.POPUPS['Starting Up'])
        print('Terrace Gallery: System startup complete')
    
    av.TerraceGallerySystemPowerOn(callback=OnStartupComplete)

@event(AllSystemPowerBtns, 'Pressed')
def BtnSystemPowerPressed(button, state):
    """Show power off confirmation popup"""
    print('Terrace Gallery: System Power button pressed')
    SyncAllPanelsShowPopup(variables.POPUPS['Confirmation'])

@event(AllPowerOffYesBtns, 'Pressed')
def BtnPowerOffYesPressed(button, state):
    """Confirm system shutdown"""
    print('Terrace Gallery: Power Off confirmed')
    SyncAllPanelsHidePopup(variables.POPUPS['Confirmation'])
    SyncAllPanelsShowPopup(variables.POPUPS['Powering Down'])
    
    def OnShutdownComplete():
        SyncAllPanelsHidePopup(variables.POPUPS['Powering Down'])
        SyncAllPanelsShowPage(variables.PAGES['Splash'])
        print('Terrace Gallery: System shutdown complete')
    
    av.TerraceGallerySystemPowerOff(callback=OnShutdownComplete)

@event(AllPowerOffCancelBtns, 'Pressed')
def BtnPowerOffCancelPressed(button, state):
    """Cancel shutdown"""
    print('Terrace Gallery: Power Off cancelled')
    SyncAllPanelsHidePopup(variables.POPUPS['Confirmation'])

@event(AllHelpBtns, 'Pressed')
def BtnHelpPressed(button, state):
    """Show help popup"""
    print('Terrace Gallery: Help button pressed')
    SyncAllPanelsShowPopup(variables.POPUPS['Help'])

@event(AllHelpPageCloseBtns, 'Pressed')
def BtnHelpPageClosePressed(button, state):
    """Close help popup"""
    print('Terrace Gallery: Help page closed')
    SyncAllPanelsHidePopup(variables.POPUPS['Help'])

# Volume Control Events -----------------------------------------------------------------

@event(AllMuteBtns, 'Pressed')
def BtnMutePressed(button, state):
    """Toggle mute state"""
    print('Terrace Gallery: Mute button pressed')
    newState = av.TerraceGalleryToggleMute()
    # Sync button state across both panels
    SyncButtonState(4, 1 if newState else 0)

@event(AllVolumeSliders, 'Changed')
def VolumeSliderChanged(slider, state, value):
    """Handle volume slider changes"""
    print(f'Terrace Gallery: Volume changed to {value}')
    # Sync slider value across both panels manually
    for otherSlider in AllVolumeSliders:
        if otherSlider != slider:
            otherSlider.SetFill(value)
    # Call AV control function with notifyUI=False to prevent feedback loop
    # (we already synced the sliders manually above)
    av.SetVolume('TerraceGallery', value, notifyUI=False)

#@event(AllCancelBtns, 'Pressed')
#def TerraceGalleryCancelBtnPressed(button, state):
#    """Handle cancel/back navigation"""
#    print('Terrace Gallery: Cancel button pressed')

# TV1 Power Control Events --------------------------------------------------------------

@event(AllTV1PowerOnBtns, 'Pressed')
def TerraceGalleryTV1PowerOnBtnPressed(button, state):
    """Turn TV1 on"""
    print('Terrace Gallery: TV1 Power On pressed')
    SyncTV1PowerButtons(button)
    av.TerraceGalleryTV1PowerOn()

@event(AllTV1PowerOffBtns, 'Pressed')
def TerraceGalleryTV1PowerOffBtnPressed(button, state):
    """Turn TV1 off"""
    print('Terrace Gallery: TV1 Power Off pressed')
    SyncTV1PowerButtons(button)
    av.TerraceGalleryTV1PowerOff()

# TV2 Power Control Events --------------------------------------------------------------

@event(AllTV2PowerOnBtns, 'Pressed')
def TerraceGalleryTV2PowerOnBtnPressed(button, state):
    """Turn TV2 on"""
    print('Terrace Gallery: TV2 Power On pressed')
    SyncTV2PowerButtons(button)
    av.TerraceGalleryTV2PowerOn()

@event(AllTV2PowerOffBtns, 'Pressed')
def TerraceGalleryTV2PowerOffBtnPressed(button, state):
    """Turn TV2 off"""
    print('Terrace Gallery: TV2 Power Off pressed')
    SyncTV2PowerButtons(button)
    av.TerraceGalleryTV2PowerOff()

# TV1 Audio Routing Events --------------------------------------------------------------

@event(AllTV1SendToAllBtns, 'Pressed')
def TerraceGalleryTV1AudioSendToAllBtnPressed(button, state):
    """Route TV1 audio to all zones"""
    print('Terrace Gallery: Send TV1 Audio to All Zones')
    SyncTV1SendToButtons(AllTV1SendToAllBtns)
    av.TerraceGalleryTV1RouteToAll()

@event(AllTV1SendToGymBtns, 'Pressed')
def TerraceGalleryTV1AudioSendToGymBtnPressed(button, state):
    """Route TV1 audio to Gym"""
    print('Terrace Gallery: Send TV1 Audio to Gym')
    SyncTV1SendToButtons(AllTV1SendToGymBtns)
    av.TerraceGalleryTV1RouteToGym()

@event(AllTV1SendToYogaBtns, 'Pressed')
def TerraceGalleryTV1AudioSendToYogaBtnPressed(button, state):
    """Route TV1 audio to Yoga Studio"""
    print('Terrace Gallery: Send TV1 Audio to Yoga Studio')
    SyncTV1SendToButtons(AllTV1SendToYogaBtns)
    av.TerraceGalleryTV1RouteToYogaStudio()

@event(AllTV1SendToTerraceBtns, 'Pressed')
def TerraceGalleryTV1AudioSendToTerraceBtnPressed(button, state):
    """Route TV1 audio to Terrace Gallery only"""
    print('Terrace Gallery: Send TV1 Audio to Terrace')
    SyncTV1SendToButtons(AllTV1SendToTerraceBtns)
    av.TerraceGalleryTV1RouteToTerrace()

@event(AllTV1SendToPartyRmBtns, 'Pressed')
def TerraceGalleryTV1AudioSendToPartyRmBtnPressed(button, state):
    """Route TV1 audio to Party Room"""
    print('Terrace Gallery: Send TV1 Audio to Party Room')
    SyncTV1SendToButtons(AllTV1SendToPartyRmBtns)
    av.TerraceGalleryTV1RouteToPartyRoom()

@event(AllTV1SendToCourtyardBtns, 'Pressed')
def TerraceGalleryTV1AudioSendToCourtyardBtnPressed(button, state):
    """Route TV1 audio to Courtyard"""
    print('Terrace Gallery: Send TV1 Audio to Courtyard')
    SyncTV1SendToButtons(AllTV1SendToCourtyardBtns)
    av.TerraceGalleryTV1RouteToCourtyard()

# TV2 Audio Routing Events --------------------------------------------------------------

@event(AllTV2SendToAllBtns, 'Pressed')
def TerraceGalleryTV2AudioSendToAllBtnPressed(button, state):
    """Route TV2 audio to all zones"""
    print('Terrace Gallery: Send TV2 Audio to All Zones')
    SyncTV2SendToButtons(AllTV2SendToAllBtns)
    av.TerraceGalleryTV2RouteToAll()

@event(AllTV2SendToGymBtns, 'Pressed')
def TerraceGalleryTV2AudioSendToGymBtnPressed(button, state):
    """Route TV2 audio to Gym"""
    print('Terrace Gallery: Send TV2 Audio to Gym')
    SyncTV2SendToButtons(AllTV2SendToGymBtns)
    av.TerraceGalleryTV2RouteToGym()

@event(AllTV2SendToYogaBtns, 'Pressed')
def TerraceGalleryTV2AudioSendToYogaBtnPressed(button, state):
    """Route TV2 audio to Yoga Studio"""
    print('Terrace Gallery: Send TV2 Audio to Yoga Studio')
    SyncTV2SendToButtons(AllTV2SendToYogaBtns)
    av.TerraceGalleryTV2RouteToYogaStudio()

@event(AllTV2SendToTerraceBtns, 'Pressed')
def TerraceGalleryTV2AudioSendToTerraceBtnPressed(button, state):
    """Route TV2 audio to Terrace Gallery only"""
    print('Terrace Gallery: Send TV2 Audio to Terrace')
    SyncTV2SendToButtons(AllTV2SendToTerraceBtns)
    av.TerraceGalleryTV2RouteToTerrace()

@event(AllTV2SendToPartyRmBtns, 'Pressed')
def TerraceGalleryTV2AudioSendToPartyRmBtnPressed(button, state):
    """Route TV2 audio to Party Room"""
    print('Terrace Gallery: Send TV2 Audio to Party Room')
    SyncTV2SendToButtons(AllTV2SendToPartyRmBtns)
    av.TerraceGalleryTV2RouteToPartyRoom()

@event(AllTV2SendToCourtyardBtns, 'Pressed')
def TerraceGalleryTV2AudioSendToCourtyardBtnPressed(button, state):
    """Route TV2 audio to Courtyard"""
    print('Terrace Gallery: Send TV2 Audio to Courtyard')
    SyncTV2SendToButtons(AllTV2SendToCourtyardBtns)
    av.TerraceGalleryTV2RouteToCourtyard()