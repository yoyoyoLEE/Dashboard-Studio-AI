"""
Page layouts for the Dashboard Studio application.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from src.ui.components import (
    mostra_calendario_tradizionale,
    mostra_lista_completa_argomenti,
    mostra_tabella_oggi,
    mostra_avanzamento,
    mostra_chat,
    mostra_storico_punteggi
)
from src.llm.api import interazione_llm_su_argomento

def main_layout(
    argomenti_df, 
    stato_argomenti_df, 
    punteggi_df, 
    calendario_studio, 
    oggi, 
    data_esame, 
    stato_file, 
    punteggi_file, 
    chat_log
):
    """
    Main application layout.
    
    Args:
        argomenti_df (pandas.DataFrame): DataFrame containing topics
        stato_argomenti_df (pandas.DataFrame): DataFrame containing topics state
        punteggi_df (pandas.DataFrame): DataFrame containing scores
        calendario_studio (pandas.DataFrame): DataFrame containing study calendar
        oggi (datetime.date): Current date
        data_esame (datetime.date): Exam date
        stato_file (str): Path to state file
        punteggi_file (str): Path to scores file
        chat_log (list): Chat history
        
    Returns:
        tuple: Updated state variables
    """
    st.title("🧠 Dashboard Studio Prova Orale – Classe AS2B")

    col_sinistra, col_destra = st.columns([2, 1])
    
    with col_sinistra:
        tab1, tab2, tab3 = st.tabs(["📅 Oggi", "📚 Tutti gli argomenti", "📊 Storico Test"])
        
        with tab1:
            # Mostra tabella oggi
            action = mostra_tabella_oggi(calendario_studio, oggi, stato_argomenti_df)
            if action:
                stato_argomenti_df, chat_log = interazione_llm_su_argomento(
                    action["topic"], 
                    action["action"], 
                    stato_argomenti_df, 
                    stato_file, 
                    punteggi_df, 
                    punteggi_file, 
                    chat_log
                )
                st.rerun()
            
            # Mostra calendario
            action = mostra_calendario_tradizionale(calendario_studio, oggi, data_esame)
            if action:
                stato_argomenti_df, chat_log = interazione_llm_su_argomento(
                    action["topic"], 
                    action["action"], 
                    stato_argomenti_df, 
                    stato_file, 
                    punteggi_df, 
                    punteggi_file, 
                    chat_log
                )
                st.rerun()
            
            # Mostra avanzamento
            mostra_avanzamento(stato_argomenti_df)
            
        with tab2:
            # Mostra lista completa argomenti
            action = mostra_lista_completa_argomenti(argomenti_df, stato_argomenti_df)
            if action:
                stato_argomenti_df, chat_log = interazione_llm_su_argomento(
                    action["topic"], 
                    action["action"], 
                    stato_argomenti_df, 
                    stato_file, 
                    punteggi_df, 
                    punteggi_file, 
                    chat_log
                )
                st.rerun()
            
        with tab3:
            # Mostra storico punteggi
            punteggi_df = mostra_storico_punteggi(punteggi_df, punteggi_file)
    
    with col_destra:
        # Mostra chat
        punteggi_df, stato_argomenti_df, chat_log = mostra_chat(
            chat_log, 
            stato_argomenti_df, 
            stato_file, 
            punteggi_df, 
            punteggi_file
        )
    
    return stato_argomenti_df, punteggi_df, chat_log
