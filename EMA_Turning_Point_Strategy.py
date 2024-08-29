# region imports
from AlgorithmImports import *
# endregion

class EmaTurningPointStrategy(QCAlgorithm):

    def initialize(self):
        self.universe_settings.resolution = Resolution.DAILY
        self.set_start_date(2020, 7, 1)
        self.set_end_date(2022, 7, 1)
        self.set_cash(5000)
        self.set_brokerage_model(BrokerageName.BITFINEX, AccountType.CASH)
        
        self.btc = self.add_crypto('BTCUSD', Resolution.DAILY).symbol
        self.set_benchmark(self.btc)
        
        stock_plot = Chart('Trade Plot')
        stock_plot.add_series(Series('BUY', SeriesType.SCATTER, '$', Color.Green, ScatterMarkerSymbol.TRIANGLE))
        stock_plot.add_series(Series('SELL', SeriesType.SCATTER, '$', Color.Red, ScatterMarkerSymbol.TRIANGLE_DOWN))
        stock_plot.add_series(Series('FOMO BUY', SeriesType.SCATTER, '$', Color.Green, ScatterMarkerSymbol.CIRCLE))
        stock_plot.add_series(Series('JOMO SELL', SeriesType.SCATTER, '$', Color.Red, ScatterMarkerSymbol.CIRCLE))
        self.add_chart(stock_plot)

        self.last_action = ['', 0]
        self.potential_action = ['', 0]

        self.add_universe_selection(ManualUniverseSelectionModel([self.btc]))
        self.set_alpha(EmaTurningPointAlphaModel(self))
        self.set_portfolio_construction(InsightWeightingPortfolioConstructionModel())
        self.set_risk_management(MaximumDrawdownPercentPortfolio(0.05, True))
        self.set_execution(ImmediateExecutionModel(self))


class EmaTurningPointAlphaModel(AlphaModel):
    def __init__(self, algorithm):
        self.algorithm = algorithm
        self.symbol_data = None
        self.lookback = 6
        self.period = 3


    def on_securities_changed(self, algorithm, changes):
        if changes.removed_securities:
            symbol_data = self.symbol_data
            if symbol_data:
                symbol_data.dispose()
                self.symbol_data = None

        if changes.added_securities:
            symbol = changes.added_securities[0].symbol
            self.symbol_data = SymbolData(algorithm, symbol, self.period, self.lookback)


    def update(self, algorithm, data):
        insights = []

        if not self.symbol_data.is_ready:
            return insights

        self.symbol = self.symbol_data.symbol
        price = data[self.symbol].Price
        
        last_averages = list(self.symbol_data.rolling_window)
        price_change = (price - self.algorithm.last_action[1]) / self.algorithm.last_action[1] if self.algorithm.last_action[0] != '' else 0
        turning_point = self.turning_point(last_averages)
        dynamic_threshold = ((self.symbol_data.atr.current.value)/price)
        
        if turning_point == 'MIN' and (self.algorithm.last_action[0][-4:] == 'SELL' or self.algorithm.last_action[0] == ''):
            if price_change <= -dynamic_threshold or self.algorithm.last_action[0] == '':
                insights.append(Insight.Price(self.symbol, timedelta(1), InsightDirection.Up))
                self.algorithm.potential_action = ['BUY', price]
        
        elif turning_point == 'MAX' and (self.algorithm.last_action[0][-3:] == 'BUY'):
            if price_change >= dynamic_threshold:
                insights.append(Insight.Price(self.symbol, timedelta(1), InsightDirection.Down))
                self.algorithm.potential_action = ['SELL', price]
        
        elif turning_point == 'NONE':
            if self.algorithm.last_action[0][-4:] == 'SELL' and price_change >= dynamic_threshold:
                insights.append(Insight.Price(self.symbol, timedelta(1), InsightDirection.Up))
                self.algorithm.potential_action = ['FOMO BUY', price]
        
            elif self.algorithm.last_action[0][-3:] == 'BUY' and price_change <= -dynamic_threshold:
                insights.append(Insight.Price(self.symbol, timedelta(1), InsightDirection.Down))
                self.algorithm.potential_action = ['JOMO SELL', price]

        self.algorithm.Plot("Trade Plot", "EMA", self.symbol_data.rolling_window[0])
        self.algorithm.Plot("Trade Plot", "BENCHMARK", price)

        return insights


    def turning_point(self, data):
        first_derivatives = np.diff(np.array(data))
        all_positive = np.all(first_derivatives[1:2] > 0)
        all_negative = np.all(first_derivatives[1:2] < 0)
        if first_derivatives[0] < 0 and all_positive:
            return 'MIN'
        elif first_derivatives[0] > 0 and all_negative:
            return 'MAX'
        return 'NONE'


