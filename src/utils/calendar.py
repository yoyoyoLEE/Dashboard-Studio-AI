"""
Calendar generation utilities for the Dashboard Studio application.
"""

import pandas as pd
from datetime import datetime, timedelta

def genera_calendario_studio(df, giorni_studio, oggi, stato_argomenti_df):
    """
    Generate study calendar.
    
    Args:
        df (pandas.DataFrame): DataFrame containing topics
        giorni_studio (int): Number of days until exam
        oggi (datetime.date): Current date
        stato_argomenti_df (pandas.DataFrame): DataFrame containing topics state
        
    Returns:
        pandas.DataFrame: DataFrame containing study calendar
    """
    # Calcola giorni totali e giorni di revisione
    giorni_totali = giorni_studio
    giorni_revisione = max(7, int(giorni_totali * 0.1))  # 10% dei giorni per revisione
    giorni_studio_effettivi = giorni_totali - giorni_revisione
    
    # Ottieni lista argomenti
    argomenti = df['Argomento'].tolist()
    
    # Distribuzione più intelligente
    distribuzione = [[] for _ in range(giorni_totali)]
    
    # Fase 1: Distribuzione iniziale
    for idx, arg in enumerate(argomenti):
        giorno_target = idx % giorni_studio_effettivi
        distribuzione[giorno_target].append(arg)
    
    # Fase 2: Aggiungi sessioni di ripasso mirato
    argomenti_da_ripassare = stato_argomenti_df[
        (stato_argomenti_df["Stato"] == "non iniziato") | 
        (stato_argomenti_df["Stato"] == "da ripassare")
    ]["Argomento"].tolist()
    
    # Distribuisci gli argomenti da ripassare nei giorni di revisione
    for idx, giorno in enumerate(range(giorni_studio_effettivi, giorni_totali)):
        if idx < len(argomenti_da_ripassare):
            distribuzione[giorno] = [argomenti_da_ripassare[idx]]
        else:
            # Se ci sono più giorni di revisione che argomenti, ripeti gli argomenti più critici
            distribuzione[giorno] = ["Ripasso approfondito"]
    
    giorni = [oggi + timedelta(days=i) for i in range(giorni_totali)]
    calendario = pd.DataFrame({"Data": giorni, "Argomenti": distribuzione})
    return calendario
