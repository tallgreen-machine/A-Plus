import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import backtrader as bt
import pandas as pd
import datetime

class SimpleRSIStrategy(bt.Strategy):
    params = (
        ('rsi_period', 14),
        ('rsi_upper', 70),
        ('rsi_lower', 30),
        ('printlog', True),
    )

    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.order = None

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function for this strategy'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            if self.rsi < self.params.rsi_lower:
                self.log('BUY CREATE, %.2f' % self.data.close[0])
                self.order = self.buy()
        else:
            if self.rsi > self.params.rsi_upper:
                self.log('SELL CREATE, %.2f' % self.data.close[0])
                self.order = self.sell()

def run_backtest():
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(SimpleRSIStrategy)

    # Load data
    datapath = 'market_data.csv'
    data = bt.feeds.GenericCSVData(
        dataname=datapath,
        dtformat=('%Y-%m-%d %H:%M:%S'),
        datetime=0,
        high=2,
        low=3,
        open=1,
        close=4,
        volume=5,
        openinterest=-1
    )

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(10000.0)
    
    # Add a sizer to trade a fixed size
    cerebro.addsizer(bt.sizers.FixedSize, stake=0.001)

    # Set the commission - 0.1% ... divide by 100 to get the decimal
    cerebro.broker.setcommission(commission=0.001)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Plot the result
    print('Plotting results...')
    figure = cerebro.plot(style='candlestick', iplot=False)[0][0]
    figure.savefig('backtest_results.png')
    print('Plot saved to backtest_results.png')

if __name__ == '__main__':
    run_backtest()
