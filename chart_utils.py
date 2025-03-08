import plotly.graph_objects as go
import pandas as pd

from constants import DEFAULT_ZOOM

def plot_candlestick(data, title, highlight_indices=None):
    """Plots a candlestick chart with optional highlighting."""
    if data is None or data.empty:
        return None

    if not isinstance(data.index, pd.DatetimeIndex):
        data = data.reset_index()
    
    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close']
    )])

    # Basic layout
    fig.update_layout(
        title=title,
        yaxis_title='Price',
        xaxis_title='Date/Time',
        template="plotly_dark",
        height=600,
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        dragmode='zoom',
        hovermode='x unified'
    )

    rangebreaks = detect_range_breaks(data)
    # Configure the x-axis for better trading view
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeslider=dict(visible=True, thickness=0.05),  # Thinner rangeslider
        type='date',
        rangebreaks=rangebreaks
    )
    
    # Configure y-axis for dynamic adjustment
    fig.update_yaxes(
        autorange=True,
        fixedrange=False,  # Allow y-axis zooming
        constrain="domain"  # This helps with y-axis auto-scaling
    )
    
    if highlight_indices is not None:
        fig.add_vrect(
            x0=data.index[highlight_indices],
            x1=data.index[-1],
            fillcolor="rgba(250, 250, 0, 0.15)",
            opacity=0.5,
            layer="below",
            line_width=0,
            annotation_text="Prediction Zone",
            annotation_position="top left"
        )
    
    # Default zoom into recent 60 candles
    zoom_candles = DEFAULT_ZOOM
    if len(data) > zoom_candles:
        visible_data = data.iloc[-zoom_candles:]
        fig.update_xaxes(range=[visible_data.index[0], visible_data.index[-1]])
        
        # Set y-axis range based on visible data
        price_buffer = 0.01  # 1% buffer above and below
        y_min = visible_data['Low'].min() * (1 - price_buffer)
        y_max = visible_data['High'].max() * (1 + price_buffer)
        fig.update_yaxes(range=[y_min, y_max])
    else:
        fig.update_xaxes(range=[data.index[0], data.index[-1]])
    
    # Add range selector buttons
    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=60, label="Recent 60", step="day", stepmode="backward"),
                    dict(count=90, label="Recent 90", step="day", stepmode="backward"),
                    dict(step="all", label="All")
                ]),
                bgcolor="rgba(50, 50, 50, 0.7)",
                font=dict(color="white")
            )
        )
    )

    return fig

def calculate_trend(data):
    """Calculates the overall trend of the data"""
    if len(data) < 2:
        return None
        
    first_30_pct = data["Close"].iloc[:int(len(data) * 0.3)].mean()
    last_30_pct = data["Close"].iloc[-int(len(data) * 0.3):].mean()
    
    if last_30_pct > first_30_pct:
        return "up"
    else:
        return "down"


# Chatgpt wrote the below function
def detect_range_breaks(data):
    """Detects missing time intervals and returns rangebreaks for Plotly."""
    if len(data) < 2:
        return []
    
    time_diffs = data.index.to_series().diff().dropna()
    median_interval = time_diffs.median()  # Detect expected interval
    
    # Find large gaps (greater than 1.5x expected interval)
    large_gaps = time_diffs[time_diffs > median_interval * 1.5]
    
    rangebreaks = []
    for gap_start in large_gaps.index:
        prev_time = gap_start - time_diffs[gap_start]
        rangebreaks.append(dict(bounds=[prev_time, gap_start]))
    
    return rangebreaks
