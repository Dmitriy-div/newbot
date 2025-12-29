import os
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from dotenv import load_dotenv

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ================== НАСТРОЙКИ ==================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")

logging.basicConfig(level=logging.INFO)

# ================== GOOGLE SHEETS ==================

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json", scope
)

client = gspread.authorize(creds)
sheet = client.open(SPREADSHEET_NAME).sheet1

# ================== BOT ==================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================== FSM ==================

class Form(StatesGroup):
    date = State()
    type = State()
    amount = State()
    category = State()
    comment = State()

# ================== КНОПКИ ==================

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)

type_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Доход"), KeyboardButton(text="➖ Расход")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)

# ================== /start ==================

@dp.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! 👋\n\n"
        "Я бот учёта бюджета 💰\n"
        "Нажми /add чтобы добавить запись."
    )

# ================== /add ==================

@dp.message(F.text == "/add")
async def add_start(message: Message, state: FSMContext):
    await state.set_state(Form.date)
    await message.answer(
        "Введите дату в формате ДД.ММ.ГГГГ\n"
        "Или отправьте «сегодня»",
        reply_markup=cancel_kb
    )

# ================== ОТМЕНА ==================

@dp.message(F.text == "❌ Отмена")
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено ❌", reply_markup=None)

# ================== ДАТА ==================

@dp.message(Form.date)
async def process_date(message: Message, state: FSMContext):
    text = message.text.strip()

    if text.lower() == "сегодня":
        date = datetime.now().strftime("%d.%m.%Y")
    else:
        try:
            datetime.strptime(text, "%d.%m.%Y")
            date = text
        except ValueError:
            await message.answer("❗ Неверный формат даты. Попробуй ещё раз.")
            return

    await state.update_data(date=date)
    await state.set_state(Form.type)

    await message.answer(
        "Выберите тип:",
        reply_markup=type_kb
    )

# ================== ТИП ==================

@dp.message(Form.type)
async def process_type(message: Message, state: FSMContext):
    if message.text not in ["➕ Доход", "➖ Расход"]:
        await message.answer("Выберите кнопку 👇")
        return

    await state.update_data(type=message.text.replace("➕ ", "").replace("➖ ", ""))
    await state.set_state(Form.amount)

    await message.answer(
        "Введите сумму:",
        reply_markup=cancel_kb
    )

# ================== СУММА ==================

@dp.message(Form.amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введите число ❗")
        return

    await state.update_data(amount=amount)
    await state.set_state(Form.category)

    await message.answer(
        "Введите категорию:",
        reply_markup=cancel_kb
    )

# ================== КАТЕГОРИЯ ==================

@dp.message(Form.category)
async def process_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text)
    await state.set_state(Form.comment)

    await message.answer(
        "Комментарий (или «-»):",
        reply_markup=cancel_kb
    )

# ================== КОММЕНТАРИЙ + ЗАПИСЬ ==================

@dp.message(Form.comment)
async def process_comment(message: Message, state: FSMContext):
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

    await message.answer(
        "✅ Запись добавлена!\n\n"
        f"📅 {data['date']}\n"
        f"👤 {message.from_user.full_name}\n"
        f"📌 {data['type']}\n"
        f"💰 {data['amount']}\n"
        f"🏷 {data['category']}\n"
        f"💬 {message.text}",
        reply_markup=None
    )

    await state.clear()

# ================== RUN ==================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
