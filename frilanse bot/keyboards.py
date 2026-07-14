from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Доход", callback_data="income"),
        InlineKeyboardButton(text="➖ Расход", callback_data="expense")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
        InlineKeyboardButton(text="📊 История", callback_data="history")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить последнюю операцию", callback_data="undo")
    )
    return builder.as_markup()

def categories_kb(operation_type: str):
    categories = {
        "income": ["Зарплата", "Фриланс", "Инвестиции", "Подарки", "Другое"],
        "expense": ["Еда", "Транспорт", "Жильё", "Здоровье", "Развлечения", "Одежда", "Другое"]
    }
    builder = InlineKeyboardBuilder()
    for cat in categories.get(operation_type, []):
        builder.add(InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}"))
    builder.adjust(2)
    return builder.as_markup()

def back_to_menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="menu")]
        ]
    )

def history_filter_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Сегодня", callback_data="hist_today"),
        InlineKeyboardButton(text="📆 Неделя", callback_data="hist_week"),
        InlineKeyboardButton(text="📅 Месяц", callback_data="hist_month")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Всё время", callback_data="hist_all")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="menu")
    )
    return builder.as_markup()