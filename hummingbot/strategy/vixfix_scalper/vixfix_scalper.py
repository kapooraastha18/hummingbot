#!/usr/bin/env python

from decimal import Decimal
import logging
import pandas as pd
import numpy as np
from typing import Optional

from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.event.events import OrderFilledEvent
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.logger import HummingbotLogger
from hummingbot.strategy.strategy_py_base import StrategyPyBase

vfs_logger = None

class VixFixScalperStrategy(StrategyPyBase):
    @classmethod
    def logger(cls) -> HummingbotLogger:
        global vfs_logger
        if vfs_logger is None:
            vfs_logger = logging.getLogger(__name__)
        return vfs_logger

    def __init__(self,
                 market_info: MarketTradingPairTuple,
                 base_order_amount: Decimal = Decimal("0.001"),
                 profit_target_pct: Decimal = Decimal("0.003"),
                 initial_stop_loss_pct: Decimal = Decimal("0.005")):
        
        super().__init__()
        self._market_info = market_info
        self._base_order_amount = base_order_amount
        self._profit_target_pct = profit_target_pct
        self._initial_stop_loss_pct = initial_stop_loss_pct
        
        # Vix Fix parameters
        self.pd = 22  # LookBack Period Standard Deviation High
        self.bbl = 20  # Bolinger Band Length
        self.mult = 2.0  # Bollinger Band Standard Deviation Up
        self.lb = 50  # Look Back Period Percentile High
        self.ph = 0.85  # Highest Percentile
        self.pl = 1.01  # Lowest Percentile
        
        # Trading state
        self.in_position = False
        self.entry_price = Decimal("0")
        self.profit_target_price = Decimal("0")
        self.stop_loss_price = Decimal("0")
        self.consecutive_wins = 0
        self.price_history = []
        self.current_capital = Decimal("10000")  # Starting capital
        
        self.add_markets([market_info.market])

    def tick(self, timestamp: float):
        if not self._market_info.market.ready:
            self.logger().warning(f"{self._market_info.market.name} is not ready. Please wait...")
            return
        
        if not self.in_position and self.should_enter_long():
            self.enter_long()
        
        if self.in_position:
            self.check_exit_conditions()

    def should_enter_long(self) -> bool:
        try:
            # Get historical prices instead of candles
            current_price = self._market_info.get_mid_price()
            if not self.price_history:
                self.price_history.append(float(current_price))
                return False
                
            self.price_history.append(float(current_price))
            if len(self.price_history) > 100:  # Keep last 100 prices
                self.price_history = self.price_history[-100:]
                
            if len(self.price_history) < self.pd:
                return False
                
            # Convert price history to DataFrame
            df = pd.DataFrame(self.price_history, columns=['close'])
            df['high'] = df['close']
            df['low'] = df['close']
            df['open'] = df['close']
            
            # Calculate Williams Vix Fix
            highest_close = df['close'].rolling(window=self.pd).max()
            wvf = ((highest_close - df['low']) / highest_close) * 100
            
            # Calculate Bollinger Bands on WVF
            mid_line = wvf.rolling(window=self.bbl).mean()
            bb_std = wvf.rolling(window=self.bbl).std()
            upper_band = mid_line + (self.mult * bb_std)
            
            # Calculate percentile range
            range_high = wvf.rolling(window=self.lb).max() * self.ph
            
            # Get current values
            current_wvf = wvf.iloc[-1]
            current_upper_band = upper_band.iloc[-1]
            current_range_high = range_high.iloc[-1]
            
            # Entry conditions
            vix_signal = current_wvf >= current_upper_band or current_wvf >= current_range_high
            
            # Price confirmation using SMA
            sma_50 = df['close'].rolling(window=50).mean().iloc[-1]
            price_above_sma = float(current_price) > float(sma_50)
            
            return vix_signal and price_above_sma
            
        except Exception as e:
            self.logger().error(f"Error in should_enter_long: {str(e)}", exc_info=True)
            return False

    def enter_long(self):
        current_price = self._market_info.get_mid_price()
        order_amount = self._base_order_amount
        
        # Place buy order
        order_id = self.buy_with_specific_market(
            self._market_info,
            amount=order_amount,
            order_type=OrderType.LIMIT,
            price=current_price
        )
        
        if order_id is not None:
            self.in_position = True
            self.entry_price = current_price
            self.profit_target_price = current_price * (Decimal("1") + self._profit_target_pct)
            self.stop_loss_price = current_price * (Decimal("1") - self._initial_stop_loss_pct)
            
            self.logger().info(
                f"Entered long: Price={current_price:.2f}, "
                f"Amount={order_amount:.6f}, "
                f"Target={self.profit_target_price:.2f}, "
                f"Stop={self.stop_loss_price:.2f}"
            )

    def check_exit_conditions(self):
        current_price = self._market_info.get_mid_price()
        
        # Check profit target
        if current_price >= self.profit_target_price:
            self.exit_position("Profit target hit")
            self.consecutive_wins += 1
            return
            
        # Check stop loss
        if current_price <= self.stop_loss_price:
            self.exit_position("Stop loss triggered")
            self.consecutive_wins = 0
            return

    def exit_position(self, reason: str):
        if not self.in_position:
            return
            
        current_price = self._market_info.get_mid_price()
        base_balance = self._market_info.market.get_balance(self._market_info.base_asset)
        
        if base_balance > Decimal("0"):
            order_id = self.sell_with_specific_market(
                self._market_info,
                amount=base_balance,
                order_type=OrderType.LIMIT,
                price=current_price
            )
            
            if order_id is not None:
                pnl_pct = (current_price - self.entry_price) / self.entry_price
                self.logger().info(
                    f"Exited position: {reason}, "
                    f"Price={current_price:.2f}, "
                    f"PnL={pnl_pct*100:.2f}%"
                )
        
        self.in_position = False

    def did_complete_buy_order(self, event: OrderFilledEvent):
        self.logger().info(f"Buy order {event.order_id} filled at {event.price}")

    def did_complete_sell_order(self, event: OrderFilledEvent):
        self.logger().info(f"Sell order {event.order_id} filled at {event.price}")

    def format_status(self) -> str:
        if not self._market_info.market.ready:
            return "Market connector not ready."
            
        lines = []
        current_price = self._market_info.get_mid_price()
        
        # Basic status
        lines.extend([
            f"Trading pair: {self._market_info.trading_pair}",
            f"Current price: {current_price:.2f}",
            f"Base order amount: {self._base_order_amount}",
            "",
            "Strategy Settings:",
            f"Profit target: {self._profit_target_pct*100:.2f}%",
            f"Stop loss: {self._initial_stop_loss_pct*100:.2f}%",
            f"Consecutive wins: {self.consecutive_wins}",
            "",
        ])
        
        # Position information
        if self.in_position:
            unrealized_pnl = ((current_price - self.entry_price) / self.entry_price) * 100
            lines.extend([
                "Current Position:",
                f"Entry price: {self.entry_price:.2f}",
                f"Profit target: {self.profit_target_price:.2f}",
                f"Stop loss: {self.stop_loss_price:.2f}",
                f"Unrealized PnL: {unrealized_pnl:.2f}%",
            ])
        else:
            lines.append("No active position")
            
        return "\n".join(lines)
