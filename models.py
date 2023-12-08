from typing import Tuple
import numpy as np
import time
from binance import Client
from config import api

api_key = api.key.get_secret_value()
api_secret = api.secret.get_secret_value()

binance = Client(api_key=api_key, api_secret=api_secret)


def round_down(number, decimals=0):
    factor = 10 ** decimals
    return np.floor(number * factor) / factor


class FuturesObj:
    def __init__(self, pair, leverage, value_usd, make_long, close_long, make_short, close_short):

        self.pair = pair
        self.leverage = leverage
        self.value_usd = value_usd
        self.make_long = make_long
        self.close_long = close_long
        self.make_short = make_short
        self.close_short = close_short

        self.precision = self.get_precision()
        self.work = False
        self.change_position_settings()

    def get_precision(self) -> int:
        exchange_info = binance.futures_exchange_info()
        precision = None

        for symbol_info in exchange_info['symbols']:
            if symbol_info['symbol'] == self.pair:
                precision = symbol_info['quantityPrecision']

        return int(precision)

    def change_position_settings(self):

        # Change leverage
        binance.futures_change_leverage(symbol=self.pair, leverage=self.leverage)

        # Change margin_type
        position_margin = self.get_position()['marginType']
        if position_margin != 'cross':
            binance.futures_change_margin_type(symbol=self.pair, marginType='CROSSED')

    def get_position(self):
        positions = binance.futures_position_information()
        for position in positions:
            if position['symbol'] == self.pair:
                return position

    def check_position(self):
        while True:
            position = self.get_position()
            if float(position['entryPrice']) <= 0:
                self.check_balance()

            time.sleep(5)

    def check_balance(self):
        while True:
            ticker = binance.get_symbol_ticker(symbol=self.pair)
            price = float(ticker['price'])

            if price >= self.make_long:
                self.open_position(price, ('BUY', 'SELL'))
                time.sleep(5)
                self.check_position()

            if price <= self.make_short:
                self.open_position(price, ('SELL', 'BUY'))
                time.sleep(5)
                self.check_position()

            time.sleep(0.1)

    def open_position(self, price: float, side: Tuple[str, str]):
        # Get quantity
        if self.precision != 0:
            quantity = round_down((self.value_usd / price * self.leverage), self.precision)
        else:
            quantity = int(self.value_usd / price * self.leverage)

        # Open position
        binance.futures_create_order(symbol=self.pair,
                                     side=side[0],
                                     type='MARKET',
                                     quantity=quantity)

        position = 'long' if side[0] == 'BUY' else 'short'
        print(f'Open {position} {self.pair}')

        # Stop loss
        close_price = self.close_long if side[0] == 'BUY' else self.close_short
        binance.futures_create_order(symbol=self.pair,
                                     side=side[1],
                                     type='STOP_MARKET',
                                     stopPrice=close_price,
                                     closePosition=True)


if __name__ == '__main__':
    inp = input().split()
    future = FuturesObj(
                    pair=inp[0],
                    leverage=int(inp[1]),
                    value_usd=float(inp[2]),
                    make_long=float(inp[3]),
                    close_long=float(inp[4]),
                    make_short=float(inp[5]),
                    close_short=float(inp[6]),
                )

    attempts = 0
    while attempts < 5:
        try:
            future.check_position()
            break
        except Exception as e:
            print(f'Error: {e} New connection attempt {future.pair}')
            attempts += 1
            time.sleep(15)
