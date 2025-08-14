"""
Data loading and initialization module for the Dashboard Studio application.
"""

import os
import pandas as pd
import streamlit as st

def carica_argomenti():
    """
    Load topics from CSV file.
    
    Returns:
        pandas.DataFrame: DataFrame containing topics
    """
    df = pd.read_csv("argomenti_orali.csv")
    return df

def inizializza_punteggi(punteggi_file):
    """
    Initialize scores DataFrame.
    
    Args:
        punteggi_file (str): Path to scores file
        
    Returns:
        pandas.DataFrame: DataFrame containing scores
    """
    if not os.path.exists(punteggi_file):
        punteggi_df = pd.DataFrame(columns=["Argomento", "Punteggio", "Data", "Commento"])
        punteggi_df.to_csv(punteggi_file, index=False)
    else:
        punteggi_df = pd.read_csv(punteggi_file)
    return punteggi_df

def inizializza_stato_argomenti(df, stato_file):
    """
    Initialize topics state DataFrame.
    
    Args:
        df (pandas.DataFrame): DataFrame containing topics
        stato_file (str): Path to state file
        
    Returns:
        pandas.DataFrame: DataFrame containing topics state
    """
    if not os.path.exists(stato_file):
        stato_df = pd.DataFrame({"Argomento": df["Argomento"], "Stato": "non iniziato"})
        stato_df.to_csv(stato_file, index=False)
    else:
        stato_df = pd.read_csv(stato_file)
        # Add any new topics that are not in the state file
        new_topics = df[~df["Argomento"].isin(stato_df["Argomento"])]
        if not new_topics.empty:
            new_rows = pd.DataFrame({
                "Argomento": new_topics["Argomento"],
                "Stato": "non iniziato"
            })
            stato_df = pd.concat([stato_df, new_rows], ignore_index=True)
            stato_df.to_csv(stato_file, index=False)
    return stato_df

def salva_punteggio(punteggi_df, argomento, punteggio, commento, punteggi_file):
    """
    Save score for a topic.
    
    Args:
        punteggi_df (pandas.DataFrame): DataFrame containing scores
        argomento (str): Topic name
        punteggio (int): Score value
        commento (str): Comment
        punteggi_file (str): Path to scores file
        
    Returns:
        pandas.DataFrame: Updated DataFrame containing scores
    """
    from datetime import datetime
    
    nuova_riga = pd.DataFrame({
        "Argomento": [argomento],
        "Punteggio": [punteggio],
        "Data": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Commento": [commento]
    })
    punteggi_df = pd.concat([punteggi_df, nuova_riga], ignore_index=True)
    punteggi_df.to_csv(punteggi_file, index=False)
    st.toast(f"✅ Punteggio salvato: {argomento} → {punteggio}/10")
    return punteggi_df
