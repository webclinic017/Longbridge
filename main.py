import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import pandas as pd
import pandas_market_calendars as mcal
import yfinance as yf
import ta
import pendulum
from datetime import datetime
from scipy.interpolate import make_interp_spline


def print_realtime_ratting(df):
    for i in range(len(df)):
        current = df["BuyIndex"][i]
        if current == "Buy" or current == "PotentialBuy":
            print("%s\tBuy   \t%.2f\tRSI: %5.2f" % (df["Datetime"][i], df["Low"][i], df["RSI"][i]))
        elif current == "Sell" or current == "PotentialSell":
            print("%s\tSell  \t%.2f\tRSI: %5.2f" % (df["Datetime"][i], df["High"][i], df["RSI"][i]))


def generate_US_trade_days(start_date, end_date):
    # Get NYSE and Nasdaq calendars
    nyse = mcal.get_calendar('NYSE')
    nasdaq = mcal.get_calendar('NASDAQ')

    # Get NYSE and Nasdaq schedules
    nyse_schedule = nyse.schedule(start_date=start_date, end_date=end_date)
    nasdaq_schedule = nasdaq.schedule(start_date=start_date, end_date=end_date)

    # Get the intersection of NYSE and Nasdaq schedules
    trade_days = nyse_schedule.index.intersection(nasdaq_schedule.index)

    return trade_days


def calculate_commission(price, position, direction):
    res = max(1, 0.005 * position) + 0.003 * position

    if direction == "Sell":
        res += max(0.01, 0.000008 * price * position) + min(7.27, max(0.01, 0.000145 * position))

    return res


def calculate_buy_position(price, balance, direction):
    for i in range(int(balance / price) + 1, -1, -1):
        rest = balance - price * i - calculate_commission(price, i, direction)
        if 0 <= rest < price:
            return i

    return 0


def find_signals(df):
    # Initialize an empty column for signals
    df["BuyIndex"] = ""
    flag_can_start = False  # Can visit df["DIF"][i - 1]
    buy_tick = True  # True: to buy, False: to hold or sell

    for i in range(len(df)):

        DIF = df["DIF"][i]
        DEM = df["DEM"][i]
        Histogram = df["Histogram"][i]
        RSI = df["RSI"][i]
        K = df["K"][i]
        D = df["D"][i]
        J = df["J"][i]

        if flag_can_start:
            DIF_last = df["DIF"][i - 1]
            DEM_last = df["DEM"][i - 1]

            if (DIF > DEM and DIF_last < DEM_last) and (DIF < 0 and DEM < 0) and (RSI <= 100):
                if buy_tick:
                    df.iloc[i, df.columns.get_loc("BuyIndex")] = "Buy"
                    buy_tick = False
                elif not buy_tick:
                    df.iloc[i, df.columns.get_loc("BuyIndex")] = "PotentialBuy"
            elif (DIF < DEM and DIF_last > DEM_last) and (DIF > 0 and DEM > 0) and (RSI >= 50):
                if not buy_tick:
                    df.iloc[i, df.columns.get_loc("BuyIndex")] = "Sell"
                    buy_tick = True
                elif buy_tick:
                    df.iloc[i, df.columns.get_loc("BuyIndex")] = "PotentialSell"
            else:
                df.iloc[i, df.columns.get_loc("BuyIndex")] = "Hold"

        if pd.notna(DIF) and pd.notna(DEM):
            flag_can_start = True
            continue

    # Return the data frame with signals
    return df


