"""
Dashboard Studio Application - Main Entry Point

This application helps students prepare for oral exams by providing
a structured study plan, topic tracking, and AI-powered study assistance.
"""

import time
import pandas as pd
import streamlit as st
import os
from datetime import datetime, timedelta

# Import modules
from src.data.loader import carica_argomenti, inizializza_punteggi, inizializza_stato_argomenti
from src.utils.calendar import genera_calendario_studio
from src.ui.pages import main_layout

# === PARAMETRI STUDIO ===
st.set_page_config(page_title="Studio Orale AS2B", layout="wide")
DATA_ESAME = datetime(2025, 9, 24)
OGGI = datetime.now().date()
GIORNI_STUDIO = (DATA_ESAME.date() - OGGI).days
STATO_FILE = "stato_argomenti.csv"
PUNTEGGI_FILE = "punteggi_test.csv"

def main():
    """Main application entry point."""
    # Initialize session state for chat log
    if "chat_log" not in st.session_state:
        st.session_state.chat_log = []
    
    # Load data with caching
    argomenti_df = carica_argomenti()
    stato_argomenti_df = inizializza_stato_argomenti(argomenti_df, STATO_FILE)
    punteggi_df = inizializza_punteggi(PUNTEGGI_FILE)
    
    # Generate study calendar
    calendario_studio = genera_calendario_studio(
        argomenti_df, 
        GIORNI_STUDIO, 
        OGGI, 
        stato_argomenti_df
    )
    
    # Render main layout
    stato_argomenti_df, punteggi_df, chat_log = main_layout(
        argomenti_df,
        stato_argomenti_df,
        punteggi_df,
        calendario_studio,
        OGGI,
        DATA_ESAME,
        STATO_FILE,
        PUNTEGGI_FILE,
        st.session_state.chat_log
    )
    
    # Update session state
    st.session_state.chat_log = chat_log

if __name__ == "__main__":
    main()
