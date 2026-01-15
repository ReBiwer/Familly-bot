from aiogram import Router

from .common import router as common_router
from .dialogs import profile_dialog

main_router = Router()

main_router.include_routers(*[common_router, profile_dialog])
