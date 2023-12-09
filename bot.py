import asyncio
import logging
import subprocess
import pandas as pd
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ContentType
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import config
from db.fuc import FuturesDataBase, Base

engine = create_engine('sqlite:///bot.db')

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

bot = Bot(token=config.api.telegram.get_secret_value())
admin = int(config.api.admin.get_secret_value())
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

process_dict = {}


@dp.message(Command('start'))
async def work(message: Message):
    if message.from_user.id == admin:
        await message.answer('/work - Показывает включенные пары \n'
                             '/not_work - Показывает выключенные пары \n'
                             '/start_futures - Запускает бота на неработающие пары \n'
                             '/stop_futures - Выключает пару и удаляет ее \n'
                             '/delete_futures - Удаляет неактивную пару \n'
                             'Отправка csv файла добавляет пары в бота \n')
    else:
        await message.answer('Вы не являетесь администратором.')


@dp.message(Command('work'))
async def work(message: Message):
    if message.from_user.id == admin:
        result = session.query(FuturesDataBase).filter_by(work=True).all()
        if len(result) == 0:
            await message.answer(f'Нет активных пар')
        for item in result:
            await message.answer(f'{item.pair}')
    else:
        await message.answer('Вы не являетесь администратором.')


@dp.message(Command('not_work'))
async def not_work(message: Message):
    if message.from_user.id == admin:
        result = session.query(FuturesDataBase).filter_by(work=False).all()
        if len(result) == 0:
            await message.answer(f'Нет неактивных пар')
        for item in result:
            await message.answer(f'{item.pair}')
    else:
        await message.answer('Вы не являетесь администратором.')


@dp.message(Command('start_futures'))
async def start_futures_bot(message: Message):
    if message.from_user.id == admin:

        result = session.query(FuturesDataBase).filter_by(work=False).all()
        with session as s:
            for item in result:
                command = [
                    'python',
                    f'{config.main_directory}/models.py',
                    f'{item.pair}',
                    f'{item.leverage}',
                    f'{item.value_usd}',
                    f'{item.make_long}',
                    f'{item.close_long}',
                    f'{item.make_short}',
                    f'{item.close_short}',
                ]
                process = subprocess.Popen(command)

                await message.answer(f'Я запустил пару {item.pair}')
                process_dict[item.pair] = process

                item.work = True

            s.commit()
    else:
        await message.answer('Вы не являетесь администратором.')


@dp.message(Command('delete_futures'))
async def stop(message: Message):
    if message.from_user.id == admin:
        result = session.query(FuturesDataBase).filter_by(work=False).all()
        await message.answer(f'{result}')
        if len(result) > 0:
            builder = InlineKeyboardBuilder()
            for item in result:
                builder.add(types.InlineKeyboardButton(
                    text=f'{item.pair}',
                    callback_data=f'pair_{item.pair}')
                    )

            await message.answer(
                    'Нажми на пару которую остановить',
                    reply_markup=builder.as_markup()
                    )
        else:
            await message.answer(
                'Нет неактивных фьючерсов'
            )
    else:
        await message.answer('Вы не являетесь администратором.')


@dp.message(Command('stop_futures'))
async def stop(message: Message):
    if message.from_user.id == admin:
        result = session.query(FuturesDataBase).filter_by(work=True).all()
        if len(result) > 0:
            builder = InlineKeyboardBuilder()
            for item in result:
                builder.add(types.InlineKeyboardButton(
                    text=f'{item.pair}',
                    callback_data=f'pair_{item.pair}')
                    )
            await message.answer(
                    'Нажми на пару которую остановить',
                    reply_markup=builder.as_markup()
                    )
        else:
            await message.answer(
                'Нет активных фьючерсов'
            )
    else:
        await message.answer('Вы не являетесь администратором.')


@dp.callback_query(F.data.startswith('pair_'))
async def callbacks_position(callback: types.CallbackQuery):
    pair = callback.data.split('_')[1]

    if pair in process_dict:
        process_dict[pair].terminate()

    element_to_delete = session.query(FuturesDataBase).filter_by(pair=pair).first()
    if element_to_delete is not None:
        session.delete(element_to_delete)

    await callback.message.answer(f'stopped {pair}')


@dp.message()
async def download_csv(message: Message):
    if message.from_user.id == admin:
        if message.content_type == ContentType.DOCUMENT:
            try:
                file_id = message.document.file_id
                file_info = await bot.get_file(file_id)
                file_path = file_info.file_path
                await bot.download_file(file_path, 'data.csv')

                df = pd.read_csv('data.csv')
                for index, row in df.iterrows():
                    future = FuturesDataBase(
                        pair=row['Pair'],
                        leverage=row['Leverage'],
                        value_usd=row['Value'],
                        make_long=row['Long_order'],
                        close_long=row['Long_stop'],
                        make_short=row['Short_price'],
                        close_short=row['Short_stop'],
                        work=False
                    )
                    session.add(future)
                    await message.answer(f'Добавлена пара {future.pair}')
            except Exception as e:
                await message.answer(f'Ошибка в файле {e}')
    else:
        await message.answer('Вы не являетесь администратором.')


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
