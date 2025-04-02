from decimal import Decimal

from pydantic import ConfigDict, SecretStr
from pydantic.v1 import Field

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap, ClientFieldData
from hummingbot.connector.derivative.gate_io_perpetual import gate_io_perpetual_constants as CONSTANTS
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

CENTRALIZED = True
EXAMPLE_PAIR = "BTC-USDT"
DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.00015"),
    taker_percent_fee_decimal=Decimal("0.0005"),
)


class GateIOPerpetualConfigMap(BaseConnectorConfigMap):
    connector: str = "gate_io_perpetual"
    gate_io_perpetual_api_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: f"Enter your {CONSTANTS.EXCHANGE_NAME} API key",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )
    gate_io_perpetual_secret_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: f"Enter your {CONSTANTS.EXCHANGE_NAME} secret key",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )
    gate_io_perpetual_user_id: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: f"Enter your {CONSTANTS.EXCHANGE_NAME} user id",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )
    model_config = ConfigDict(title="gate_io_perpetual")


KEYS = GateIOPerpetualConfigMap.construct()
