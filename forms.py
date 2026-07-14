from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    waiting_name = State()
    waiting_country = State()


class AdminCreateMatchState(StatesGroup):
    waiting_player1 = State()
    waiting_player2 = State()


class AdminBroadcastState(StatesGroup):
    waiting_message = State()
