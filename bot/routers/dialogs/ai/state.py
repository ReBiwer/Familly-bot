from aiogram.fsm.state import State, StatesGroup


class AgentChoiceSG(StatesGroup):
    choice_agent = State()
    default_agent = State()
