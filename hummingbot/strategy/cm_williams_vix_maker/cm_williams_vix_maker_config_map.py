from decimal import Decimal
from typing import Optional

from hummingbot.client.config.config_var import ConfigVar
from hummingbot.client.config.config_validators import (
    validate_bool,
    validate_decimal,
    validate_exchange,
    validate_int,
    validate_market_trading_pair,
)
from hummingbot.client.settings import (
    required_exchanges,
    AllConnectorSettings,
)

def trading_pair_prompt():
    exchange = cm_williams_vix_maker_config_map.get("exchange").value
    example = AllConnectorSettings.get_example_pairs().get(exchange)
    return "Enter the trading pair you would like to trade on %s%s >>> " \
           % (exchange, f" (e.g. {example})" if example else "")

def str2bool(value: str):
    return str(value).lower() in ('yes', 'true', 't', '1')

# Strategy specific validation functions
def validate_lookback_period(value: str) -> Optional[str]:
    try:
        lookback = int(value)
        if lookback < 1:
            return "Lookback period must be greater than 0."
    except ValueError:
        return "Please enter a valid integer."
    return None

def validate_percentile(value: str) -> Optional[str]:
    try:
        percentile = float(value)
        if not (0 < percentile < 1):
            return "Percentile must be between 0 and 1."
    except ValueError:
        return "Please enter a valid decimal number."
    return None

cm_williams_vix_maker_config_map = {
    "strategy": ConfigVar(
        key="strategy",
        prompt="",
        default="cm_williams_vix_maker"
    ),
    "exchange": ConfigVar(
        key="exchange",
        prompt="Enter your maker spot connector >>> ",
        prompt_on_new=True,
        validator=validate_exchange,
        on_validated=lambda value: required_exchanges.append(value),
    ),
    "trading_pair": ConfigVar(
        key="trading_pair",
        prompt=trading_pair_prompt,
        prompt_on_new=True,
        validator=validate_market_trading_pair,
        on_validated=lambda value: required_exchanges.append(value),
    ),
    "lookback_period_sd": ConfigVar(
        key="lookback_period_sd",
        prompt="Enter lookback period for standard deviation (e.g. 22) >>> ",
        type_str="int",
        default=22,
        validator=validate_lookback_period,
    ),
    "bb_length": ConfigVar(
        key="bb_length",
        prompt="Enter Bollinger Band length (e.g. 20) >>> ",
        type_str="int",
        default=20,
        validator=validate_int,
    ),
    "bb_std": ConfigVar(
        key="bb_std",
        prompt="Enter Bollinger Band standard deviation multiplier (e.g. 2.0) >>> ",
        type_str="float",
        default=2.0,
        validator=validate_decimal,
    ),
    "lookback_period_percentile": ConfigVar(
        key="lookback_period_percentile",
        prompt="Enter lookback period for percentile calculation (e.g. 50) >>> ",
        type_str="int",
        default=50,
        validator=validate_lookback_period,
    ),
    "high_percentile": ConfigVar(
        key="high_percentile",
        prompt="Enter high percentile threshold (e.g. 0.85 for 85%) >>> ",
        type_str="float",
        default=0.85,
        validator=validate_percentile,
    ),
    "low_percentile": ConfigVar(
        key="low_percentile",
        prompt="Enter low percentile threshold (e.g. 1.01 for 101%) >>> ",
        type_str="float",
        default=1.01,
        validator=validate_decimal,
    ),
    "order_amount": ConfigVar(
        key="order_amount",
        prompt="Enter the order amount >>> ",
        type_str="decimal",
        validator=validate_decimal,
    ),
    "min_spread": ConfigVar(
        key="min_spread",
        prompt="Enter the minimum spread (e.g. 0.01 for 1%) >>> ",
        type_str="decimal",
        default=Decimal("0.01"),
        validator=validate_decimal,
    ),
    "max_spread": ConfigVar(
        key="max_spread",
        prompt="Enter the maximum spread (e.g. 0.05 for 5%) >>> ",
        type_str="decimal",
        default=Decimal("0.05"),
        validator=validate_decimal,
    ),
    "inventory_target_base_pct": ConfigVar(
        key="inventory_target_base_pct",
        prompt="Enter the target base asset percentage (e.g. 0.5 for 50%) >>> ",
        type_str="decimal",
        default=Decimal("0.5"),
        validator=validate_decimal,
    ),
    "inventory_range_multiplier": ConfigVar(
        key="inventory_range_multiplier",
        prompt="Enter the inventory range multiplier >>> ",
        type_str="decimal",
        default=Decimal("1.0"),
        validator=validate_decimal,
    ),
    "volatility_adjustment": ConfigVar(
        key="volatility_adjustment",
        prompt="Enter the volatility adjustment multiplier >>> ",
        type_str="decimal",
        default=Decimal("1.0"),
        validator=validate_decimal,
    ),
    "order_refresh_time": ConfigVar(
        key="order_refresh_time",
        prompt="Enter the order refresh time in seconds >>> ",
        type_str="float",
        default=30.0,
        validator=validate_decimal,
    ),
    "max_order_age": ConfigVar(
        key="max_order_age",
        prompt="Enter the maximum order age in seconds >>> ",
        type_str="float",
        default=1800.0,
        validator=validate_decimal,
    ),
    "order_refresh_tolerance_pct": ConfigVar(
        key="order_refresh_tolerance_pct",
        prompt="Enter the order refresh tolerance (e.g. 0.002 for 0.2%) >>> ",
        type_str="decimal",
        default=Decimal("0.002"),
        validator=validate_decimal,
    ),
    "filled_order_delay": ConfigVar(
        key="filled_order_delay",
        prompt="Enter the delay before placing new orders after fills (in seconds) >>> ",
        type_str="float",
        default=60.0,
        validator=validate_decimal,
    ),
    "hanging_orders_enabled": ConfigVar(
        key="hanging_orders_enabled",
        prompt="Do you want to enable hanging orders? (Yes/No) >>> ",
        type_str="bool",
        default=False,
        validator=validate_bool,
    ),
    "hanging_orders_cancel_pct": ConfigVar(
        key="hanging_orders_cancel_pct",
        prompt="Enter the hanging orders cancel threshold (e.g. 0.1 for 10%) >>> ",
        type_str="decimal",
        default=Decimal("0.1"),
        validator=validate_decimal,
        required_if=lambda: cm_williams_vix_maker_config_map.get("hanging_orders_enabled").value,
    ),
    "order_optimization_enabled": ConfigVar(
        key="order_optimization_enabled",
        prompt="Do you want to enable order optimization? (Yes/No) >>> ",
        type_str="bool",
        default=True,
        validator=validate_bool,
    ),
    "risk_factor": ConfigVar(
        key="risk_factor",
        prompt="Enter the risk factor multiplier (e.g. 1.0) >>> ",
        type_str="decimal",
        default=Decimal("1.0"),
        validator=validate_decimal,
    ),
    "max_position_size": ConfigVar(
        key="max_position_size",
        prompt="Enter the maximum position size >>> ",
        type_str="decimal",
        validator=validate_decimal,
    ),
    "stop_loss_pct": ConfigVar(
        key="stop_loss_pct",
        prompt="Enter the stop loss percentage (e.g. 0.05 for 5%) >>> ",
        type_str="decimal",
        default=Decimal("0.05"),
        validator=validate_decimal,
    ),
    "position_cooling_off": ConfigVar(
        key="position_cooling_off",
        prompt="Enter the position cooling-off period in seconds >>> ",
        type_str="int",
        default=300,
        validator=validate_int,
    ),
}
