from aiogram.fsm.state import State, StatesGroup

class UpdateProfileSG(StatesGroup):
    main_menu = State()
    input_mid_name = State()
    input_last_name = State()
    input_phone = State()
    input_email = State()