class SymbolData:
    def __init__(self, algorithm, symbol, period, lookback):
        self.algorithm = algorithm
        self.symbol = symbol
        self.lookback = lookback
        self.period = period
        self.updated = False

        self.rolling_window = RollingWindow[float](self.period)
        self.consolidator = TradeBarConsolidator(timedelta(days=1))
        
        self.ema = ExponentialMovingAverage(name='ema', period=self.period)
        self.ema.updated += self.on_update
        self.atr = AverageTrueRange(name='atr_short', period=self.lookback)

        self.algorithm.register_indicator(self.symbol, self.ema, self.consolidator)
        self.algorithm.register_indicator(self.symbol, self.atr, self.consolidator)
        self.algorithm.subscription_manager.add_consolidator(self.symbol, self.consolidator)

        history = algorithm.history[TradeBar](self.symbol, self.lookback, Resolution.DAILY)
        for bar in history:
            self.consolidator.update(bar)
            if self.ema.is_ready:
                self.rolling_window.add(self.ema.current.value)


    def on_update(self, sender, updated):
        self.rolling_window.add(updated.value)
        self.updated = True


    def dispose(self):
        self.ema.updated -= self.on_update
        self.atr.updated -= self.on_update
        self.ema.reset()
        self.atr.reset()
        self.rolling_window.reset()
        self.algorithm.subscription_manager.remove_consolidator(self.symbol, self.consolidator)


    @property
    def is_ready(self):
        return self.rolling_window.is_ready


class InsightWeightingPortfolioConstructionModel(PortfolioConstructionModel):
    def __init__(self):
        super().__init__()


    def create_targets(self, algorithm, insights):
        targets = []
        
        for insight in insights:
            symbol = insight.symbol
            security = algorithm.securities[symbol]

            if insight.Direction == InsightDirection.Up:
                cash_to_invest = 0.975 * algorithm.portfolio.cash
                symbol_price = security.price
                target_quantity = cash_to_invest / symbol_price
            else:
                target_quantity = 0

            targets.append(PortfolioTarget(symbol, target_quantity))
        
        return targets


class ImmediateExecutionModel(ExecutionModel):
    def __init__(self, algorithm):
        super().__init__()
        self.algorithm = algorithm
        self.brokerage_fees = 0.002


    def execute(self, algorithm, targets):
        for target in targets:
            current_quantity = self.algorithm.securities[target.symbol].holdings.quantity
            order_quantity = target.quantity - current_quantity
            price_change = abs((self.algorithm.potential_action[1] - self.algorithm.last_action[1])/self.algorithm.last_action[1]) if self.algorithm.last_action[0] != '' else 0

            self.algorithm.debug(self.algorithm.last_action)
            self.algorithm.debug(self.algorithm.potential_action)

            if ((self.brokerage_fees * 2 < price_change or self.algorithm.last_action[0] == '') and order_quantity != 0):
                self.algorithm.market_order(target.symbol, order_quantity)
                self.algorithm.last_action = self.algorithm.potential_action
                algorithm.Plot("Trade Plot", self.algorithm.potential_action[0], self.algorithm.potential_action[1])
