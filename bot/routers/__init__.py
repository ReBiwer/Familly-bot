from aiogram import Router

from .common import router as common_router

main_router = Router()

main_router.include_routers(*[common_router])
