from decimal import Decimal
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import logging
import asyncio

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
        
        # Paper Trading Settings
        self.paper_trade_enabled = True
        self.trading_pair = market_info.trading_pair
        self.exchange = market_info.market.name
        
        # Dynamic Risk Management
        self.initial_portfolio_value = Decimal("10000")  # Starting paper trading capital
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
        self._last_stop_loss = Decimal("0")
        self.price_history = []
        self.last_volatility_check = 0
        self._last_timestamp = 0
        self._ready_to_trade = False
        self._last_price_log = 0
        
        self.add_markets([market_info.market])

    def tick(self, timestamp: float):
        try:
            if timestamp - self._last_timestamp <= 1.0:
                return
            self._last_timestamp = timestamp
            
            if not self._ready_to_trade:
                if not self._market_info.market.ready:
                    self.logger().info(f"Waiting for {self._market_info.market.name} to be ready...")
                    return
                self._ready_to_trade = True
                self.logger().info(f"Paper trading started on {self._market_info.market.name} for {self.trading_pair}")
            
            # Safely get current price
            try:
                current_price = self._market_info.get_mid_price()
                if current_price is None or current_price == Decimal("0"):
                    self.logger().warning("Unable to get current price. Skipping tick.")
                    return
                    
                self.price_history.append(float(current_price))
                if len(self.price_history) > 100:
                    self.price_history = self.price_history[-100:]
                    
                # Log price updates every 30 seconds
                if timestamp - self._last_price_log >= 30:
                    self._last_price_log = timestamp
                    self.logger().info(f"Current {self.trading_pair} price: {current_price}")
                
                # Only proceed if we have enough price history
                if len(self.price_history) >= self.pd:
                    if not self.in_position:
                        if self.should_enter_long():
                            self.enter_long()
                    else:
                        self.adjust_stop_loss()
                        self.check_exit_conditions()
                else:
                    if timestamp - self._last_price_log >= 30:
                        self.logger().info(f"Building price history: {len(self.price_history)}/{self.pd}")
                    
            except Exception as price_error:
                self.logger().error(f"Error processing price data: {str(price_error)}", exc_info=True)
                
        except Exception as e:
            self.logger().error(f"Error in tick: {str(e)}", exc_info=True)

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
            
            if vix_signal and price_above_sma:
                self.logger().info(f"Entry signal detected - VIX: {current_wvf:.2f}, Upper Band: {current_upper_band:.2f}")
            
            return vix_signal and price_above_sma
            
        except Exception as e:
            self.logger().error(f"Error in should_enter_long: {str(e)}", exc_info=True)
            return False

    def adjust_stop_loss(self):
        try:
            if not self.in_position:
                return
                
            current_price = float(self._market_info.get_mid_price())
            
            # Calculate dynamic risk based on consecutive wins
            risk_amount = min(
                self.base_risk_amount * (Decimal("1") + Decimal("0.25") * self.consecutive_wins),
                self.max_risk_amount
            )
            
            # Calculate stop loss percentage (as a decimal)
            stop_loss_pct = float(risk_amount) / float(self.current_portfolio_value)
            
            # Update stop loss price
            self.stop_loss_price = self.entry_price * (Decimal("1") - Decimal(str(stop_loss_pct)))
            
            # Only log if stop loss has changed significantly
            if abs(float(self.stop_loss_price) - float(self._last_stop_loss)) > 0.01:
                self._last_stop_loss = self.stop_loss_price
                self.logger().info(f"Paper trade - Adjusted stop loss to: {self.stop_loss_price:.2f} ({stop_loss_pct*100:.2f}%)")
                
        except Exception as e:
            self.logger().error(f"Error adjusting stop loss: {str(e)}", exc_info=True)

    def enter_long(self):
        try:
            current_price = self._market_info.get_mid_price()
            
            # Calculate dynamic risk based on consecutive wins
            risk_amount = min(
                self.base_risk_amount * (Decimal("1") + Decimal("0.25") * self.consecutive_wins),
                self.max_risk_amount
            )
            
            # Calculate stop loss percentage based on risk amount
            stop_loss_pct = float(risk_amount) / float(self.current_portfolio_value)
            
            # Use existing order amount
            order_amount = self._base_order_amount
            
            # Paper trade - simulate buy order
            self.in_position = True
            self.entry_price = current_price
            self.profit_target_price = current_price * (Decimal("1") + self._profit_target_pct)
            self.stop_loss_price = current_price * (Decimal("1") - Decimal(str(stop_loss_pct)))
            self._last_stop_loss = self.stop_loss_price
            
            self.logger().info(
                f"Paper trade - Entered long: {self.trading_pair}\n"
                f"Price: ${float(current_price):.2f}\n"
                f"Amount: {float(order_amount):.6f}\n"
                f"Target: ${float(self.profit_target_price):.2f}\n"
                f"Stop: ${float(self.stop_loss_price):.2f}\n"
                f"Risk: ${float(risk_amount):.2f}"
            )
        except Exception as e:
            self.logger().error(f"Error entering long position: {str(e)}", exc_info=True)

    def check_exit_conditions(self):
        try:
            if not self.in_position:
                return

            current_price = self._market_info.get_mid_price()
            
            # Check stop loss
            if current_price <= self.stop_loss_price:
                self.exit_position("Stop loss hit")
                self.consecutive_wins = 0
                self.losing_trades += 1
                
            # Check profit target
            elif current_price >= self.profit_target_price:
                self.exit_position("Profit target reached")
                self.consecutive_wins += 1
                self.winning_trades += 1
        except Exception as e:
            self.logger().error(f"Error checking exit conditions: {str(e)}", exc_info=True)

    def exit_position(self, reason: str):
        try:
            if not self.in_position:
                return
                
            current_price = self._market_info.get_mid_price()
            
            # Paper trade - simulate sell order
            self.in_position = False
            pnl = (current_price - self.entry_price) * self._base_order_amount
            self.total_realized_pnl += pnl
            self.total_trades += 1
            
            self.logger().info(
                f"Paper trade - Exited position: {self.trading_pair}\n"
                f"Reason: {reason}\n"
                f"Exit Price: ${float(current_price):.2f}\n"
                f"PnL: ${float(pnl):.2f}\n"
                f"Total PnL: ${float(self.total_realized_pnl):.2f}\n"
                f"Win Rate: {self.winning_trades/self.total_trades*100:.1f}%"
            )
        except Exception as e:
            self.logger().error(f"Error exiting position: {str(e)}", exc_info=True)

    def format_status(self) -> str:
        if not self._ready_to_trade:
            return "Paper trading strategy initializing..."
        
        lines = []
        lines.append(f"\nPaper Trading Status: {self.trading_pair} on {self.exchange}")
        lines.append(f"Strategy state:")
        lines.append(f"  Ready to trade: {self._ready_to_trade}")
        lines.append(f"  Current position: {'In position' if self.in_position else 'No position'}")
        
        if len(self.price_history) > 0:
            current_price = self.price_history[-1]
            lines.append(f"  Current price: ${current_price:.2f}")
            lines.append(f"  Price history length: {len(self.price_history)}/{self.pd}")
        
        if self.in_position:
            lines.append(f"\nCurrent Trade:")
            lines.append(f"  Entry price: ${float(self.entry_price):.2f}")
            lines.append(f"  Stop loss: ${float(self.stop_loss_price):.2f}")
            lines.append(f"  Target: ${float(self.profit_target_price):.2f}")
        
        lines.append(f"\nPerformance:")
        lines.append(f"  Total trades: {self.total_trades}")
        lines.append(f"  Winning trades: {self.winning_trades}")
        lines.append(f"  Total PnL: ${float(self.total_realized_pnl):.2f}")
        
        return "\n".join(lines)
