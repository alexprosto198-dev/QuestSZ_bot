import os
import random
import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# In-memory storage for player states (can be connected to SQLite easily)
players = {}

# Monsters database
MONSTERS = [
    {"name": "Гоблин-разведчик", "hp": 25, "atk": 6, "img": "assets/goblin.png", "exp": 15, "gold": 10},
    {"name": "Проклятый Скелет", "hp": 40, "atk": 10, "img": "assets/skeleton.png", "exp": 25, "gold": 20},
    {"name": "Огненный Дракон", "hp": 85, "atk": 18, "img": "assets/dragon.png", "exp": 70, "gold": 80},
]

def get_player(user_id, username="Герой"):
    if user_id not in players:
        players[user_id] = {
            "name": username,
            "hp": 100,
            "max_hp": 100,
            "atk": 12,
            "potions": 3,
            "gold": 0,
            "floor": 1,
            "enemy": None,
            "in_battle": False
        }
    return players[user_id]

# --- Keyboards ---
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚪 Войти в следующую комнату", callback_data="explore")],
        [InlineKeyboardButton(text="🧪 Выпить зелье здоровья", callback_data="drink_potion")],
        [InlineKeyboardButton(text="👤 Профиль персонажа", callback_data="profile")]
    ])

def battle_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атаковать", callback_data="attack")],
        [InlineKeyboardButton(text="🛡️ Защита (-50% урона)", callback_data="defend")],
        [InlineKeyboardButton(text="🧪 Зелье (+35 HP)", callback_data="potion_battle")]
    ])

def restart_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Возродиться заново", callback_data="restart")]
    ])

# --- Handlers ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    p = get_player(message.from_user.id, message.from_user.first_name)
    photo = FSInputFile("assets/hero.png")
    text = (
        f"🏰 <b>Добро пожаловать в Подземелье, {p['name']}!</b>\n\n"
        f"Исследуй комнаты, сражайся с монстрами и собирай сокровища.\n"
        f"❤️ Здоровье: <b>{p['hp']}/{p['max_hp']}</b>\n"
        f"⚔️ Атака: <b>{p['atk']}</b>\n"
        f"🧪 Зелья: <b>{p['potions']}</b>\n"
        f"💰 Золото: <b>{p['gold']}</b>\n"
        f"📍 Комната (Этаж): <b>{p['floor']}</b>\n\n"
        f"<i>Что будешь делать?</i>"
    )
    await message.answer_photo(photo=photo, caption=text, parse_mode="HTML", reply_markup=main_menu_kb())

@dp.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery):
    p = get_player(call.from_user.id)
    text = (
        f"👤 <b>Статистика героя: {p['name']}</b>\n\n"
        f"❤️ HP: <b>{p['hp']}/{p['max_hp']}</b>\n"
        f"⚔️ Сила атаки: <b>{p['atk']}</b>\n"
        f"🧪 Зелий в сумке: <b>{p['potions']}</b>\n"
        f"💰 Монет: <b>{p['gold']}</b>\n"
        f"🚩 Пройдено комнат: <b>{p['floor']}</b>"
    )
    await call.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=main_menu_kb())
    await call.answer()

@dp.callback_query(F.data == "drink_potion")
async def cb_drink_potion(call: CallbackQuery):
    p = get_player(call.from_user.id)
    if p["potions"] <= 0:
        await call.answer("❌ Зелья закончились!", show_alert=True)
        return
    if p["hp"] >= p["max_hp"]:
        await call.answer("❤️ У тебя и так полное здоровье!", show_alert=True)
        return
    p["potions"] -= 1
    heal = 40
    p["hp"] = min(p["max_hp"], p["hp"] + heal)
    text = (
        f"🧪 Ты выпил зелье и восстановил <b>+{heal} HP</b>!\n\n"
        f"❤️ Здоровье: <b>{p['hp']}/{p['max_hp']}</b>\n"
        f"🧪 Осталось зелий: <b>{p['potions']}</b>"
    )
    await call.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=main_menu_kb())
    await call.answer()

@dp.callback_query(F.data == "explore")
async def cb_explore(call: CallbackQuery):
    p = get_player(call.from_user.id)
    if p["in_battle"]:
        await call.answer("Сначала завершите текущую битву!", show_alert=True)
        return
    
    p["floor"] += 1
    event = random.choice(["monster", "monster", "chest", "fountain"])

    if event == "chest":
        found_gold = random.randint(15, 40)
        p["gold"] += found_gold
        found_pot = random.random() < 0.4
        pot_text = ""
        if found_pot:
            p["potions"] += 1
            pot_text = "\n🧪 Также вы нашли лечебное зелье!"
        
        photo = FSInputFile("assets/chest.png")
        text = (
            f"🎁 <b>Комната {p['floor']}: Сундук с сокровищами!</b>\n\n"
            f"Ты открываешь сундук и находишь <b>+{found_gold} 💰</b>!{pot_text}\n\n"
            f"❤️ Твоё HP: <b>{p['hp']}/{p['max_hp']}</b> | Золото: <b>{p['gold']}</b>"
        )
        await call.message.delete()
        await call.message.answer_photo(photo=photo, caption=text, parse_mode="HTML", reply_markup=main_menu_kb())

    elif event == "fountain":
        p["hp"] = p["max_hp"]
        photo = FSInputFile("assets/hero.png")
        text = (
            f"⛲ <b>Комната {p['floor']}: Священный источник!</b>\n\n"
            f"Ты испил целебной воды и полностью восстановил здоровье!\n\n"
            f"❤️ Здоровье: <b>{p['hp']}/{p['max_hp']}</b>"
        )
        await call.message.delete()
        await call.message.answer_photo(photo=photo, caption=text, parse_mode="HTML", reply_markup=main_menu_kb())

    else: # monster
        # Pick monster according to floor
        if p["floor"] < 4:
            m_data = MONSTERS[0] # Goblin
        elif p["floor"] < 8:
            m_data = random.choice([MONSTERS[0], MONSTERS[1]])
        else:
            m_data = random.choice(MONSTERS)

        p["enemy"] = {
            "name": m_data["name"],
            "hp": m_data["hp"],
            "max_hp": m_data["hp"],
            "atk": m_data["atk"],
            "gold": m_data["gold"],
            "img": m_data["img"]
        }
        p["in_battle"] = True

        photo = FSInputFile(m_data["img"])
        text = (
            f"⚔️ <b>Комната {p['floor']}: Внезапная встреча!</b>\n\n"
            f"Перед тобой <b>{m_data['name']}</b>!\n"
            f"👾 HP монстра: <b>{m_data['hp']}</b> | Атака: <b>{m_data['atk']}</b>\n\n"
            f"❤️ Твоё HP: <b>{p['hp']}/{p['max_hp']}</b>\n"
            f"<i>Выбери действие:</i>"
        )
        await call.message.delete()
        await call.message.answer_photo(photo=photo, caption=text, parse_mode="HTML", reply_markup=battle_kb())
    await call.answer()

