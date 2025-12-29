import asyncio
import os
import json
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

import gspread
from google.oauth2.service_account import Credentials

# =======================
# ENV
# =======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not all([BOT_TOKEN, SPREADSHEET_NAME, GOOGLE_CREDENTIALS_JSON]):
    raise RuntimeError("ENV variables are not set")

# =======================
# Google Sheets
# =======================
creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials = Credentials.from_service_account_info(
    creds_dict,
    scopes=scopes
)

gc = gspread.authorize(credentials)
sheet = gc.open(SPREADSHEET_NAME).sheet1

# =======================
# Bot
# =======================
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# =======================
# States
# =======================
class Form(StatesGroup):
    date = State()
    type = State()
    amount = State()
    category = State()
    comment = State()

# =======================
# Keyboards
# =======================
cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)

type_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Доход"), KeyboardButton(text="➖ Расход")],
        [KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)

# =======================
# Handlers
# =======================
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет 👋\nВведи дату в формате ДД.ММ.ГГГГ",
        reply_markup=cancel_kb
    )
    await state.set_state(Form.date)


@dp.message(Form.date)
async def get_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Действие отменено", reply_markup=types.ReplyKeyboardRemove())
        return

    try:
        date = datetime.strptime(message.text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("Неверный формат даты. Пример: 25.12.2025")
        return

    await state.update_data(date=str(date))
    await message.answer("Выбери тип:", reply_markup=type_kb)
    await state.set_state(Form.type)


@dp.message(Form.type)
async def get_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=types.ReplyKeyboardRemove())
        return

    if message.text == "⬅️ Назад":
        await message.answer("Введи дату:")
        await state.set_state(Form.date)
        return

    if message.text not in ["➕ Доход", "➖ Расход"]:
        await message.answer("Выбери кнопкой")
        return

    await state.update_data(type=message.text.replace("➕ ", "").replace("➖ ", ""))
    await message.answer("Введи сумму:")
    await state.set_state(Form.amount)


@dp.message(Form.amount)
async def get_amount(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=types.ReplyKeyboardRemove())
        return

    try:
        amount = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи число")
        return

    await state.update_data(amount=amount)
    await message.answer("Категория:")
    await state.set_state(Form.category)


@dp.message(Form.category)
async def get_category(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=types.ReplyKeyboardRemove())
        return

    await state.update_data(category=message.text)
    await message.answer("Комментарий (или '-'):")
    await state.set_state(Form.comment)


@dp.message(Form.comment)
async def finish(message: types.Message, state: FSMContext):
    data = await state.get_data()

    row = [
        data["date"],
        message.from_user.full_name,
        data["type"],
        data["amount"],
        data["category"],
        message.text
    ]

    sheet.append_row(row)

    await state.clear()
    await message.answer(
        "✅ Запись сохранена",
        reply_markup=types.ReplyKeyboardRemove()
    )


# =======================
# Main
# =======================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
