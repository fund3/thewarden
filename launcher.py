import PySimpleGUI as sg
# Main Windows Launcher for APP
layout = [[
    sg.Text('Welcome to the WARden', font='Courier 12', text_color='blue')
], [sg.Button('Launch WARden Server')], [sg.Button('Check for Updates')],
          [sg.InputText()], [sg.Button('Exit')]]

# Create the Window
window = sg.Window('The WARden').Layout(layout)

# Readers on the Window
button_launch = window.Read()

# Event Loop to process "events"
while True:
    event, values = window.Read()
    if event in (None, 'Cancel'):
        break

window.Close()