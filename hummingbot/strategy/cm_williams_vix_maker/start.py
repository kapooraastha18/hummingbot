from decimal import Decimal
from typing import Dict, Any, List, Tuple
import logging

from hummingbot.connector.exchange.paper_trade import create_paper_trade_market
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.strategy.cm_williams_vix_maker import CMWilliamsVixMaker
from hummingbot.strategy.cm_williams_vix_maker.cm_williams_vix_maker_config_map import cm_williams_vix_maker_config_map as c_map

def start(self):
    try:
        # Basic configuration
        exchange = c_map.get("exchange").value
        trading_pair = c_map.get("trading_pair").value
        
        # Get market
        try:
            market = self.markets[exchange]
        except KeyError:
            self.notify(f"Market {exchange} is not initialized.")
            return

        # Order parameters
        order_amount = c_map.get("order_amount").value
        min_spread = c_map.get("min_spread").value / Decimal("100")
        max_spread = c_map.get("max_spread").value / Decimal("100")
        
        # VIX parameters
        lookback_period = c_map.get("lookback_period").value
        bb_length = c_map.get("bb_length").value
        bb_std = c_map.get("bb_std").value
        high_volatility_multiplier = c_map.get("high_volatility_multiplier").value
        low_volatility_multiplier = c_map.get("low_volatility_multiplier").value
        
        # Trend analysis parameters
        ema_short = c_map.get("ema_short").value
        ema_long = c_map.get("ema_long").value
        trend_strength_threshold = c_map.get("trend_strength_threshold").value
        
        # Risk management parameters
        max_position_size = c_map.get("max_position_size").value
        stop_loss_spread = c_map.get("stop_loss_spread").value / Decimal("100")
        take_profit_spread = c_map.get("take_profit_spread").value / Decimal("100")
        dynamic_spread_adjustment = c_map.get("dynamic_spread_adjustment").value
        inventory_target_base_pct = c_map.get("inventory_target_base_pct").value
        risk_factor = c_map.get("risk_factor").value
        max_order_age = c_map.get("max_order_age").value
        
        # Order management parameters
        order_refresh_time = c_map.get("order_refresh_time").value
        filled_order_delay = c_map.get("filled_order_delay").value
        order_optimization_enabled = c_map.get("order_optimization_enabled").value
        position_cooling_off = c_map.get("position_cooling_off").value
        
        # Logging and reporting
        logging_options = c_map.get("logging_options").value
        status_report_interval = c_map.get("status_report_interval").value

        # Set up market info
        maker_data = [market, trading_pair]
        self.market_trading_pair_tuples = [MarketTradingPairTuple(*maker_data)]

        # Initialize strategy with all parameters
        self.strategy = CMWilliamsVixMaker(
            market_info=MarketTradingPairTuple(*maker_data),
            # Order parameters
            order_amount=order_amount,
            min_spread=min_spread,
            max_spread=max_spread,
            # VIX parameters
            lookback_period=lookback_period,
            bb_length=bb_length,
            bb_std=bb_std,
            high_volatility_multiplier=high_volatility_multiplier,
            low_volatility_multiplier=low_volatility_multiplier,
            # Trend analysis parameters
            ema_short=ema_short,
            ema_long=ema_long,
            trend_strength_threshold=trend_strength_threshold,
            # Risk management parameters
            max_position_size=max_position_size,
            stop_loss_spread=stop_loss_spread,
            take_profit_spread=take_profit_spread,
            dynamic_spread_adjustment=dynamic_spread_adjustment,
            inventory_target_base_pct=inventory_target_base_pct,
            risk_factor=risk_factor,
            max_order_age=max_order_age,
            # Order management parameters
            order_refresh_time=order_refresh_time,
            filled_order_delay=filled_order_delay,
            order_optimization_enabled=order_optimization_enabled,
            position_cooling_off=position_cooling_off,
            # Logging and reporting
            logging_options=logging_options,
            status_report_interval=status_report_interval,
        )
        
        # Set logging level
        if logging_options == 1:
            self.logger().setLevel(logging.INFO)
        else:
            self.logger().setLevel(logging.DEBUG)
            
    except Exception as e:
        self.notify(str(e))
        self.logger().error("Unknown error during initialization.", exc_info=True)
        return
