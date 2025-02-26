from uuid import UUID
from common_lib.alpaca_helpers.async_impl.async_rest import AsyncRestClient
from pydantic import TypeAdapter

from alpaca.common import RawData
from alpaca.common.utils import (
    validate_symbol_or_contract_id,
    validate_uuid_id_param,
    validate_symbol_or_asset_id,
)
from typing import Optional, List, Union
from alpaca.common.enums import BaseURL

from alpaca.trading.requests import (
    ClosePositionRequest,
    GetAssetsRequest,
    GetOptionContractsRequest,
    GetPortfolioHistoryRequest,
    OrderRequest,
    GetOrdersRequest,
    ReplaceOrderRequest,
    GetOrderByIdRequest,
    CancelOrderResponse,
)

from alpaca.trading.models import (
    OptionContract,
    OptionContractsResponse,
    Order,
    PortfolioHistory,
    Position,
    ClosePositionResponse,
    Asset,
    Watchlist,
    TradeAccount,
    AccountConfiguration,
)

class AsyncTradingClient(AsyncRestClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        oauth_token: Optional[str] = None,
        paper: bool = True,
        raw_data: bool = False,
        url_override: Optional[str] = None,
    ) -> None:
        """
        Instantiates a client for trading and managing personal brokerage accounts.

        Args:
            api_key (Optional[str]): The API key for trading. Use paper keys if paper is set to true.
            secret_key (Optional[str]): The secret key for trading. Use paper keys if paper is set to true.
            oauth_token (Optional[str]): The oauth token for trading on behalf of end user.
            paper (bool): True is paper trading should be enabled.
            raw_data (bool): Whether API responses should be wrapped in data models or returned raw.
                This has not been implemented yet.
            url_override (Optional[str]): If specified allows you to override the base url the client points to for proxy/testing.
        """
        super().__init__(
            api_key=api_key,
            secret_key=secret_key,
            oauth_token=oauth_token,
            api_version="v2",
            base_url=(
                url_override
                if url_override
                else BaseURL.TRADING_PAPER if paper else BaseURL.TRADING_LIVE
            ),
            sandbox=paper,
            raw_data=raw_data,
        )

    async def submit_order(self, order_data: OrderRequest) -> Union[Order, RawData]:
        """Creates an order to buy or sell an asset.

        Args:
            order_data (alpaca.trading.requests.OrderRequest): The request data for creating a new order.

        Returns:
            alpaca.trading.models.Order: The resulting submitted order.
        """
        data = order_data.to_request_fields()
        response = await self.post("/orders", data)

        if self._use_raw_data:
            return response

        return Order(**response)

    async def get_orders(
        self, filter: Optional[GetOrdersRequest] = None
    ) -> Union[List[Order], RawData]:
        """
        Returns all orders. Orders can be filtered by parameters.

        Args:
            filter (Optional[GetOrdersRequest]): The parameters to filter the orders with.

        Returns:
            List[alpaca.trading.models.Order]: The queried orders.
        """
        # checking to see if we specified at least one param
        params = filter.to_request_fields() if filter is not None else {}

        if "symbols" in params and isinstance(params["symbols"], list):
            params["symbols"] = ",".join(params["symbols"])

        response = await self.get("/orders", params)

        if self._use_raw_data:
            return response

        return TypeAdapter(List[Order]).validate_python(response)

    async def get_order_by_id(
        self, order_id: Union[UUID, str], filter: Optional[GetOrderByIdRequest] = None
    ) -> Union[Order, RawData]:
        """
        Returns a specific order by its order id.

        Args:
            order_id (Union[UUID, str]): The unique uuid identifier for the order.
            filter (Optional[GetOrderByIdRequest]): The parameters for the query.

        Returns:
            alpaca.trading.models.Order: The order that was queried.
        """
        # checking to see if we specified at least one param
        params = filter.to_request_fields() if filter is not None else {}

        order_id = validate_uuid_id_param(order_id, "order_id")

        response = await self.get(f"/orders/{order_id}", params)

        if self._use_raw_data:
            return response

        return Order(**response)

    async def get_order_by_client_id(self, client_id: str) -> Union[Order, RawData]:
        """
        Returns a specific order by its client order id.

        Args:
            client_id (str): The client order identifier for the order.

        Returns:
            alpaca.trading.models.Order: The queried order.
        """
        params = {"client_order_id": client_id}

        response = await self.get("/orders:by_client_order_id", params)

        if self._use_raw_data:
            return response

        return Order(**response)

    async def replace_order_by_id(
        self,
        order_id: Union[UUID, str],
        order_data: Optional[ReplaceOrderRequest] = None,
    ) -> Union[Order, RawData]:
        """
        Updates an order with new parameters.

        Args:
            order_id (Union[UUID, str]): The unique uuid identifier for the order being replaced.
            order_data (Optional[ReplaceOrderRequest]): The parameters we wish to update.

        Returns:
            alpaca.trading.models.Order: The updated order.
        """
        # checking to see if we specified at least one param
        params = order_data.to_request_fields() if order_data is not None else {}

        order_id = validate_uuid_id_param(order_id, "order_id")

        response = await self.patch(f"/orders/{order_id}", params)

        if self._use_raw_data:
            return response

        return Order(**response)

    async def cancel_orders(self) -> Union[List[CancelOrderResponse], RawData]:
        """
        Cancels all orders.

        Returns:
            List[CancelOrderResponse]: The list of HTTP statuses for each order attempted to be cancelled.
        """
        response = await self.delete("/orders")

        if self._use_raw_data:
            return response

        return TypeAdapter(List[CancelOrderResponse]).validate_python(response)

    async def cancel_order_by_id(self, order_id: Union[UUID, str]) -> None:
        """
        Cancels a specific order by its order id.

        Args:
            order_id (Union[UUID, str]): The unique uuid identifier of the order being cancelled.

        Returns:
            CancelOrderResponse: The HTTP response from the cancel request.
        """
        order_id = validate_uuid_id_param(order_id, "order_id")

        # TODO: Should ideally return some information about the order's cancel status. (Issue #78).
        # TODO: Currently no way to retrieve status details for empty responses with base REST implementation
        await self.delete(f"/orders/{order_id}")

    # ############################## POSITIONS ################################# #

    async def get_all_positions(
        self,
    ) -> Union[List[Position], RawData]:
        """
        Gets all the current open positions.

        Returns:
            List[Position]: List of open positions.
        """
        response = await self.get("/positions")

        if self._use_raw_data:
            return response

        return TypeAdapter(List[Position]).validate_python(response)

    async def get_open_position(
        self, symbol_or_asset_id: Union[UUID, str]
    ) -> Union[Position, RawData]:
        """
        Gets the open position for an account for a single asset. Throws an APIError if the position does not exist.

        Args:
            symbol_or_asset_id (Union[UUID, str]): The symbol name of asset id of the position to get.

        Returns:
            Position: Open position of the asset.
        """
        symbol_or_asset_id = validate_symbol_or_asset_id(symbol_or_asset_id)
        response = await self.get(f"/positions/{symbol_or_asset_id}")

        if self._use_raw_data:
            return response

        return Position(**response)

    async def close_all_positions(
        self, cancel_orders: Optional[bool] = None
    ) -> Union[List[ClosePositionResponse], RawData]:
        """
        Liquidates all positions for an account.

        Places an order for each open position to liquidate.

        Args:
            cancel_orders (Optional[bool]): If true is specified, cancel all open orders before liquidating all positions.

        Returns:
            List[ClosePositionResponse]: A list of responses from each closed position containing the status code and
              order id.
        """
        response = await self.delete(
            "/positions",
            {"cancel_orders": cancel_orders} if cancel_orders else None,
        )

        if self._use_raw_data:
            return response

        return TypeAdapter(List[ClosePositionResponse]).validate_python(response)

    async def close_position(
        self,
        symbol_or_asset_id: Union[UUID, str],
        close_options: Optional[ClosePositionRequest] = None,
    ) -> Union[Order, RawData]:
        """
        Liquidates the position for a single asset.

        Places a single order to close the position for the asset.

        **This method will throw an error if the position does not exist!**

        Args:
            symbol_or_asset_id (Union[UUID, str]): The symbol name of asset id of the position to close.
            close_options: The various close position request parameters.

        Returns:
            alpaca.trading.models.Order: The order that was placed to close the position.
        """
        symbol_or_asset_id = validate_symbol_or_asset_id(symbol_or_asset_id)
        response = await self.delete(
            f"/positions/{symbol_or_asset_id}",
            close_options.to_request_fields() if close_options else {},
        )

        if self._use_raw_data:
            return response

        return Order(**response)

    async def exercise_options_position(
        self,
        symbol_or_contract_id: Union[UUID, str],
    ) -> None:
        """
        This endpoint enables users to exercise a held option contract, converting it into the underlying asset based on the specified terms.
        All available held shares of this option contract will be exercised.
        By default, Alpaca will automatically exercise in-the-money (ITM) contracts at expiry.
        Exercise requests will be processed immediately once received. Exercise requests submitted outside market hours will be rejected.
        To cancel an exercise request or to submit a Do-not-exercise (DNE) instruction, please contact our support team.

        Args:
            symbol_or_contract_id (Union[UUID, str]): Option contract symbol or ID.

        Returns:
            None
        """
        symbol_or_contract_id = validate_symbol_or_contract_id(symbol_or_contract_id)
        await self.post(
            f"/positions/{symbol_or_contract_id}/exercise",
        )

    # ############################## Portfolio ################################# #

    async def get_portfolio_history(
        self,
        history_filter: Optional[GetPortfolioHistoryRequest] = None,
    ) -> Union[PortfolioHistory, RawData]:
        """
        Gets the portfolio history statistics for an account.

        Args:
            account_id (Union[UUID, str]): The ID of the Account to get the portfolio history for.
            history_filter: The various portfolio history request parameters.

        Returns:
            PortfolioHistory: The portfolio history statistics for the account.
        """
        response = await self.get(
            "/account/portfolio/history",
            history_filter.to_request_fields() if history_filter else {},
        )

        if self._use_raw_data:
            return response

        return PortfolioHistory(**response)

    # ############################## Assets ################################# #

    async def get_all_assets(
        self, filter: Optional[GetAssetsRequest] = None
    ) -> Union[List[Asset], RawData]:
        """
        The assets API serves as the master list of assets available for trade and data consumption from Alpaca.
        Some assets are not tradable with Alpaca. These assets will be marked with the flag tradable=false.

        Args:
            filter (Optional[GetAssetsRequest]): The parameters that can be assets can be queried by.

        Returns:
            List[Asset]: The list of assets.
        """
        # checking to see if we specified at least one param
        params = filter.to_request_fields() if filter is not None else {}

        response = await self.get("/assets", params)

        if self._use_raw_data:
            return response

        return TypeAdapter(List[Asset]).validate_python(response)

    async def get_asset(self, symbol_or_asset_id: Union[UUID, str]) -> Union[Asset, RawData]:
        """
        Returns a specific asset by its symbol or asset id. If the specified asset does not exist
        a 404 error will be thrown.

        Args:
            symbol_or_asset_id (Union[UUID, str]): The symbol or asset id for the specified asset

        Returns:
            Asset: The asset if it exists.
        """

        symbol_or_asset_id = validate_symbol_or_asset_id(symbol_or_asset_id)

        response = await self.get(f"/assets/{symbol_or_asset_id}")

        if self._use_raw_data:
            return response

        return Asset(**response)

    # ############################## ACCOUNT ################################# #

    async def get_account(self) -> Union[TradeAccount, RawData]:
        """
        Returns account details. Contains information like buying power,
        number of day trades, and account status.

        Returns:
            alpaca.trading.models.TradeAccount: The account details
        """

        response = await self.get("/account")

        if self._use_raw_data:
            return response

        return TradeAccount(**response)

    async def get_account_configurations(self) -> Union[AccountConfiguration, RawData]:
        """
        Returns account configuration details. Contains information like shorting, margin multiplier
        trader confirmation emails, and Pattern Day Trading (PDT) checks.

        Returns:
            alpaca.broker.models.AccountConfiguration: The account configuration details
        """
        response = await self.get("/account/configurations")

        if self._use_raw_data:
            return response

        return AccountConfiguration(**response)

    async def set_account_configurations(
        self, account_configurations: AccountConfiguration
    ) -> Union[AccountConfiguration, RawData]:
        """
        Returns account configuration details. Contains information like shorting, margin multiplier
        trader confirmation emails, and Pattern Day Trading (PDT) checks.

        Returns:
            alpaca.broker.models.TradeAccountConfiguration: The account configuration details
        """
        response = await self.patch(
            "/account/configurations", data=account_configurations.model_dump()
        )

        if self._use_raw_data:
            return response

        return AccountConfiguration(**response)

    # ############################## WATCHLIST ################################# #

    async def get_watchlists(
        self,
    ) -> Union[List[Watchlist], RawData]:
        """
        Returns all watchlists.

        Returns:
            List[Watchlist]: The list of all watchlists.
        """

        result = await self.get("/watchlists")

        if self._use_raw_data:
            return result

        return TypeAdapter(List[Watchlist]).validate_python(result)

    # ############################## OPTIONS CONTRACTS ################################# #

    async def get_option_contracts(
        self, request: GetOptionContractsRequest
    ) -> Union[OptionContractsResponse, RawData]:
        """
        The option contracts API serves as the master list of option contracts available for trade and data consumption from Alpaca.

        Args:
            request (GetOptionContractsRequest): The parameters that option contracts can be queried by.

        Returns:
            OptionContracts (Union[OptionContractsResponse, RawData]): The object includes list of option contracts.
        """
        if request is None:
            raise ValueError("request (GetOptionContractsRequest) is required")

        params = request.to_request_fields()

        if "underlying_symbols" in params and isinstance(
            request.underlying_symbols, list
        ):
            params["underlying_symbols"] = ",".join(request.underlying_symbols)

        response = await self.get("/options/contracts", params)

        if self._use_raw_data:
            return response

        return TypeAdapter(OptionContractsResponse).validate_python(response)

    async def get_option_contract(
        self, symbol_or_id: Union[UUID, str]
    ) -> Union[OptionContract, RawData]:
        """
        The option contracts API serves as the master list of option contracts available for trade and data consumption from Alpaca.

        Args:
            symbol_or_id (Union[UUID, str]): The symbol or id of the option contract to retrieve.

        Returns:
            OptionContracts (Union[OptionContracts, RawData]): The list of option contracts.
        """
        if symbol_or_id == "":
            raise ValueError("symbol_or_id is required")

        response = await self.get(f"/options/contracts/{symbol_or_id}")

        if self._use_raw_data:
            return response

        return TypeAdapter(OptionContract).validate_python(response)