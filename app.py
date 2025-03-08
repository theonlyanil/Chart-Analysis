import streamlit as st
import random
from st_paywall import add_auth

from constants import *
from data_handler import get_data
from chart_utils import plot_candlestick, calculate_trend

add_auth(required=True)


# --- Helper Functions ---
def get_random_symbol(universe=None):
    """Gets a random symbol from selected universe or custom input."""
    if universe == "Custom":
        symbol = st.session_state.get("custom_symbol", DEFAULT_SYMBOL)
        return symbol
    elif universe:
        symbol = random.choice(STOCK_UNIVERSES[universe])
        return symbol
    else:
        all_symbols = [symbol for symbols in STOCK_UNIVERSES.values() for symbol in symbols]
        symbol = random.choice(all_symbols)
        return symbol

# --- Streamlit App ---
def main():
    st.title("Candlestick Chart Predictor")

    # Initialize essential session state variables
    if "score" not in st.session_state:
        st.session_state.score = 0
    if "history" not in st.session_state:
        st.session_state.history = []
    if "predicted" not in st.session_state:
        st.session_state.predicted = False
    if "prediction" not in st.session_state:
        st.session_state.prediction = None
    if "already_scored" not in st.session_state:
        st.session_state.already_scored = False
    if "active_symbol" not in st.session_state:
        st.session_state.active_symbol = DEFAULT_SYMBOL
    if "full_data" not in st.session_state:
        st.session_state.full_data = None
    if "last_universe" not in st.session_state:
        st.session_state.last_universe = None
    if "last_interval" not in st.session_state:
        st.session_state.last_interval = DEFAULT_INTERVAL
    if "prediction_candles" not in st.session_state:
        st.session_state.prediction_candles = DEFAULT_PREDICTION_CANDLES
        
    # Sidebar settings
    st.sidebar.header("Settings")
    
    # Universe selector
    universe_options = list(STOCK_UNIVERSES.keys()) + ["Custom"]
    selected_universe = st.sidebar.selectbox("Select Stock Universe", universe_options, key="universe_selector")
    
    # Custom symbol input
    if selected_universe == "Custom":
        previous_custom = st.session_state.get("custom_symbol", DEFAULT_SYMBOL) 
        st.session_state.custom_symbol = st.sidebar.text_input(
            "Enter Symbol (add .NS for Indian stocks)", value=previous_custom
        ).upper()
    
    # Interval selector
    interval_index = INTERVALS.index(DEFAULT_INTERVAL)  # Default interval
    interval = st.sidebar.selectbox("Select Interval", INTERVALS, index=interval_index, key="interval_selector")
    
    # Prediction candles selector
    prediction_candles = st.sidebar.slider("Number of candles to predict", 
                                          min_value=MIN_PREDICTION_CANDLES, 
                                          max_value=MAX_PREDICTION_CANDLES, 
                                          value=st.session_state.prediction_candles, 
                                          step=PREDICTION_CANDLES_STEP)
    st.session_state.prediction_candles = prediction_candles
    
    # Scoreboard
    st.sidebar.markdown("---")
    st.sidebar.header("Scoreboard")
    st.sidebar.markdown(f"**Total Score:** {st.session_state.score}")
    if len(st.session_state.history) > 0:
        accuracy = round(sum(st.session_state.history) / len(st.session_state.history) * 100, 2)
        st.sidebar.markdown(f"**Accuracy:** {accuracy}%")
        st.sidebar.markdown(f"**Total Predictions:** {len(st.session_state.history)}")
    
    # Reset button
    if st.sidebar.button("Reset Score", key="reset_button"):
        st.session_state.score = 0
        st.session_state.history = []
        st.session_state.predicted = False
        st.session_state.already_scored = False
        st.session_state.active_symbol = DEFAULT_SYMBOL
        st.session_state.full_data = None
        st.session_state.custom_symbol = DEFAULT_SYMBOL
        st.session_state.last_universe = None
        st.session_state.last_interval = DEFAULT_INTERVAL
        st.session_state.prediction_candles = DEFAULT_PREDICTION_CANDLES
        st.rerun()

    # Determine if we need new data based on universe/interval changes
    need_new_data = False
    
    # Check if universe changed
    if st.session_state.last_universe != selected_universe:
        st.session_state.last_universe = selected_universe
        need_new_data = True
        
        # Get new symbol if universe changed (except for Custom)
        if selected_universe != "Custom":
            st.session_state.active_symbol = get_random_symbol(selected_universe)
    
    # Check if interval changed
    if st.session_state.last_interval != interval:
        st.session_state.last_interval = interval
        need_new_data = True
    
    # Handle custom symbol changes
    if selected_universe == "Custom":
        current_symbol = st.session_state.custom_symbol
        if st.session_state.active_symbol != current_symbol:
            st.session_state.active_symbol = current_symbol
            need_new_data = True
    else:
        current_symbol = st.session_state.active_symbol
        if current_symbol is None or current_symbol == DEFAULT_SYMBOL and st.session_state.full_data is None:
            # First run or after reset - generate a new symbol
            current_symbol = get_random_symbol(selected_universe)
            st.session_state.active_symbol = current_symbol
            need_new_data = True
    
    # Load data if needed (first time or symbol/interval change)
    if need_new_data or st.session_state.full_data is None:
        with st.spinner("Loading data..."):
            full_data = get_data(current_symbol, interval)
            if full_data is not None and not full_data.empty:
                st.session_state.full_data = full_data
                # Reset prediction state when data changes
                if st.session_state.predicted:
                    st.session_state.predicted = False
                    st.session_state.already_scored = False
            else:
                st.session_state.full_data = None
    
    # Use the stored data
    full_data = st.session_state.full_data
    
    if full_data is not None and not full_data.empty:
        # Display current symbol and period
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"Stock Universe: **{selected_universe}**")
        with col2:
            st.write(f"Symbol: **{current_symbol}** - Interval: **{interval}**")
        with col3:
            data_start = full_data.index[0].strftime('%Y-%m-%d')
            data_end = full_data.index[-1].strftime('%Y-%m-%d')
            st.write(f"Period: **{data_start}** to **{data_end}**")
        
        if len(full_data) < MIN_REQUIRED_DATA_POINTS + st.session_state.prediction_candles:
            st.error(f"Not enough data points for the selected interval and {st.session_state.prediction_candles} prediction candles. Please choose another interval.")
        else:
            total_candles = len(full_data)
            split_index = total_candles - st.session_state.prediction_candles
            
            # Check if we're in prediction mode or result mode
            if not st.session_state.predicted:
                # Initial view - show all data except the last prediction candles
                initial_data = full_data.iloc[:split_index].copy()
                fig = plot_candlestick(initial_data, f"{current_symbol} - Initial Data")
                st.plotly_chart(fig, use_container_width=True)
                
                # Prediction form
                st.header(f"Predict the trend for the next {st.session_state.prediction_candles} candles:")
                with st.form("prediction_form"):
                    prediction = st.radio("Your prediction:", options=["Up", "Down"], horizontal=True)
                    submit_button = st.form_submit_button("Submit Prediction")
                    
                    if submit_button:
                        st.session_state.prediction = prediction.lower()
                        st.session_state.predicted = True
                        st.session_state.already_scored = False
                        st.rerun()
            
            else:
                # Display full view with highlighted prediction zone
                fig = plot_candlestick(full_data, f"{current_symbol} - Full Data", highlight_indices=split_index)
                st.plotly_chart(fig, use_container_width=True)

                # Calculate and show results
                final_candles = full_data.iloc[split_index:].copy()
                true_trend = calculate_trend(final_candles)
                
                # Check if prediction was correct
                if true_trend == st.session_state.prediction:
                    st.success("Correct prediction!")
                    if not st.session_state.already_scored:
                        st.balloons()
                        st.session_state.score += 1
                        st.session_state.history.append(1)
                        st.session_state.already_scored = True
                else:
                    st.error(f"Incorrect prediction. True trend was {true_trend}.")
                    if not st.session_state.already_scored:
                        st.session_state.score -= 1
                        st.session_state.history.append(0)
                        st.session_state.already_scored = True

                # Show score
                st.write(f"**Score:** {st.session_state.score}")
                if len(st.session_state.history) > 0:
                    accuracy = round(sum(st.session_state.history) / len(st.session_state.history) * 100, 2)
                    st.write(f"**Accuracy:** {accuracy}%")

                # Next button
                if st.button("Next", key="next_button"):
                    st.session_state.predicted = False
                    st.session_state.already_scored = False
                    
                    # Only get a new random symbol if not in custom mode
                    if selected_universe != "Custom":
                        new_symbol = get_random_symbol(selected_universe)
                        st.session_state.active_symbol = new_symbol
                        # Clear data to force reload with new symbol
                        st.session_state.full_data = None
                    st.rerun()
    else:
        st.warning("No data available. Please try another interval.")

if __name__ == "__main__":
    main()