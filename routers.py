from fastapi import APIRouter

from user.routers import router as auth_router
from words.routers import category_router, words_router
# from slide.views import router as slide_router
# from worker.views import router as worker_router
# from connect.views import router as connect_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix='', tags=['Auth'])
api_router.include_router(category_router, prefix='', tags=['Categories'])
api_router.include_router(words_router, prefix='', tags=['Words'])
# api_router.include_router(slide_router, prefix='', tags=['Slide'])
# api_router.include_router(worker_router, prefix='', tags=['Worker'])
# api_router.include_router(connect_router, prefix='', tags=['Connect'])