# FILE: webgui.py
import streamlit as st
import time
from datetime import datetime
import plotly.graph_objects as go
from scraper import get_prediction, get_stock_data
import json
import os
from dotenv import load_dotenv

load_dotenv()

USER_AGENT = os.getenv('YAHOO_FINANCE_USER_AGENT')

st.set_page_config(page_title="Stock Price Tracker", layout="wide")

# Initialize session state for multiple predictions
if 'predictions' not in st.session_state:
    st.session_state.predictions = {}  # {prediction_id: {'user', 'prediction', 'prices_history'}}
if 'next_id' not in st.session_state:
    st.session_state.next_id = 0

def create_price_chart(prices_history, target_price):
    timestamps = [t for t, _ in prices_history]
    prices = [p for _, p in prices_history]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=prices,
        name="Price",
        line=dict(color="blue")
    ))
    
    # Add target price line
    fig.add_hline(
        y=target_price,
        line_dash="dash",
        line_color="red",
        annotation_text="Target"
    )
    
    fig.update_layout(
        title="Price History",
        xaxis_title="Time",
        yaxis_title="Price ($)",
        height=400
    )
    
    return fig

def delete_prediction(prediction_id):
    if prediction_id in st.session_state.predictions:
        del st.session_state.predictions[prediction_id]

def main():
    st.title("Stock Price Prediction Tracker")
    
    # Add new prediction form
    with st.form("prediction_form"):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Username:")
        with col2:
            prediction_input = st.text_input("Prediction:")
        submitted = st.form_submit_button("Track")
        
        if submitted and username and prediction_input:
            prediction = get_prediction(prediction_input)
            if prediction:
                prediction_id = st.session_state.next_id
                st.session_state.predictions[prediction_id] = {
                    'user': username,
                    'prediction': prediction,
                    'prices_history': []
                }
                st.session_state.next_id += 1
    
    # Display active predictions
    for pred_id, pred_data in list(st.session_state.predictions.items()):
        with st.expander(f"{pred_data['user']}'s Prediction - {pred_data['prediction']['symbol']}", expanded=True):
            # Delete button
            if st.button("Delete", key=f"delete_{pred_id}"):
                delete_prediction(pred_id)
                st.rerun(scope="app")  # Updated rerun command
                continue
            
            pred = pred_data['prediction']
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Symbol", pred['symbol'])
            with col2:
                st.metric("Target Price", f"${pred['target_price']:.2f}")
            with col3:
                st.metric("Target Date", pred['date'])
            
            # Price updates
            current_price = get_stock_data(pred['symbol'])
            if current_price is not None:
                # Update price history
                pred_data['prices_history'].append((datetime.now(), current_price))
                if len(pred_data['prices_history']) > 60:
                    pred_data['prices_history'].pop(0)
                
                # Calculate difference percentage
                diff_pct = ((current_price - float(pred['target_price'])) / float(pred['target_price'])) * 100
                
                # Display metrics
                mcol1, mcol2 = st.columns(2)
                with mcol1:
                    st.metric("Current Price", f"${current_price:.2f}")
                with mcol2:
                    st.metric("Difference", f"{diff_pct:.2f}%")
                
                # Display chart
                st.plotly_chart(
                    create_price_chart(
                        pred_data['prices_history'],
                        float(pred['target_price'])
                    ),
                    use_container_width=True
                )
    
    # Add small delay between updates
    time.sleep(10)

if __name__ == "__main__":
    main()