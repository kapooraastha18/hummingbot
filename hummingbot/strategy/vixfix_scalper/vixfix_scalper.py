from decimal import Decimal
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import logging

from hummingbot.core.data_type.limit_order import LimitOrder
from hummingbot.core.event.events import OrderType, OrderFilledEvent
from hummingbot.strategy.strategy_py_base import StrategyPyBase
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.logger import HummingbotLogger

logger = None

class VixFixScalperStrategy(StrategyPyBase):
    @classmethod
    def logger(cls) -> HummingbotLogger:
        global logger
        if logger is None:
            logger = logging.getLogger(__name__)
        return logger

    def __init__(
        self,
        market_info: MarketTradingPairTuple,
        base_order_amount: Decimal = Decimal("0.001"),
        profit_target_pct: Decimal = Decimal("0.003"),
        initial_stop_loss_pct: Decimal = Decimal("0.005")
    ):
        super().__init__()
        self._market_info = market_info
        self._base_order_amount = base_order_amount
        self._profit_target_pct = profit_target_pct
        self._initial_stop_loss_pct = initial_stop_loss_pct
        
        # VixFix Parameters
        self.pd = 22  # LookBack Period Standard Deviation High
        self.bbl = 20  # Bollinger Band Length
        self.mult = 2.0  # Bollinger Band Standard Deviation Up
        self.lb = 50  # Look Back Period Percentile High
        self.ph = 0.85  # Highest Percentile
        self.pl = 1.01  # Lowest Percentile
        
        # Dynamic Risk Management
        self.initial_portfolio_value = Decimal("10000")  # Starting capital
        self.current_portfolio_value = self.initial_portfolio_value
        self.consecutive_wins = 0
        self.base_risk_amount = Decimal("150")  # Initial risk amount $150
        self.max_risk_amount = Decimal("300")   # Maximum risk amount $300
        
        # PnL Tracking
        self.total_realized_pnl = Decimal("0")
        self.current_unrealized_pnl = Decimal("0")
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Trading state
        self.in_position = False
        self.entry_price = Decimal("0")
        self.profit_target_price = Decimal("0")
        self.stop_loss_price = Decimal("0")
        self.price_history = []
        self.last_volatility_check = 0
        
        self.add_markets([market_info.market])

    def tick(self, timestamp: float):
        if not self._market_info.market.ready:
            self.logger().warning(f"{self._market_info.market.name} is not ready. Please wait...")
            return
        
        # Update price history
        current_price = float(self._market_info.get_mid_price())
        self.price_history.append(current_price)
        if len(self.price_history) > 100:  # Keep last 100 prices
            self.price_history = self.price_history[-100:]
        
        if self.in_position:
            self.adjust_stop_loss()
            self.check_exit_conditions()
        elif self.should_enter_long():
            self.enter_long()

    def should_enter_long(self) -> bool:
        try:
            if len(self.price_history) < self.pd:
                return False
                
            # Convert price history to DataFrame
            df = pd.DataFrame(self.price_history, columns=['close'])
            df['high'] = df['close']
            df['low'] = df['close']
            
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
            current_price = self._market_info.get_mid_price()
            price_above_sma = float(current_price) > float(sma_50)
            
            return vix_signal and price_above_sma
            
        except Exception as e:
            self.logger().error(f"Error in should_enter_long: {str(e)}", exc_info=True)
            return False

    def adjust_stop_loss(self):
        try:
            if not self.in_position:
                return
                
            # Calculate Williams VIX Fix
            df = pd.DataFrame(self.price_history, columns=['close'])
            df['high'] = df['close']
            df['low'] = df['close']
            
            highest_close = df['close'].rolling(window=self.pd).max()
            wvf = ((highest_close - df['low']) / highest_close) * 100
            
            # Calculate Bollinger Bands on WVF
            mid_line = wvf.rolling(window=self.bbl).mean()
            bb_std = wvf.rolling(window=self.bbl).std()
            upper_band = mid_line + (self.mult * bb_std)
            
            current_wvf = wvf.iloc[-1]
            current_upper_band = upper_band.iloc[-1]
            
            # Calculate dynamic risk based on consecutive wins
            risk_amount = min(
                self.base_risk_amount * (Decimal("1") + Decimal("0.25") * self.consecutive_wins),
                self.max_risk_amount
            )
            
            # Calculate stop loss percentage based on risk amount
            stop_loss_pct = risk_amount / self.current_portfolio_value
            
            # Update stop loss price
            self.stop_loss_price = self.entry_price * (Decimal("1") - stop_loss_pct)
            self.logger().info(f"Adjusted stop loss to: {self.stop_loss_price:.2f} ({float(stop_loss_pct)*100:.2f}%)")
                
        except Exception as e:
            self.logger().error(f"Error adjusting stop loss: {str(e)}", exc_info=True)

    def enter_long(self):
        current_price = self._market_info.get_mid_price()
        
        # Calculate dynamic risk based on consecutive wins
        risk_amount = min(
            self.base_risk_amount * (Decimal("1") + Decimal("0.25") * self.consecutive_wins),
            self.max_risk_amount
        )
        
        # Calculate stop loss percentage based on risk amount
        stop_loss_pct = risk_amount / self.current_portfolio_value
        
        # Use existing order amount
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
            self.stop_loss_price = current_price * (Decimal("1") - stop_loss_pct)
            
            self.logger().info(
                f"Entered long: Price={current_price:.2f}, "
                f"Amount={order_amount:.6f}, "
                f"Target={self.profit_target_price:.2f}, "
                f"Stop={self.stop_loss_price:.2f}, "
                f"Risk=${float(risk_amount):.2f}, "
                f"Consecutive Wins={self.consecutive_wins}"
            )

    def check_exit_conditions(self):
        current_price = self._market_info.get_mid_price()
        
        # Update unrealized PnL
        if self.in_position:
            base_balance = self._market_info.market.get_balance(self._market_info.base_asset)
            self.current_unrealized_pnl = (current_price - self.entry_price) * base_balance
        
        # Check profit target
        if current_price >= self.profit_target_price:
            self.exit_position("Profit target hit")
            return
            
        # Check stop loss
        if current_price <= self.stop_loss_price:
            self.exit_position("Stop loss triggered")
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
                # Calculate PnL
                pnl = (current_price - self.entry_price) * base_balance
                pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
                
                # Update trading statistics
                self.total_realized_pnl += pnl
                self.total_trades += 1
                if pnl > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1
                
                # Update portfolio value and consecutive wins
                self.current_portfolio_value += pnl
                
                if current_price >= self.profit_target_price:
                    self.consecutive_wins += 1
                else:
                    self.consecutive_wins = 0
                
                self.logger().info(
                    f"Exited position: {reason}, "
                    f"Price={current_price:.2f}, "
                    f"PnL=${float(pnl):.2f} ({pnl_pct:.2f}%), "
                    f"Total Realized PnL=${float(self.total_realized_pnl):.2f}, "
                    f"Portfolio=${float(self.current_portfolio_value):.2f}, "
                    f"Consecutive Wins={self.consecutive_wins}"
                )
        
        self.in_position = False
        self.current_unrealized_pnl = Decimal("0")  # Reset unrealized PnL

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
            f"Portfolio value: ${float(self.current_portfolio_value):.2f}",
            "",
            "Performance Metrics:",
            f"Total Realized PnL: ${float(self.total_realized_pnl):.2f}",
            f"Current Unrealized PnL: ${float(self.current_unrealized_pnl):.2f}",
            f"Total Trades: {self.total_trades}",
            f"Win Rate: {(self.winning_trades/self.total_trades*100):.1f}% ({self.winning_trades}/{self.total_trades})" if self.total_trades > 0 else "Win Rate: N/A",
            f"Consecutive wins: {self.consecutive_wins}",
            "",
            "Strategy Settings:",
            f"Profit target: {self._profit_target_pct*100:.2f}%",
            f"Current risk: ${float(min(self.base_risk_amount * (Decimal('1') + Decimal('0.25') * self.consecutive_wins), self.max_risk_amount)):.2f}",
            "",
        ])
        
        # Position information
        if self.in_position:
            unrealized_pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
            lines.extend([
                "Current Position:",
                f"Entry price: {self.entry_price:.2f}",
                f"Profit target: {self.profit_target_price:.2f}",
                f"Stop loss: {self.stop_loss_price:.2f}",
                f"Unrealized PnL: ${float(self.current_unrealized_pnl):.2f} ({unrealized_pnl_pct:.2f}%)",
            ])
        else:
            lines.append("No active position")
            
        return "\n".join(lines)
