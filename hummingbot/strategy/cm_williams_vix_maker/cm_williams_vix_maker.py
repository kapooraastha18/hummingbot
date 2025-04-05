from decimal import Decimal
import logging
from typing import Dict, List
import numpy as np
from hummingbot.core.data_type.common import OrderType, PriceType, TradeType
from hummingbot.strategy.market_making import MarketMakingStrategy
from hummingbot.strategy.market_making.market_making_config_map import MarketMakingConfigMap

logger = logging.getLogger(__name__)

class CMWilliamsVixMaker(MarketMakingStrategy):
    @classmethod
    def get_config_map(cls) -> MarketMakingConfigMap:
        return MarketMakingConfigMap()

    def __init__(self,
                 exchange: str,
                 trading_pair: str,
                 lookback_period_sd: int = 22,
                 bb_length: int = 20,
                 bb_std: float = 2.0,
                 lookback_period_percentile: int = 50,
                 high_percentile: float = 0.85,
                 low_percentile: float = 1.01,
                 order_amount: Decimal = Decimal("1.0"),
                 min_spread: Decimal = Decimal("0.01"),
                 max_spread: Decimal = Decimal("0.05"),
                 # ... other parameters from our previous implementation
                 ):
        super().__init__(exchange=exchange,
                        trading_pair=trading_pair,
                        order_amount=order_amount,
                        # ... other parameters)
        
        # CM Williams VIX Fix parameters
        self.lookback_period_sd = lookback_period_sd
        self.bb_length = bb_length
        self.bb_std = bb_std
        self.lookback_period_percentile = lookback_period_percentile
        self.high_percentile = high_percentile
        self.low_percentile = low_percentile
        
        # Store historical data
        self.price_history = []
        self.vix_history = []

    def calculate_cm_williams_vix(self) -> tuple:
        """Calculate CM Williams VIX Fix indicator"""
        if len(self.price_history) < self.lookback_period_sd:
            return 0.0, False

        prices = np.array(self.price_history[-self.lookback_period_sd:])
        highest_close = np.max(prices)
        current_low = prices[-1]

        # Calculate Williams VIX Fix
        wvf = ((highest_close - current_low) / highest_close) * 100

        # Calculate Bollinger Bands
        if len(self.vix_history) >= self.bb_length:
            vix_values = np.array(self.vix_history[-self.bb_length:])
            mid_line = np.mean(vix_values)
            std_dev = np.std(vix_values)
            upper_band = mid_line + (self.bb_std * std_dev)
            
            # Calculate percentile-based ranges
            if len(self.vix_history) >= self.lookback_period_percentile:
                range_high = np.percentile(
                    self.vix_history[-self.lookback_period_percentile:], 
                    self.high_percentile * 100
                )
                
                # Signal high volatility if WVF crosses above upper band or range high
                is_high_volatility = wvf >= upper_band or wvf >= range_high
                return wvf, is_high_volatility

        self.vix_history.append(wvf)
        return wvf, False

    def create_proposal_based_on_order_levels(self) -> Tuple[List[OrderCandidate], List[OrderCandidate]]:
        """Create buy and sell proposals based on VIX readings"""
        # Get VIX readings
        vix, is_high_volatility = self.calculate_cm_williams_vix()
        
        # Adjust spreads based on volatility
        spread = self.max_spread if is_high_volatility else self.min_spread
        
        # Get reference price
        ref_price = self.get_price(PriceType.MidPrice)
        
        # Calculate order prices
        buy_price = ref_price * (Decimal("1") - spread)
        sell_price = ref_price * (Decimal("1") + spread)
        
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

    def get_price_type(self, price_type: PriceType) -> Decimal:
        """Get price based on type"""
        if len(self.price_history) > 0:
            self.price_history.append(float(self.get_price(PriceType.MidPrice)))
        return super().get_price_type(price_type)
