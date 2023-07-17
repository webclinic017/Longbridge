import numpy as np
from datetime import datetime
from tradingview_ta import TA_Handler
from . import models as md


def prepare_tradingview(interval):
    res = np.array([["APPL", "", "", "", "", ""]])

    for ticker, exchange in md.ticker_exchanges.items():
        handler = TA_Handler(
            symbol=ticker,
            exchange=exchange,
            screener="america",
        )

        handler.interval = md.intervals.get(interval)
        current = [ticker, "", "", "", "", ""]

        try:
            now = datetime.now()
            print("Ticker: %-5s\t%4s\ton: %s" % (
                ticker, interval, now.strftime("%d/%m/%y %H:%M:%S")))

            analysis = handler.get_analysis()
            latest_price = analysis.indicators["close"]
            latest_change = analysis.indicators["change"]
            ratting = analysis.summary
            current[1] = f"{latest_price:,.2f}" + f" {latest_change:,.2f}"
            current[2] = ratting.get('RECOMMENDATION')
            current[3] = ratting.get('BUY')
            current[4] = ratting.get('NEUTRAL')
            current[5] = ratting.get('SELL')
        except Exception as e:
            print(f"Error retrieving data for {ticker} at {interval}: {e}")

        res = np.append(res, [current], axis=0)

    return res[1:]


def prepare_web_content(trade_date):
    def find_timing(df):
        buyTime, sellTime = "", ""
        buyPrice, sellPrice = 0.00, 0.00
        for i in range(len(df) - 1, -1, -1):
            if df["BuyIndex"][i] == "PotentialBuy" and buyTime == "":
                buyTime = datetime.strftime(df["Datetime"][i], "%d/%m %H:%M")
                buyPrice = df["Low"][i]
            elif df["BuyIndex"][i] == "PotentialSell" and sellTime == "":
                sellTime = datetime.strftime(df["Datetime"][i], "%d/%m %H:%M")
                sellPrice = df["High"][i]

        return f"%s\n%s" % (buyTime, f"{buyPrice:,.2f}"), f"%s\n%s" % (sellTime, f"{sellPrice:,.2f}")

    res = np.array([["APPL", 0.00, 0.00, "", "", "", "", "", "", "", "", "", ""]])

    for ticker, _ in md.ticker_exchanges.items():
        now = datetime.now()
        print("Trade date: %s\tTicker: %-5s\tCalculation date: %s" % (
            trade_date, ticker, now.strftime("%d/%m/%y %H:%M:%S")))

        df = md.get_df_interval(ticker, trade_date, "1m", md.interval_type.get("1m"))
        current = [
            ticker, f"{df['CRSI'][len(df) - 1]:,.2f}", f"{df['Close'][len(df) - 1]:,.2f}",
            "", "", "", "", "", "", "", "", "", ""]
        current[3], current[4] = find_timing(df)

        df = md.get_df_interval(ticker, trade_date, "15m", md.interval_type.get("15m"))
        current[5], current[6] = find_timing(df)

        df = md.get_df_interval(ticker, trade_date, "30m", md.interval_type.get("30m"))
        current[7], current[8] = find_timing(df)

        df = md.get_df_interval(ticker, trade_date, "60m", md.interval_type.get("60m"))
        current[9], current[10] = find_timing(df)

        df = md.get_df_interval(ticker, trade_date, "1d", md.interval_type.get("1d"))
        current[11], current[12] = find_timing(df)

        res = np.append(res, [current], axis=0)

    return res[1:]

# print(prepare_web_content("2023-07-17"))