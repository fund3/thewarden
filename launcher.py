import PySimpleGUI as sg
# Main Windows Launcher for APP

layout = [[
    sg.Text('Welcome to the WARden', font='Courier 12', text_color='blue')
], [sg.OK(), sg.Cancel()]]
# Create the Window
window = sg.Window('The WARden', layout)
# Event Loop to process "events"
while True:
    event, values = window.Read()
    if event in (None, 'Cancel'):
        break

window.Close()