from decimal import Decimal
import logging
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd

from hummingbot.core.data_type.common import OrderType, PriceType, TradeType
from hummingbot.core.data_type.order_candidate import OrderCandidate
from hummingbot.strategy.market_making_strategy_base import MarketMakingStrategyBase
from hummingbot.core.event.events import OrderFilledEvent
from hummingbot.core.data_type.limit_order import LimitOrder
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.logger import HummingbotLogger

logger = None

class CMWilliamsVixMaker(MarketMakingStrategyBase):
    @classmethod
    def logger(cls) -> HummingbotLogger:
        global logger
        if logger is None:
            logger = logging.getLogger(__name__)
        return logger

    def __init__(self,
                 market_info: MarketTradingPairTuple,
                 min_spread: Decimal,
                 max_spread: Decimal,
                 order_amount: Decimal,
                 order_refresh_time: float = 30.0,
                 filled_order_delay: float = 60.0,
                 order_optimization_enabled: bool = False,
                 # VIX specific parameters
                 lookback_period: int = 22,
                 bb_length: int = 20,
                 bb_std: float = 2.0,
                 high_volatility_multiplier: Decimal = Decimal("1.5"),
                 low_volatility_multiplier: Decimal = Decimal("0.5"),
                 # Risk management parameters
                 max_position_size: Decimal = None,
                 stop_loss_spread: Decimal = Decimal("0.05"),
                 take_profit_spread: Decimal = Decimal("0.02"),
                 position_cooling_off: int = 300,
                 logging_options: int = 15,
                 status_report_interval: float = 900):
        super().__init__()
        self._market_info = market_info
        self._min_spread = min_spread
        self._max_spread = max_spread
        self._order_amount = order_amount
        self._order_refresh_time = order_refresh_time
        self._filled_order_delay = filled_order_delay
        self._order_optimization_enabled = order_optimization_enabled
        
        # VIX parameters
        self._lookback_period = lookback_period
        self._bb_length = bb_length
        self._bb_std = bb_std
        self._high_volatility_multiplier = high_volatility_multiplier
        self._low_volatility_multiplier = low_volatility_multiplier
        
        # Risk management
        self._max_position_size = max_position_size or (order_amount * Decimal("10"))
        self._stop_loss_spread = stop_loss_spread
        self._take_profit_spread = take_profit_spread
        self._position_cooling_off = position_cooling_off
        
        # Internal tracking
        self._price_history = []
        self._vix_history = []
        self._last_trade_price = None
        self._last_timestamp = 0
        self._logging_options = logging_options
        self._status_report_interval = status_report_interval
        self._last_position_check_timestamp = 0
        self._current_timestamp = 0
        
        self.add_markets([market_info.market])

    def calculate_cm_williams_vix(self) -> Tuple[float, bool]:
        """
        Calculate CM Williams VIX Fix indicator
        Returns: (vix_value, is_high_volatility)
        """
        try:
            if len(self._price_history) < self._lookback_period:
                return 0.0, False

            # Convert price history to numpy array for calculations
            prices = np.array(self._price_history[-self._lookback_period:])
            if len(prices) == 0:
                return 0.0, False

            highest_close = np.max(prices)
            if highest_close == 0:
                return 0.0, False

            current_low = prices[-1]

            # Calculate Williams VIX Fix
            wvf = ((highest_close - current_low) / highest_close) * 100

            # Calculate Bollinger Bands on VIX
            if len(self._vix_history) >= self._bb_length:
                vix_values = np.array(self._vix_history[-self._bb_length:])
                mid_line = np.mean(vix_values)
                std_dev = np.std(vix_values)
                upper_band = mid_line + (self._bb_std * std_dev)
                
                # Signal high volatility if WVF crosses above upper band
                is_high_volatility = wvf > upper_band
                
                self._vix_history.append(wvf)
                return float(wvf), is_high_volatility
            
            self._vix_history.append(wvf)
            return float(wvf), False
        except Exception as e:
            self.logger().error(f"Error calculating VIX: {str(e)}", exc_info=True)
            return 0.0, False

    def get_spread_multiplier(self, is_high_volatility: bool) -> Decimal:
        """Adjust spread based on volatility"""
        return self._high_volatility_multiplier if is_high_volatility else self._low_volatility_multiplier

    def get_price(self) -> Optional[Decimal]:
        """Get the current price safely"""
        try:
            price = self._market_info.get_mid_price()
            return price if price and price > Decimal('0') else None
        except Exception:
            return None

    def create_order_proposals(self) -> Tuple[List[OrderCandidate], List[OrderCandidate]]:
        """Create buy and sell proposals based on market making parameters and VIX readings"""
        if not self._market_info.market.ready:
            return [], []

        # Get reference price
        ref_price = self.get_price()
        if ref_price is None:
            return [], []

        try:
            # Update price history and calculate VIX
            self._price_history.append(float(ref_price))
            # Trim price history to prevent memory growth
            if len(self._price_history) > max(self._lookback_period * 2, self._bb_length * 2):
                self._price_history = self._price_history[-self._lookback_period:]
            
            vix, is_high_volatility = self.calculate_cm_williams_vix()
            
            # Adjust spread based on volatility
            spread_multiplier = self.get_spread_multiplier(is_high_volatility)
            adjusted_spread = min(
                max(self._min_spread * spread_multiplier, self._min_spread),
                self._max_spread
            )
            
            # Calculate order prices
            buy_price = ref_price * (Decimal("1") - adjusted_spread)
            sell_price = ref_price * (Decimal("1") + adjusted_spread)
            
            # Create proposals
            buy_proposals = []
            sell_proposals = []
            
            # Check position limits
            current_position = self._market_info.market.get_position(self._market_info.trading_pair)
            position_size = abs(current_position.amount) if current_position else Decimal("0")
            
            if position_size < self._max_position_size:
                # Create buy order
                buy_proposals.append(
                    OrderCandidate(
                        trading_pair=self._market_info.trading_pair,
                        is_maker=True,
                        order_type=OrderType.LIMIT,
                        order_side=TradeType.BUY,
                        amount=self._order_amount,
                        price=buy_price
                    )
                )
                
                # Create sell order
                sell_proposals.append(
                    OrderCandidate(
                        trading_pair=self._market_info.trading_pair,
                        is_maker=True,
                        order_type=OrderType.LIMIT,
                        order_side=TradeType.SELL,
                        amount=self._order_amount,
                        price=sell_price
                    )
                )
            
            return buy_proposals, sell_proposals
        except Exception as e:
            self.logger().error(f"Error creating proposals: {str(e)}", exc_info=True)
            return [], []

    def place_order(self, market_info, order_type, amount, order_type_str, price) -> str:
        """Place an order and return the order id"""
        try:
            if amount > 0 and price > 0:
                order_fn = self.buy_with_specific_market if order_type == TradeType.BUY else self.sell_with_specific_market
                return order_fn(
                    market_info,
                    amount,
                    order_type_str,
                    price
                )
        except Exception as e:
            self.logger().error(f"Error placing order: {str(e)}", exc_info=True)
        return ""

    def did_fill_order(self, event: OrderFilledEvent):
        """Handle order filled event for risk management"""
        try:
            super().did_fill_order(event)
            
            # Store last trade price for stop loss/take profit calculations
            self._last_trade_price = event.price
            
            # Create stop loss and take profit orders
            if event.trade_type == TradeType.BUY:
                stop_loss_price = event.price * (Decimal("1") - self._stop_loss_spread)
                take_profit_price = event.price * (Decimal("1") + self._take_profit_spread)
                
                # Place stop loss sell order
                self.place_order(
                    self._market_info,
                    TradeType.SELL,
                    event.amount,
                    OrderType.STOP,
                    stop_loss_price
                )
                
                # Place take profit sell order
                self.place_order(
                    self._market_info,
                    TradeType.SELL,
                    event.amount,
                    OrderType.LIMIT,
                    take_profit_price
                )
            else:  # SELL
                stop_loss_price = event.price * (Decimal("1") + self._stop_loss_spread)
                take_profit_price = event.price * (Decimal("1") - self._take_profit_spread)
                
                # Place stop loss buy order
                self.place_order(
                    self._market_info,
                    TradeType.BUY,
                    event.amount,
                    OrderType.STOP,
                    stop_loss_price
                )
                
                # Place take profit buy order
                self.place_order(
                    self._market_info,
                    TradeType.BUY,
                    event.amount,
                    OrderType.LIMIT,
                    take_profit_price
                )
        except Exception as e:
            self.logger().error(f"Error handling filled order: {str(e)}", exc_info=True)

    def check_and_cancel_active_orders(self):
        """Check and cancel active orders based on market conditions"""
        if not self.active_orders:
            return
        
        try:
            current_tick = self._current_timestamp
            vix, is_high_volatility = self.calculate_cm_williams_vix()
            
            for order in self.active_orders:
                # Cancel orders in high volatility if they've been active too long
                if is_high_volatility and (current_tick - order.timestamp) > self._order_refresh_time:
                    self.cancel_order(self._market_info, order.client_order_id)
                
                # Cancel orders if price moved significantly
                current_price = self.get_price()
                if current_price:
                    price_change = abs(order.price - current_price) / current_price
                    if price_change > self._stop_loss_spread:
                        self.cancel_order(self._market_info, order.client_order_id)
        except Exception as e:
            self.logger().error(f"Error checking active orders: {str(e)}", exc_info=True)

    def tick(self, timestamp: float):
        """
        Clock tick entry point.
        :param timestamp: current tick timestamp
        """
        try:
            super().tick(timestamp)
            
            # Store timestamp for internal logic
            self._current_timestamp = timestamp
            
            # Check and cancel active orders
            self.check_and_cancel_active_orders()
            
            # Create new order proposals
            self.process_tick()
            
            # Log status
            if self._should_report_status(timestamp):
                self.report_status()
        except Exception as e:
            self.logger().error(f"Error running tick: {str(e)}", exc_info=True)

    def _should_report_status(self, timestamp: float) -> bool:
        """Determine if status should be reported"""
        return (timestamp - self._last_timestamp) > self._status_report_interval

    def report_status(self):
        """Report strategy status"""
        if not self._market_info.market.ready:
            return

        try:
            # Get current market status
            active_orders = len(self.active_orders)
            current_price = self.get_price()
            position = self._market_info.market.get_position(self._market_info.trading_pair)
            position_size = position.amount if position else Decimal("0")
            
            # Calculate VIX status
            vix, is_high_volatility = self.calculate_cm_williams_vix()
            
            # Log status
            self.logger().info(f"""
                Strategy Status:
                Current price: {current_price}
                Active orders: {active_orders}
                Position size: {position_size}
                VIX value: {vix:.2f}
                High volatility: {is_high_volatility}
            """)
            
            self._last_timestamp = self._current_timestamp
        except Exception as e:
            self.logger().error(f"Error reporting status: {str(e)}", exc_info=True)
         