def print_day_trade(df, principle):
    df["Balance"] = principle
    df["Position"] = 0
    df["Commission"] = 0.00

    for i in range(len(df)):
        direction = df["BuyIndex"][i]
        balance = df["Balance"][i - 1]
        position = 0

        if direction == "Buy":
            price = df["Low"][i]
            position = calculate_buy_position(price, balance, direction)
            commission = calculate_commission(price, position, direction)
            balance = balance - price * position - commission

            df.iloc[i, df.columns.get_loc("Balance")] = balance
            df.iloc[i, df.columns.get_loc("Position")] = position
            df.iloc[i, df.columns.get_loc("Commission")] = commission
        elif direction == "Sell":
            price = df["High"][i]
            position = df["Position"][i - 1]
            commission = calculate_commission(price, position, direction)
            balance = balance + price * position - commission

            df.iloc[i, df.columns.get_loc("Balance")] = balance
            df.iloc[i, df.columns.get_loc("Position")] = 0
            df.iloc[i, df.columns.get_loc("Commission")] = commission
        else:
            df.iloc[i, df.columns.get_loc("Balance")] = df["Balance"][i - 1]
            df.iloc[i, df.columns.get_loc("Position")] = df["Position"][i - 1]

        if direction == "Buy" or direction == "Sell":
            print("%s\t%-4s\t%5.2f\t@%4d\tCommission: %4.2f\tBalance: %10s\tTotal: %10s" % (
                df["Datetime"][i], direction, df["Low"][i], position, df["Commission"][i], f"{balance:,.2f}",
                f"{balance + df['Close'][i] * df['Position'][i]:,.2f}"))

    final_index = len(df) - 1
    final_asset = df["Balance"][final_index]
    if df["Position"][final_index] > 0:
        final_asset += df["Close"][final_index] * df["Position"][final_index]
    print(f"{final_asset:,.2f}")

    return df


def plot_vertical_lines(df, ax):
    for i in range(len(df)):
        x_trade = df["Datetime"][i]
        current = df["BuyIndex"][i]
        if current == "Buy" or current == "PotentialBuy":
            ax.axvline(x=x_trade, ymin=0, ymax=3.2, c="#ff2f92", linewidth=0.5, alpha=1, zorder=0, clip_on=False)
        elif current == "Sell" or current == "PotentialSell":
            ax.axvline(x=x_trade, ymin=0, ymax=3.2, c="#0055cc", linewidth=0.5, alpha=1, zorder=0, clip_on=False)


def mark_buy_and_sell(df, ax):
    for i in range(len(df)):
        x_trade = df["Datetime"][i]
        y_trade = -200
        if df["BuyIndex"][i] == "Buy":
            text = "B\n" + f"{df['Low'][i]:,.2f}"
            ax.annotate(text, xy=(x_trade, y_trade), xytext=(
                x_trade, y_trade), color="#ffffff", fontsize=8,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.15", facecolor="#ff2f92",
                                  edgecolor="none", alpha=1))
        elif df["BuyIndex"][i] == "PotentialBuy":
            text = f"{df['Low'][i]:,.2f}"
            ax.annotate(text, xy=(x_trade, y_trade), xytext=(
                x_trade, y_trade), color="#ffffff", fontsize=7,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.15", facecolor="#ff2f92",
                                  edgecolor="none", alpha=1))
        elif df["BuyIndex"][i] == "Sell":
            text = "S\n" + f"{df['High'][i]:,.2f}"
            ax.annotate(text, xy=(x_trade, y_trade), xytext=(
                x_trade, y_trade + 80), color="#ffffff", fontsize=8,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.15", facecolor="#0055cc",
                                  edgecolor="none", alpha=1))
        elif df["BuyIndex"][i] == "PotentialSell":
            text = f"{df['High'][i]:,.2f}"
            ax.annotate(text, xy=(x_trade, y_trade), xytext=(
                x_trade, y_trade), color="#ffffff", fontsize=7,
                        bbox=dict(boxstyle="round, pad=0.15, rounding_size=0.15", facecolor="#0055cc",
                                  edgecolor="none", alpha=1))


