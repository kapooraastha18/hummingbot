from decimal import Decimal
import logging
import numpy as np
from typing import List, Tuple

from hummingbot.core.data_type.common import OrderType, PriceType, TradeType
from hummingbot.core.data_type.order_candidate import OrderCandidate
from hummingbot.strategy.market_making import MarketMakingStrategy
from hummingbot.strategy.market_making.market_making_config_map import MarketMakingConfigMap

logger = logging.getLogger(__name__)

class SimpleCMWilliamsVixMaker(MarketMakingStrategy):
    """
    A simplified implementation of the CM Williams VIX Fix market making strategy.
    This strategy adjusts bid/ask spreads based on market volatility.
    """
    
    @classmethod
    def get_config_map(cls) -> MarketMakingConfigMap:
        return MarketMakingConfigMap()

    def __init__(self,
                 exchange: str,
                 trading_pair: str,
                 order_amount: Decimal = Decimal("1.0"),
                 min_spread: Decimal = Decimal("0.01"),
                 max_spread: Decimal = Decimal("0.05"),
                 lookback_period: int = 20,
                 volatility_threshold: float = 1.5,
                 # Include all other required parameters from parent class
                 order_refresh_time: float = 30,
                 order_refresh_tolerance_pct: Decimal = Decimal("0.2"),
                 filled_order_delay: float = 60,
                 hanging_orders_enabled: bool = False,
                 hanging_orders_cancel_pct: Decimal = Decimal("10.0"),
                 order_optimization_enabled: bool = False,
                 ask_order_optimization_depth: Decimal = Decimal("0"),
                 bid_order_optimization_depth: Decimal = Decimal("0"),
                 add_transaction_costs_to_orders: bool = False,
                 price_ceiling: Decimal = Decimal("1000000"),
                 price_floor: Decimal = Decimal("0"),
                 ping_pong_enabled: bool = False,
                 logging_options: int = 3,
                 status_report_interval: float = 900,
                 minimum_spread: Decimal = Decimal("0.0")
                 ):
        # Initialize parent with all required parameters
        super().__init__(
            exchange=exchange,
            trading_pair=trading_pair,
            order_amount=order_amount,
            order_refresh_time=order_refresh_time,
            order_refresh_tolerance_pct=order_refresh_tolerance_pct,
            filled_order_delay=filled_order_delay,
            hanging_orders_enabled=hanging_orders_enabled,
            hanging_orders_cancel_pct=hanging_orders_cancel_pct,
            order_optimization_enabled=order_optimization_enabled,
            ask_order_optimization_depth=ask_order_optimization_depth,
            bid_order_optimization_depth=bid_order_optimization_depth,
            add_transaction_costs_to_orders=add_transaction_costs_to_orders,
            price_ceiling=price_ceiling,
            price_floor=price_floor,
            ping_pong_enabled=ping_pong_enabled,
            logging_options=logging_options,
            status_report_interval=status_report_interval,
            minimum_spread=minimum_spread
        )
        
        # Strategy-specific parameters
        self.min_spread = min_spread
        self.max_spread = max_spread
        self.lookback_period = lookback_period
        self.volatility_threshold = volatility_threshold
        
        # Price history
        self.price_history = []
        
    def update_price_history(self):
        """Add current mid price to price history"""
        mid_price = self.get_mid_price()
        if mid_price is not None:
            self.price_history.append(float(mid_price))
            # Keep only the most recent prices
            if len(self.price_history) > self.lookback_period:
                self.price_history = self.price_history[-self.lookback_period:]
    
    def get_mid_price(self) -> Decimal:
        """Get current mid price"""
        return self.market_info.get_mid_price()
    
    def calculate_volatility(self) -> float:
        """Calculate recent market volatility"""
        if len(self.price_history) < self.lookback_period:
            return 0.0
        
        # Simple volatility calculation (standard deviation / mean)
        prices = np.array(self.price_history[-self.lookback_period:])
        return float(np.std(prices) / np.mean(prices))
    
    def is_high_volatility(self) -> bool:
        """Determine if market is in high volatility state"""
        return self.calculate_volatility() > self.volatility_threshold
    
    def create_order_proposals(self) -> Tuple[List[OrderCandidate], List[OrderCandidate]]:
        """Create buy and sell order proposals based on volatility"""
        # Update price history
        self.update_price_history()
        
        # Determine spread based on volatility
        spread = self.max_spread if self.is_high_volatility() else self.min_spread
        
        # Get reference price
        mid_price = self.get_mid_price()
        if mid_price is None:
            return [], []
        
        # Calculate order prices
        buy_price = mid_price * (Decimal("1") - spread)
        sell_price = mid_price * (Decimal("1") + spread)
        
        # Create proposals
        buy_proposals = [OrderCandidate(
            trading_pair=self.trading_pair,
            is_maker=True,
            order_type=OrderType.LIMIT,
            order_side=TradeType.BUY,
            amount=self.order_amount,
            price=buy_price
        )]
        
        sell_proposals = [OrderCandidate(
            trading_pair=self.trading_pair,
            is_maker=True,
            order_type=OrderType.LIMIT,
            order_side=TradeType.SELL,
            amount=self.order_amount,
            price=sell_price
        )]
        
        return buy_proposals, sell_proposals
    
    # Override this method from parent class
    def create_proposal_based_on_order_levels(self) -> Tuple[List[OrderCandidate], List[OrderCandidate]]:
        return self.create_order_proposals()
    
    # Add any other required methods from the parent class here
    
    def log_with_clock(self, log_level: int, msg: str):
        """Log message with clock timestamp"""
        if log_level in (0, 1, 2, 3):
            logger.info(f"{msg}")
    
    def tick(self, timestamp: float):
        """Called on each clock tick"""
        super().tick(timestamp)
        
        # Log volatility info occasionally
        if self.price_history and len(self.price_history) >= self.lookback_period:
            volatility = self.calculate_volatility()
            state = "HIGH" if self.is_high_volatility() else "NORMAL"
            self.log_with_clock(
                1, 
                f"Volatility: {volatility:.4f}, State: {state}, " +
                f"Spread: {self.max_spread if self.is_high_volatility() else self.min_spread}"
            )
