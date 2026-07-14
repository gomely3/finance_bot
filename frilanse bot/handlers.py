from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from decimal import Decimal

from database import AsyncSessionLocal, User, Operation
from states import FinanceStates
from keyboards import (
    main_menu_kb, categories_kb, back_to_menu_kb, history_filter_kb
)
from utils import format_currency

router = Router()

# ---- Регистрация / Старт ----
@router.message(F.text == "/start")
async def cmd_start(message: Message):
    async with AsyncSessionLocal() as session:
        user = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = user.scalar_one_or_none()
        if not user:
            new_user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            session.add(new_user)
            await session.commit()
            await message.answer("👋 Добро пожаловать! Бот для учета финансов создан.")
        else:
            await message.answer("👋 С возвращением!")
    await show_menu(message)

async def show_menu(message: Message):
    await message.answer(
        "📌 *Главное меню*\nВыберите действие:",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown"
    )

# ---- Главное меню (callback) ----
@router.callback_query(F.data == "menu")
async def callback_menu(callback: CallbackQuery):
    await callback.message.delete()
    await show_menu(callback.message)
    await callback.answer()

# ---- Добавление дохода/расхода ----
@router.callback_query(F.data.in_(["income", "expense"]))
async def callback_add_operation(callback: CallbackQuery, state: FSMContext):
    op_type = "income" if callback.data == "income" else "expense"
    await state.update_data(op_type=op_type)
    await state.set_state(FinanceStates.waiting_for_amount)
    await callback.message.delete()
    await callback.message.answer(
        f"✏️ Введите сумму *{ 'дохода' if op_type == 'income' else 'расхода' }* (в рублях):",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(FinanceStates.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше нуля. Попробуйте снова:")
            return
        await state.update_data(amount=amount)
        data = await state.get_data()
        await state.set_state(FinanceStates.waiting_for_category)
        await message.answer(
            "📂 Выберите категорию:",
            reply_markup=categories_kb(data["op_type"])
        )
    except ValueError:
        await message.answer("❌ Введите число (например, 1500.50). Попробуйте снова:")

@router.callback_query(F.data.startswith("cat_"), FinanceStates.waiting_for_category)
async def process_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.replace("cat_", "")
    await state.update_data(category=category)
    await state.set_state(FinanceStates.waiting_for_description)
    await callback.message.delete()
    await callback.message.answer(
        "📝 Введите описание (или отправьте '-' чтобы пропустить):"
    )
    await callback.answer()

@router.message(FinanceStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    description = message.text if message.text != "-" else None
    data = await state.get_data()
    
    async with AsyncSessionLocal() as session:
        user = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = user.scalar_one()
        
        operation = Operation(
            user_id=user.id,
            type=data["op_type"],
            amount=data["amount"],
            category=data["category"],
            description=description
        )
        session.add(operation)
        await session.commit()
    
    await state.clear()
    await message.answer(
        f"✅ Операция добавлена!\n"
        f"{'💰 Доход' if data['op_type'] == 'income' else '💸 Расход'}: {data['amount']:.2f} руб.\n"
        f"Категория: {data['category']}\n"
        f"Описание: {description or '—'}"
    )
    await show_menu(message)

# ---- Баланс ----
@router.callback_query(F.data == "balance")
async def callback_balance(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        user = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = user.scalar_one()
        
        total_income = await session.scalar(
            select(func.sum(Operation.amount))
            .where(Operation.user_id == user.id, Operation.type == "income")
        ) or 0.0
        
        total_expense = await session.scalar(
            select(func.sum(Operation.amount))
            .where(Operation.user_id == user.id, Operation.type == "expense")
        ) or 0.0
        
        balance = total_income - total_expense
        
    await callback.message.delete()
    await callback.message.answer(
        f"💰 *Ваш баланс:*\n"
        f"Доходы: +{total_income:.2f} руб.\n"
        f"Расходы: −{total_expense:.2f} руб.\n"
        f"━━━━━━━━━━━━━\n"
        f"Итого: *{balance:.2f} руб.*",
        reply_markup=back_to_menu_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ---- История ----
@router.callback_query(F.data == "history")
async def callback_history(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "📊 Выберите период для истории:",
        reply_markup=history_filter_kb()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("hist_"))
async def callback_history_filter(callback: CallbackQuery):
    period = callback.data.replace("hist_", "")
    now = datetime.utcnow()
    date_from = None
    
    if period == "today":
        date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        date_from = now - timedelta(days=7)
    elif period == "month":
        date_from = now - timedelta(days=30)
    # "all" - без фильтрации
    
    async with AsyncSessionLocal() as session:
        user = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = user.scalar_one()
        
        query = select(Operation).where(Operation.user_id == user.id)
        if date_from:
            query = query.where(Operation.date >= date_from)
        query = query.order_by(Operation.date.desc()).limit(20)
        
        operations = await session.execute(query)
        operations = operations.scalars().all()
    
    if not operations:
        await callback.message.answer("📭 Операций за выбранный период нет.", reply_markup=back_to_menu_kb())
        await callback.answer()
        return
    
    text = "📋 *История операций (последние 20):*\n\n"
    for op in operations:
        sign = "+" if op.type == "income" else "-"
        text += (
            f"{op.date.strftime('%d.%m.%Y %H:%M')} | "
            f"{sign}{op.amount:.2f} руб. | "
            f"{op.category} | {op.description or '—'}\n"
        )
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="Markdown")
    await callback.answer()

# ---- Удаление последней операции ----
@router.callback_query(F.data == "undo")
async def callback_undo(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        user = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = user.scalar_one()
        
        last_op = await session.execute(
            select(Operation)
            .where(Operation.user_id == user.id)
            .order_by(Operation.created_at.desc())
            .limit(1)
        )
        last_op = last_op.scalar_one_or_none()
        
        if not last_op:
            await callback.message.answer(
                "❌ Нет операций для удаления.",
                reply_markup=back_to_menu_kb()
            )
            await callback.answer()
            return
        
        await session.delete(last_op)
        await session.commit()
    
    await callback.message.delete()
    await callback.message.answer(
        f"🗑 Удалена последняя операция:\n"
        f"{'💰 Доход' if last_op.type == 'income' else '💸 Расход'} "
        f"{last_op.amount:.2f} руб. ({last_op.category})",
        reply_markup=back_to_menu_kb()
    )
    await callback.answer()