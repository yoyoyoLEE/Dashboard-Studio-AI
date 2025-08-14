"""
State management utilities for the Dashboard Studio application.
"""

import streamlit as st
import pandas as pd

def aggiorna_stato_argomento(stato_argomenti_df, argomento, nuovo_stato, stato_file):
    """
    Update topic state.
    
    Args:
        stato_argomenti_df (pandas.DataFrame): DataFrame containing topics state
        argomento (str): Topic name
        nuovo_stato (str): New state
        stato_file (str): Path to state file
        
    Returns:
        pandas.DataFrame: Updated DataFrame containing topics state
    """
    stato_argomenti_df.loc[stato_argomenti_df.Argomento == argomento, "Stato"] = nuovo_stato
    stato_argomenti_df.to_csv(stato_file, index=False)
    st.toast(f"✅ Stato aggiornato: {argomento} → {nuovo_stato}")
    return stato_argomenti_df

def elimina_test(punteggi_df, argomento, data, punteggi_file, file_path=None):
    """
    Delete test from history.
    
    Args:
        punteggi_df (pandas.DataFrame): DataFrame containing scores
        argomento (str): Topic name
        data (str): Test date
        punteggi_file (str): Path to scores file
        file_path (str, optional): Path to test file
        
    Returns:
        pandas.DataFrame: Updated DataFrame containing scores
    """
    import os
    
    # Trova la riga corrispondente all'argomento e alla data
    mask = (punteggi_df["Argomento"] == argomento) & (punteggi_df["Data"] == data)
    
    if mask.any():
        # Rimuovi la riga dal dataframe
        punteggi_df = punteggi_df[~mask].reset_index(drop=True)
        
        # Salva immediatamente le modifiche
        punteggi_df.to_csv(punteggi_file, index=False)
        
        # Aggiorna anche la sessione per mantenere la coerenza tra refresh
        if "punteggi_df" in st.session_state:
            st.session_state.punteggi_df = punteggi_df
        
        # Se è fornito un percorso file, elimina anche il file di test
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                st.error(f"Errore nell'eliminazione del file: {str(e)}")
        
        # Notifica all'utente
        st.toast("✅ Test eliminato con successo")
        st.success("Test eliminato con successo! La pagina verrà aggiornata.")
    else:
        st.error("Test non trovato nel database")
    
    return punteggi_df