@dp.callback_query(F.data.in_(["attack", "defend", "potion_battle"]))
async def cb_battle_action(call: CallbackQuery):
    p = get_player(call.from_user.id)
    if not p["in_battle"] or not p["enemy"]:
        await call.answer("Битва уже окончена!")
        return

    e = p["enemy"]
    action = call.data
    log = []

    # Player turn
    if action == "attack":
        dmg = random.randint(p["atk"] - 3, p["atk"] + 4)
        e["hp"] -= dmg
        log.append(f"💥 Ты атаковал <b>{e['name']}</b> и нанёс <b>{dmg}</b> урона!")
    elif action == "defend":
        log.append("🛡️ Ты приготовился защищаться!")
    elif action == "potion_battle":
        if p["potions"] > 0:
            p["potions"] -= 1
            heal = 35
            p["hp"] = min(p["max_hp"], p["hp"] + heal)
            log.append(f"🧪 Ты выпил зелье и восстановил <b>+{heal} HP</b>!")
        else:
            await call.answer("❌ Зелья закончились!", show_alert=True)
            return

    # Check monster death
    if e["hp"] <= 0:
        p["in_battle"] = False
        p["gold"] += e["gold"]
        # slight attack boost reward
        if random.random() < 0.3:
            p["atk"] += 1
            log.append("✨ Твой меч стал острее (+1 к атаке)!")
        
        photo = FSInputFile("assets/hero.png")
        text = (
            f"🎉 <b>ПОБЕДА!</b>\n\n"
            f"Ты одолел чудовище <b>{e['name']}</b>!\n"
            f"Награда: <b>+{e['gold']} 💰</b> монет!\n\n"
            f"❤️ Здоровье: <b>{p['hp']}/{p['max_hp']}</b> | 💰 Монеты: <b>{p['gold']}</b>"
        )
        await call.message.delete()
        await call.message.answer_photo(photo=photo, caption=text, parse_mode="HTML", reply_markup=main_menu_kb())
        await call.answer()
        return

    # Enemy turn
    incoming_dmg = random.randint(e["atk"] - 2, e["atk"] + 3)
    if action == "defend":
        incoming_dmg = max(1, incoming_dmg // 2)
        log.append(f"🛡️ Твой блок снизил урон! <b>{e['name']}</b> нанёс лишь <b>{incoming_dmg}</b> урона.")
    else:
        log.append(f"🩸 <b>{e['name']}</b> атакует в ответ на <b>{incoming_dmg}</b> урона!")

    p["hp"] -= incoming_dmg

    # Check player death
    if p["hp"] <= 0:
        p["in_battle"] = False
        p["hp"] = 0
        photo = FSInputFile("assets/skeleton.png")
        text = (
            f"💀 <b>ТЫ ПОГИБ В БОЮ...</b>\n\n"
            f"<b>{e['name']}</b> оказался сильнее.\n"
            f"Ты дошёл до <b>{p['floor']} этажа</b> и собрал <b>{p['gold']} 💰</b> монет.\n\n"
            f"Хочешь начать заново?"
        )
        await call.message.delete()
        await call.message.answer_photo(photo=photo, caption=text, parse_mode="HTML", reply_markup=restart_kb())
        await call.answer()
        return

    # Battle continues
    text = (
        f"⚔️ <b>Битва с {e['name']}!</b>\n\n"
        + "\n".join(log) + "\n\n"
        f"👾 HP монстра: <b>{max(0, e['hp'])}/{e['max_hp']}</b>\n"
        f"❤️ Твоё HP: <b>{p['hp']}/{p['max_hp']}</b> | 🧪 Зелья: <b>{p['potions']}</b>"
    )
    await call.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=battle_kb())
    await call.answer()

@dp.callback_query(F.data == "restart")
async def cb_restart(call: CallbackQuery):
    user_id = call.from_user.id
    players[user_id] = {
        "name": call.from_user.first_name or "Герой",
        "hp": 100,
        "max_hp": 100,
        "atk": 12,
        "potions": 3,
        "gold": 0,
        "floor": 1,
        "enemy": None,
        "in_battle": False
    }
    await call.message.delete()
    await cmd_start(call.message)
    await call.answer()

async def main():
    print("Бот подземелий запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
