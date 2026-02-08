from .get_and_clean_data import get_and_clean_data


# from numpy.testing._private.utils import assert_allclose
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt 
matplotlib.use('Agg')
from matplotlib.transforms import blended_transform_factory





def plot_strategy(
    auto_figsize: bool=True,
    figsize: tuple=(16, 9),
    width_per_candle: float=0.12,
    min_width: float=12,
    max_width: float=300,
    height: float=9,
    df=None,
    output_candles=None,
    

        

):
    def _calculate_figsize():
        """
        Calculate optimal figsize for output based on number of candles.
        Width scales with candle count, height stays reasonable.
        
        Returns:
            tuple: (width, height) in inches
        """
        if not auto_figsize:
            # Use manual figsize from config
            return figsize


        # Calculate width based on actual data length
        num_candles = len(df) if df is not None else output_candles
        width = num_candles * width_per_candle
        width = max(min_width, min(max_width, width))

        return (width, height)



    # plotting functions
    def _plot_last_price_line(ax, df, asset):
        """Draw TradingView-style last price line starting from last candle."""
        if df is None or df.empty:
            return

        last_price = float(df['close'].iloc[-1])

        # IMPORTANT: x-axis is integer-based
        last_x = len(df) - 1

        # Axis limits (right margin already added by caller)
        x_left, x_right = ax.get_xlim()

        # Extend line to the right edge
        ax.plot(
            [last_x, x_right],
            [last_price, last_price],
            linestyle='--',
            linewidth=1.5,
            color='#2962ff',
            alpha=0.9,
            zorder=4,
            clip_on=False
        )

        # Price formatting
        if np.abs(last_price) >= 100:
            price_txt = f"{last_price:,.2f}"
        elif np.abs(last_price) >= 1:
            price_txt = f"{last_price:,.4f}"
        else:
            price_txt = f"{last_price:,.6f}"

        # Label at the right edge
        ax.text(
            x_right,
            last_price,
            f" {price_txt} ",
            ha='left',
            va='center',
            fontsize=9,
            color='white',
            bbox=dict(
                boxstyle='round,pad=0.35',
                facecolor='#2962ff',
                edgecolor='none',
                alpha=0.95
            ),
            zorder=5,
            clip_on=False
        )


    def _plot_last_datetime_info(ax, df, asset):
        """TradingView-style datetime box under the last candle"""
        if df is None or df.empty:
            return

        # Datetime is the INDEX
        last_datetime = df.index[-1]

        # INTEGER x-axis
        last_x = len(df) - 1

        formatted_date = last_datetime.strftime("%a %d %b '%y  %H:%M")

        trans = blended_transform_factory(ax.transData, ax.transAxes)

        ax.text(
            last_x,
            -0.03,
            formatted_date,
            ha='center',
            va='top',
            fontsize=10,
            color='#d1d4dc',
            bbox=dict(
                boxstyle='round,pad=0.45',
                facecolor='#2a2e39',
                edgecolor='#434651',
                linewidth=1,
                alpha=0.95
            ),
            transform=trans,
            clip_on=False,
            zorder=10
        )


    # === MAIN PLOTTING LOGIC ===

    # Calculate optimal figsize
    figsize = _calculate_figsize()

    rows = 1
    cols = 1

    fig, axes = plt.subplots(
        rows, cols,
        figsize=figsize,  # Use calculated figsize
        facecolor=self.config['bg_color'],
        # gridspec_kw={'height_ratios': [7, 1]},
    )

    plot_candlestick(
        ax=axes[0],
        df=self.df,
        tf=self.tf,
        ticker=self.asset,
        timezone=self.config["ohlc_tz"],
        up_color=self.config["up_color"],
        down_color=self.config["down_color"],
        edge_color=self.config["edge_color"],
        wick_color=self.config["wick_color"],
        volume_color=self.config["volume_color"],
        bg_color=self.config["bg_color"],
        grid_color=self.config["grid_color"],
        grid_style=self.config["grid_style"],
        grid_alpha=self.config["grid_alpha"],
        show_grid=self.config["show_grid"],
        candle_width=self.config["candle_width"],
        date_format=self.config["date_format"],
        rotation=self.config["rotation"],
        show_nontrading=self.config["show_nontrading"],
        title_fontsize=self.config["title_fontsize"],
        title_fontweight=self.config["title_fontweight"],
        title_color=self.config["title_color"],
        label_fontsize=self.config["label_fontsize"],
        label_color=self.config["label_color"],
        tick_fontsize=self.config["tick_fontsize"],
        tick_color=self.config["tick_color"],
        spine_color=self.config["spine_color"],
        spine_linewidth=self.config["spine_linewidth"],
        show_top_spine=self.config["show_top_spine"],
        show_right_spine=self.config["show_right_spine"],
        y_padding=self.config["y_padding"]
    )

    xlim = axes[0].get_xlim()
    right_margin = self.config['right_margin']
    axes[0].set_xlim(xlim[0], xlim[1] + right_margin)

    # Add all overlay elements
    _add_session_backgrounds_and_labels(axes[0], self.df, self.asset)
    _plot_ma(axes[0], self.df, self.asset)
    _plot_last_price_line(axes[0], self.df, self.asset)
    _plot_last_datetime_info(axes[0], self.df, self.asset)
    # _plot_other_datetime_info(axes[0], self.df, self.asset, tf=self.tf)
    _plot_position_box(axes[0], self.df, self.asset)
    _plot_signal_scatter(axes[0], self.df, self.asset)
    _plot_macd(axes[1], self.df, self.asset)

    plt.tight_layout()
    return fig