def plot_candlestick(df, ax, ticker):
    # plot the candlestick chart on ax
    mc = mpf.make_marketcolors(up='#006d21', down='#ff2f92', edge='inherit', wick='inherit',
                               volume='inherit')
    s = mpf.make_mpf_style(base_mpf_style='starsandstripes', rc={'font.size': 6},
                           marketcolors=mc)
    mpf.plot(df, type="candle", ax=ax, style=s, warn_too_much_data=10000000)
    ax.set_ylabel("%s @ %s" % (ticker, str(df["Datetime"][len(df) - 1])[:10]))
    ax.yaxis.set_label_position("right")
    [ax.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
    ax.set_xticklabels([])
    ax.set_xticks([])
    ax.margins(x=0)


def plot_MACD(df, ax, date_format):
    # plot the MACD, signal and histogram on ax
    ax.set_ylabel("MACD")
    ax.set_xlim(min(df["Datetime"]), max(df["Datetime"]))
    ax.margins(x=0)
    ax.xaxis.set_label_position("top")
    ax.xaxis.set_ticks_position("top")
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_ticks_position("right")
    [ax.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
    ax.xaxis.set_major_formatter(date_format)
    ax.tick_params(axis="x", top=False)
    ax.plot(df["Datetime"], df["DIF"], color="#0055cc", label="DIF", linewidth=1)
    ax.plot(df["Datetime"], df["DEM"], color="#ffa500", label="DEM", linewidth=1)
    ax.bar(df["Datetime"], df["Histogram"], width=[0.0005 if len(df) <= 390 else 2000 / len(df)],
           color=["#006d21" if h >= 0 else "#ff2f92" for h in df["Histogram"]])


def plot_RSI(df, ax):
    # plot the RSI on ax
    ax.set_ylabel("RSI")
    ax.set_xlim(min(df["Datetime"]), max(df["Datetime"]))
    ax.margins(x=0)
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_ticks_position("right")
    ax.plot(df["Datetime"], df["RSI"], label="RSI", color="#ff2f92", linewidth=1)
    [ax.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
    ax.set_xticklabels([])
    ax.set_xticks([])
    ax.set_ylim(0, 100)


def plot_KDJ(df, ax):
    # plot the KDJ on ax
    ax.set_ylabel("KDJ")
    ax.set_xlim(min(df["Datetime"]), max(df["Datetime"]))
    ax.margins(x=0)
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_ticks_position("right")
    ax.plot(df["Datetime"], df["K"], label="K", color="#ff2f92", linewidth=1)
    ax.plot(df["Datetime"], df["D"], label="D", color="#0055cc", linewidth=1)
    ax.plot(df["Datetime"], df["J"], label="J", color="#ffa500", linewidth=1)
    [ax.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
    ax.set_xticklabels([])
    ax.set_xticks([])
    ax.set_ylim(-200, 200)


def plot_Volume(df, ax):
    ax.set_ylabel("Vol")
    ax.set_xlim(min(df["Datetime"]), max(df["Datetime"]))
    ax.margins(x=0)
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_ticks_position("right")
    ax.bar(df["Datetime"], df["Volume"], width=0.0005, color="#006d21")
    [ax.spines[s].set_visible(False) for s in ["top", "right", "bottom", "left"]]
    ax.set_ylim(top=max(df["Volume"]))
    ax.set_xticklabels([])
    ax.set_xticks([])

    # Add a smooth fitting line based on df["Volume"]
    x_new = pd.date_range(df["Datetime"].min(), df["Datetime"].max(), periods=300)
    spl = make_interp_spline(df["Datetime"], df["Volume"], k=3)
    volume_smooth = spl(x_new)
    plt.plot(x_new, volume_smooth * 4, color="#ffa500", linewidth=1)


def calculate_df(df):
    # Convert date column to datetime format
    df["Datetime"] = pd.to_datetime(df.index)

    # Calculate MACD, RSI, KDJ, CCI using ta library
    df["DIF"] = ta.trend.MACD(df["Close"], window_slow=26, window_fast=12).macd()
    df["DEM"] = df["DIF"].ewm(span=9).mean()
    df["Histogram"] = df["DIF"] - df["DEM"].ewm(span=9).mean()

    df["KDJ"] = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"]).stoch()
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
    df["K"] = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"], window=9).stoch()
    df["D"] = df["K"].ewm(com=2).mean()
    df["J"] = 3 * df["K"] - 2 * df["D"]

    df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"], window=20, constant=0.015).cci()

    return df


def plotOneDay(ticker, start_time, end_time):
    # define the ticker symbol
    date_format = mdates.DateFormatter("%d/%m/%y")

    # get data using download method
    df = yf.download(ticker, start=start_time, end=end_time, interval="1d", progress=False)
    df = calculate_df(df)
    df = find_signals(df)

    # Plot stock price, MACD, KDJ, RSI using matplotlib
    plt.rcParams["font.family"] = "Menlo"
    fig = plt.figure(figsize=(16, 9), dpi=300)

    ax1 = plt.subplot2grid((8, 1), (0, 0), rowspan=4)
    ax2 = plt.subplot2grid((8, 1), (4, 0), rowspan=2)
    ax3 = plt.subplot2grid((8, 1), (6, 0), rowspan=1)
    ax4 = plt.subplot2grid((8, 1), (7, 0), rowspan=1)

    plot_candlestick(df, ax1, ticker)
    plot_MACD(df, ax2, date_format)
    plot_RSI(df, ax3)
    plot_KDJ(df, ax4)

    plot_vertical_lines(df, ax2)
    plot_vertical_lines(df, ax3)
    plot_vertical_lines(df, ax4)
    mark_buy_and_sell(df, ax4)

    # save the figure
    fig.savefig("1d %-5s %s %s.png" % (ticker, start_time, end_time), transparent=True, bbox_inches="tight")
    return df


def plotOneMinute(ticker, trade_day):
    # define the ticker symbol
    date_format = mdates.DateFormatter("%H:%M")

    # get data using download method
    start_time = pendulum.parse(trade_day + " 00:00")
    end_time = pendulum.parse(trade_day + " 23:59")
    df = yf.download(ticker, start=start_time, end=end_time, interval="1m", progress=False)

    # convert the index to Eastern Time and remove the timezone
    df.index = pd.DatetimeIndex(df.index).tz_convert("US/Eastern").tz_localize(None)
    df = calculate_df(df)
    df = find_signals(df)
    print_realtime_ratting(df)

    # Plot stock price, MACD, KDJ, RSI using matplotlib
    plt.rcParams["font.family"] = "Menlo"
    fig = plt.figure(figsize=(16, 9), dpi=300)

    ax1 = plt.subplot2grid((9, 1), (0, 0), rowspan=4)
    ax2 = plt.subplot2grid((9, 1), (4, 0), rowspan=2)
    ax3 = plt.subplot2grid((9, 1), (6, 0), rowspan=1)
    ax4 = plt.subplot2grid((9, 1), (7, 0), rowspan=1)
    ax5 = plt.subplot2grid((9, 1), (8, 0), rowspan=3)

    plot_candlestick(df, ax1, ticker)
    plot_MACD(df, ax2, date_format)
    plot_RSI(df, ax3)
    plot_KDJ(df, ax4)
    plot_Volume(df, ax5)

    plot_vertical_lines(df, ax2)
    plot_vertical_lines(df, ax3)
    plot_vertical_lines(df, ax4)
    plot_vertical_lines(df, ax5)
    mark_buy_and_sell(df, ax4)

    # save the figure
    fig.savefig("1m %-5s %s.png" % (ticker, trade_day), transparent=True, bbox_inches="tight")
    return df


tickers = ["NVDA", "MSFT", "META", "TSM", "GOOGL", "AMZN", "QCOM", "AMD", "ORCL", "VZ", "NFLX", "JPM", "GS",
           "MS",
           "WFC", "BAC",
           "V", "MA", "AXP", "CVX", "XOM", "MCD", "PEP", "KO", "PG", "ABBV", "MRK", "LLY", "UNH", "PFE", "JNJ", "SPY",
           "SPLG"]

today = datetime.today()
date_string = today.strftime("%Y-%m-%d")
date_string_today = today.strftime("%Y-%m-%d")
principal = 10000.00

# 1. For single stock
plotOneDay("NVDA", "2020-01-01", date_string_today)
plotOneMinute("NVDA", "2023-06-28")

# # 2. For all stocks in the list
# for x in tickers:
#     now = datetime.now()
#     print("%-5s %s" % (x, now.strftime("%d/%m/%y %H:%M:%S")))
#     plotOneMinute(x, "2023-06-30")
#     plotOneDay(x, "2020-01-01", date_string_today)

# # 3. Day trade in recent 30 days
# trade_days = generate_US_trade_days("2023-06-01", "2023-06-29")
#
# for i in trade_days:
#     trade_day = str(i)[:10]
