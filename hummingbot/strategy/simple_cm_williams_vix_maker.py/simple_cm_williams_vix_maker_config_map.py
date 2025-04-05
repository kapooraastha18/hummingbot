from decimal import Decimal
from typing import Optional
from hummingbot.client.config.config_var import ConfigVar
from hummingbot.client.config.config_validators import (
    validate_exchange,
    validate_market_trading_pair,
    validate_bool,
    validate_decimal,
    validate_int
)
from hummingbot.client.settings import (
    required_exchanges,
    EXAMPLE_PAIRS,
)
from hummingbot.client.config.config_helpers import (
    minimum_order_amount
)

def trading_pair_prompt():
    exchange = simple_cm_williams_vix_maker_config_map.get("exchange").value
    example = EXAMPLE_PAIRS.get(exchange)
    return "Enter the trading pair you would like to trade on %s%s >>> " % (
        exchange,
        f" (e.g. {example})" if example else "",
    )

def str2bool(value: str):
    return str(value).lower() in ("yes", "true", "t", "1")

# strategy specific validators
def validate_order_amount(value: str) -> Optional[str]:
    try:
        exchange = simple_cm_williams_vix_maker_config_map.get("exchange").value
        trading_pair = simple_cm_williams_vix_maker_config_map.get("trading_pair").value
        min_amount = minimum_order_amount(exchange, trading_pair)
        if Decimal(value) < min_amount:
            return f"Order amount must be at least {min_amount}."
    except Exception:
        return "Invalid order amount."
    return None

simple_cm_williams_vix_maker_config_map = {
    "strategy": ConfigVar(
        key="strategy",
        prompt="",
        default="simple_cm_williams_vix_maker"
    ),
    "exchange": ConfigVar(
        key="exchange",
        prompt="Enter your exchange name >>> ",
        validator=validate_exchange,
        on_validated=lambda value: required_exchanges.append(value),
    ),
    "trading_pair": ConfigVar(
        key="trading_pair",
        prompt=trading_pair_prompt,
        validator=validate_market_trading_pair,
    ),
    "order_amount": ConfigVar(
        key="order_amount",
        prompt="Enter the order amount >>> ",
        type_str="decimal",
        validator=validate_order_amount,
    ),
    "min_spread": ConfigVar(
        key="min_spread",
        prompt="Enter the minimum spread (e.g. 0.01 for 1%) >>> ",
        type_str="decimal",
        validator=lambda v: validate_decimal(v, min_value=0),
    ),
    "max_spread": ConfigVar(
        key="max_spread",
        prompt="Enter the maximum spread for high volatility (e.g. 0.05 for 5%) >>> ",
        type_str="decimal",
        validator=lambda v: validate_decimal(v, min_value=0),
    ),
    "lookback_period": ConfigVar(
        key="lookback_period",
        prompt="Enter the lookback period for volatility calculation >>> ",
        type_str="int",
        validator=lambda v: validate_int(v, min_value=5),
        default=20
    ),
    "volatility_threshold": ConfigVar(
        key="volatility_threshold",
        prompt="Enter the volatility threshold (e.g. 0.015 for 1.5%) >>> ",
        type_str="float",
        default=0.015
    ),
    "order_refresh_time": ConfigVar(
        key="order_refresh_time",
        prompt="How often do you want to refresh orders (in seconds)? >>> ",
        type_str="float",
        validator=lambda v: validate_decimal(v, min_value=0, inclusive=False),
        default=30.0
    ),
    "order_refresh_tolerance_pct": ConfigVar(
        key="order_refresh_tolerance_pct",
        prompt="Enter the percent change in price needed to refresh orders (Enter 1 to indicate 1%) >>> ",
        type_str="decimal",
        validator=lambda v: validate_decimal(v, min_value=0, inclusive=True),
        default=Decimal("0.2")
    ),
    "filled_order_delay": ConfigVar(
        key="filled_order_delay",
        prompt="How long do you want to wait before placing the next order (in seconds)? >>> ",
        type_str="float",
        validator=lambda v: validate_decimal(v, min_value=0, inclusive=False),
        default=60.0
    ),
    "hanging_orders_enabled": ConfigVar(
        key="hanging_orders_enabled",
        prompt="Do you want to enable hanging orders? (Yes/No) >>> ",
        type_str="bool",
        default=False,
        validator=validate_bool
    ),
    "hanging_orders_cancel_pct": ConfigVar(
        key="hanging_orders_cancel_pct",
        prompt="At what spread percentage do you want to cancel hanging orders? (Enter 1 to indicate 1%) >>> ",
        type_str="decimal",
        default=Decimal("10"),
        validator=lambda v: validate_decimal(v, min_value=0, inclusive=False),
    ),
    "order_optimization_enabled": ConfigVar(
        key="order_optimization_enabled",
        prompt="Do you want to enable best bid ask jumping? (Yes/No) >>> ",
        type_str="bool",
        default=False,
        validator=validate_bool
    ),
    "ask_order_optimization_depth": ConfigVar(
        key="ask_order_optimization_depth",
        prompt="How deep do you want to go into the order book for ask (sell) price? >>> ",
        type_str="decimal",
        default=Decimal("0"),
        validator=lambda v: validate_decimal(v, min_value=0),
    ),
    "bid_order_optimization_depth": ConfigVar(
        key="bid_order_optimization_depth",
        prompt="How deep do you want to go into the order book for bid (buy) price? >>> ",
        type_str="decimal",
        default=Decimal("0"),
        validator=lambda v: validate_decimal(v, min_value=0),
    ),
    "add_transaction_costs_to_orders": ConfigVar(
        key="add_transaction_costs_to_orders",
        prompt="Do you want to add transaction costs to order prices? (Yes/No) >>> ",
        type_str="bool",
        default=False,
        validator=validate_bool
    ),
    "price_ceiling": ConfigVar(
        key="price_ceiling",
        prompt="Enter the price ceiling for the strategy >>> ",
        type_str="decimal",
        default=Decimal("1000000"),
        validator=lambda v: validate_decimal(v, Decimal("0"), inclusive=False),
    ),
    "price_floor": ConfigVar(
        key="price_floor",
        prompt="Enter the price floor for the strategy >>> ",
        type_str="decimal",
        default=Decimal("0"),
        validator=lambda v: validate_decimal(v, Decimal("0"), inclusive=True),
    ),
    "ping_pong_enabled": ConfigVar(
        key="ping_pong_enabled",
        prompt="Would you like to use the ping pong feature and alternate between buy and sell? (Yes/No) >>> ",
        type_str="bool",
        default=False,
        validator=validate_bool
    ),
    "logging_options": ConfigVar(
        key="logging_options",
        prompt=f"Enter logging level (0-4) >>> ",
        type_str="int",
        validator=lambda v: validate_int(v, min_value=0, max_value=4),
        default=3,
    ),
    "status_report_interval": ConfigVar(
        key="status_report_interval",
        prompt="How often would you like to receive status reports? (in seconds) >>> ",
        type_str="float",
        default=900,
        validator=lambda v: validate_decimal(v, min_value=0, inclusive=False),
    ),
    "minimum_spread": ConfigVar(
        key="minimum_spread",
        prompt="At what spread should the strategy stop placing orders? (Enter 1 for 1%) >>> ",
        type_str="decimal",
        default=Decimal("0"),
        validator=lambda v: validate_decimal(v, min_value=0, inclusive=True),
    ),
}
