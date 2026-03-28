input_box = InputField(position=(0, 0.3), scale=(0.4, 0.05))
label = Text(text='Type destination airport code (BLR, ICN, HND):', position=(input_box.position[0] - 0.2, input_box.position[1] + 0.1), color=color.black)
submit_button = Button(text='Submit', position=(0, 0.2), scale=(0.1, 0.05), on_click=navigate)

speed = 0

