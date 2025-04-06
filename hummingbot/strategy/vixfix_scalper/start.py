from typing import Dict
from decimal import Decimal
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.strategy.vixfix_scalper.vixfix_scalper import VixFixScalperStrategy
from hummingbot.strategy.vixfix_scalper.vixfix_scalper_config_map import vixfix_scalper_config_map as c_map

def start(self):
    try:
        connector = c_map.get("connector").value
        market = c_map.get("market").value
        base_order_amount = c_map.get("base_order_amount").value
        profit_target_pct = c_map.get("profit_target_pct").value
        initial_stop_loss_pct = c_map.get("initial_stop_loss_pct").value

        self._initialize_markets([(connector, [market])])
        market_info = MarketTradingPairTuple(self.markets[connector], market, *market.split("-"))
        self.market_trading_pair_tuples = [market_info]

        self.strategy = VixFixScalperStrategy(
            market_info=market_info,
            base_order_amount=base_order_amount,
            profit_target_pct=profit_target_pct,
            initial_stop_loss_pct=initial_stop_loss_pct
        )
    except Exception as e:
        self.notify(f"Error initializing strategy: {str(e)}")
        self.logger().error("Error initializing strategy.", exc_info=True)
