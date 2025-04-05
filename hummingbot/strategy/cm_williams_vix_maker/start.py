from decimal import Decimal
from typing import List, Tuple

from hummingbot.connector.exchange.paper_trade import create_paper_trade_market
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.strategy.cm_williams_vix_maker import CMWilliamsVixMaker
from hummingbot.strategy.cm_williams_vix_maker.cm_williams_vix_maker_config_map import cm_williams_vix_maker_config_map as c_map

def start(self):
    try:
        # Basic configuration
        order_amount = c_map.get("order_amount").value
        min_spread = c_map.get("min_spread").value / Decimal("100")
        max_spread = c_map.get("max_spread").value / Decimal("100")
        order_refresh_time = c_map.get("order_refresh_time").value
        filled_order_delay = c_map.get("filled_order_delay").value
        order_optimization_enabled = c_map.get("order_optimization_enabled").value
        
        # VIX parameters
        lookback_period = c_map.get("lookback_period").value
        bb_length = c_map.get("bb_length").value
        bb_std = c_map.get("bb_std").value
        high_volatility_multiplier = c_map.get("high_volatility_multiplier").value
        low_volatility_multiplier = c_map.get("low_volatility_multiplier").value
        
        # Risk management parameters
        max_position_size = c_map.get("max_position_size").value
        stop_loss_spread = c_map.get("stop_loss_spread").value / Decimal("100")
        take_profit_spread = c_map.get("take_profit_spread").value / Decimal("100")
        position_cooling_off = c_map.get("position_cooling_off").value
        
        # Logging and status
        logging_options = c_map.get("logging_options").value
        status_report_interval = c_map.get("status_report_interval").value

        trading_pair = c_map.get("trading_pair").value
        exchange = c_map.get("exchange").value

        # Get market
        try:
            market = self.markets[exchange]
        except KeyError:
            self.notify(f"Market {exchange} is not initialized. ")
            return

        maker_data = [market, trading_pair]
        self.market_trading_pair_tuples = [MarketTradingPairTuple(*maker_data)]

        self.strategy = CMWilliamsVixMaker(
            market_info=MarketTradingPairTuple(*maker_data),
            min_spread=min_spread,
            max_spread=max_spread,
            order_amount=order_amount,
            order_refresh_time=order_refresh_time,
            filled_order_delay=filled_order_delay,
            order_optimization_enabled=order_optimization_enabled,
            # VIX parameters
            lookback_period=lookback_period,
            bb_length=bb_length,
            bb_std=bb_std,
            high_volatility_multiplier=high_volatility_multiplier,
            low_volatility_multiplier=low_volatility_multiplier,
            # Risk management parameters
            max_position_size=max_position_size,
            stop_loss_spread=stop_loss_spread,
            take_profit_spread=take_profit_spread,
            position_cooling_off=position_cooling_off,
            logging_options=logging_options,
            status_report_interval=status_report_interval,
        )
    except Exception as e:
        self.notify(str(e))
        self.logger().error("Unknown error during initialization.", exc_info=True)
        return
