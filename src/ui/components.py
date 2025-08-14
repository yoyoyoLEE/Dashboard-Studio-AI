"""
UI components for the Dashboard Studio application.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

from src.llm.api import interazione_llm_su_argomento, submit_test_risposta, chiamata_llm
from src.utils.state import aggiorna_stato_argomento, elimina_test

def mostra_calendario_tradizionale(calendario_studio, oggi, data_esame):
    """
    Display traditional calendar.
    
    Args:
        calendario_studio (pandas.DataFrame): DataFrame containing study calendar
        oggi (datetime.date): Current date
        data_esame (datetime.date): Exam date
    """
    st.subheader("📆 Calendario Studio Preparatorio")
    
    # Convert calendar dates to datetime
    calendario_studio['Data'] = pd.to_datetime(calendario_studio['Data'])
    
    # Get the start and end dates
    start_date = oggi
    end_date = data_esame.date()
    
    # Create a container for the calendar
    calendar_container = st.container()
    
    with calendar_container:
        # Generate list of months
        months = []
        current = start_date.replace(day=1)
        end_month = end_date.replace(day=1)
        while current <= end_month:
            months.append(current)
            if current.month == 12:
                current = current.replace(year=current.year+1, month=1)
            else:
                current = current.replace(month=current.month+1)
        
        # Default to current month
        default_index = months.index(oggi.replace(day=1)) if oggi.replace(day=1) in months else 0
        
        # Month selection dropdown
        selected_month = st.selectbox(
            "Seleziona mese", 
            months, 
            format_func=lambda d: d.strftime("%B %Y"),
            index=default_index
        )
        
        # Display selected month
        st.subheader(f"{selected_month.strftime('%B %Y')}")
        
        # Create calendar grid
        col_names = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
        cols = st.columns(7)
        for i, col in enumerate(cols):
            col.write(f"**{col_names[i]}**")
        
        # Calculate starting day offset
        start_offset = selected_month.weekday()
        current_day = 1
        max_days = (selected_month.replace(month=selected_month.month+1, day=1) - timedelta(days=1)).day
        
        # Generate calendar rows
        while current_day <= max_days:
            row = st.columns(7)
            for i in range(7):
                if (current_day == 1 and i < start_offset) or current_day > max_days:
                    row[i].write("")
                else:
                    cell_date = datetime(selected_month.year, selected_month.month, current_day)
                    # Get topics for this day
                    day_topics = calendario_studio[calendario_studio['Data'].dt.date == cell_date.date()]['Argomenti']
                    topics = day_topics.iloc[0] if not day_topics.empty else []
                    
                    # Style current day
                    style = "background: #e6f7ff; border-radius: 5px; padding: 5px;" if cell_date.date() == oggi else ""
                    
                    with row[i]:
                        # Use expander for each day to show topics
                        with st.expander(f"{current_day}{' 📚' if topics else ''}"):
                            if topics:
                                for topic in topics:
                                    st.caption(topic)  # Smaller text size
                                    # Icon-only buttons with tooltips
                                    if st.button("📖", key=f"studia_{cell_date.strftime('%Y%m%d')}_{topic}", 
                                                 help="Studia questo argomento", 
                                                 use_container_width=True):
                                        return {"action": "studio", "topic": topic}
                                    if st.button("📝", key=f"test_{cell_date.strftime('%Y%m%d')}_{topic}", 
                                                 help="Test questo argomento", 
                                                 use_container_width=True):
                                        return {"action": "test", "topic": topic}
                                    st.markdown("---")
                            else:
                                st.caption("Nessun argomento")
                    
                    current_day += 1
                    if current_day > max_days:
                        break
    
    return None

def mostra_lista_completa_argomenti(argomenti_df, stato_argomenti_df):
    """
    Display complete list of topics.
    
    Args:
        argomenti_df (pandas.DataFrame): DataFrame containing topics
        stato_argomenti_df (pandas.DataFrame): DataFrame containing topics state
        
    Returns:
        dict or None: Action to perform
    """
    st.markdown("### 📚 Lista Completa Argomenti")
    
    # Group topics by macro category
    macro_argomenti = {}
    for argomento in argomenti_df['Argomento']:
        if ':' in argomento:
            macro, sub = argomento.split(':', 1)
            if macro not in macro_argomenti:
                macro_argomenti[macro] = []
            macro_argomenti[macro].append(sub.strip())
        else:
            if "Generale" not in macro_argomenti:
                macro_argomenti["Generale"] = []
            macro_argomenti["Generale"].append(argomento)
    
    # Display in scrollable container
    with st.container(height=400):
        for macro, argomenti in macro_argomenti.items():
            with st.expander(f"**{macro}**"):
                for arg in argomenti:
                    full_arg = f"{macro}: {arg}" if macro != "Generale" else arg
                    # Handle missing topics
                    matches = stato_argomenti_df.loc[stato_argomenti_df.Argomento == full_arg, "Stato"]
                    stato_corrente = matches.values[0] if not matches.empty else "non iniziato"
                    # Etichette aggiornate secondo la nuova logica:
                    # - Completati: dopo aver fatto il test dell'argomento
                    # - Da ripassare: se hai fatto solo la funzione studio dell'argomento
                    # - Critici: se non è stato fatto nessuno dei due
                    etichetta = {"non iniziato": "⚪ Critico", "da ripassare": "🟠 Da ripassare", "completato": "🟢 Completato"}.get(stato_corrente, "⚪ Critico")
                    
                    col1, col2, col3 = st.columns([5, 1, 1])
                    with col1:
                        st.markdown(f"{arg} - **{etichetta}**")
                    with col2:
                        if st.button("📖", key=f"studia_{full_arg}"):
                            return {"action": "studio", "topic": full_arg}
                    with col3:
                        if st.button("📝", key=f"test_{full_arg}"):
                            return {"action": "test", "topic": full_arg}
    
    return None

def mostra_tabella_oggi(calendario_studio, oggi, stato_argomenti_df):
    """
    Display today's study table.
    
    Args:
        calendario_studio (pandas.DataFrame): DataFrame containing study calendar
        oggi (datetime.date): Current date
        stato_argomenti_df (pandas.DataFrame): DataFrame containing topics state
        
    Returns:
        dict or None: Action to perform
    """
    st.markdown("### 📋 Studio del giorno: **" + str(oggi.strftime("%A %d %B %Y")) + "**")
    oggi_row = calendario_studio[calendario_studio["Data"] == oggi]
    if oggi_row.empty:
        st.success("Hai completato tutti gli argomenti! Usa il tempo per ripassare.")
    else:
        lista = oggi_row.iloc[0]["Argomenti"]
        for arg in lista:
            # Handle missing topics
            matches = stato_argomenti_df.loc[stato_argomenti_df.Argomento == arg, "Stato"]
            stato_corrente = matches.values[0] if not matches.empty else "non iniziato"
            # Etichette aggiornate secondo la nuova logica:
            # - Completati: dopo aver fatto il test dell'argomento
            # - Da ripassare: se hai fatto solo la funzione studio dell'argomento
            # - Critici: se non è stato fatto nessuno dei due
            etichetta = {"non iniziato": "⚪ Critico", "da ripassare": "🟠 Da ripassare", "completato": "🟢 Completato"}.get(stato_corrente, "⚪ Critico")
            
            col1, col2, col3 = st.columns([5, 1, 1])
            with col1:
                st.markdown(f"{arg} - **{etichetta}**")
            with col2:
                if st.button("📖", key=f"studia_oggi_{arg}"):
                    return {"action": "studio", "topic": arg}
            with col3:
                if st.button("📝", key=f"test_oggi_{arg}"):
                    return {"action": "test", "topic": arg}
    
    return None

def mostra_avanzamento(stato_argomenti_df):
    """
    Display progress.
    
    Args:
        stato_argomenti_df (pandas.DataFrame): DataFrame containing topics state
    """
    totale = len(stato_argomenti_df)
    completati = (stato_argomenti_df["Stato"] == "completato").sum()
    da_ripassare = (stato_argomenti_df["Stato"] == "da ripassare").sum()
    critici = totale - completati - da_ripassare
    percentuale = completati / totale if totale > 0 else 0
    st.markdown("### 📈 Avanzamento Complessivo")
    st.progress(percentuale, text=f"{int(percentuale*100)}% completato")
    st.write(f"🟢 Completati: {completati} | 🟠 Da ripassare: {da_ripassare} | ⚪ Critici: {critici}")

def mostra_chat(chat_log, stato_argomenti_df, stato_file, punteggi_df, punteggi_file):
    """
    Display chat interface.
    
    Args:
        chat_log (list): Chat history
        stato_argomenti_df (pandas.DataFrame): DataFrame containing topics state
        stato_file (str): Path to state file
        punteggi_df (pandas.DataFrame): DataFrame containing scores
        punteggi_file (str): Path to scores file
        
    Returns:
        tuple: Updated state variables
    """
    st.markdown("### 💬 Chat con AI")
    
    # Initialize session state variables if they don't exist
    if "test_valutazione" not in st.session_state:
        st.session_state.test_valutazione = ""
    
    if "test_risposta_modello" not in st.session_state:
        st.session_state.test_risposta_modello = ""
    
    if "test_risposta_utente" not in st.session_state:
        st.session_state.test_risposta_utente = ""
    
    if "test_domanda" not in st.session_state:
        st.session_state.test_domanda = ""
    
    if "test_argomento" not in st.session_state:
        st.session_state.test_argomento = ""
    
    # Chat history container with fixed height
    with st.container(height=400):
        for turno in chat_log:
            # Verifica se è una risposta a un test
            if turno['utente'].startswith("Risposta al test:"):
                # Formatta in modo speciale le risposte ai test per renderle più visibili
                st.markdown("---")
                st.markdown("📝 **Test completato**")
                st.markdown(f"**🧑 La tua risposta**: {turno['utente'].replace('Risposta al test: ', '')}")
                st.markdown(f"**🤖 Valutazione**: {turno['llm']}")
                
                # Mostra la risposta modello se disponibile
                if "test_risposta_modello" in st.session_state:
                    with st.expander("Mostra risposta modello", expanded=False):
                        st.markdown("**Risposta modello**:")
                        st.markdown(st.session_state.test_risposta_modello)
                
                st.markdown("---")
            else:
                # Formattazione standard per le altre interazioni
                st.markdown(f"**🧑 Utente**: {turno['utente']}")
                st.markdown(f"**🤖 AI**: {turno['llm']}")
                st.divider()
    
    # Gestione del test in corso
    if "test_in_corso" in st.session_state and st.session_state.test_in_corso:
        if "test_fase" in st.session_state and st.session_state.test_fase == "domanda":
            st.info(f"📝 **Test in corso su: {st.session_state.test_argomento}**")
            st.markdown(f"**Domanda**: {st.session_state.test_domanda}")
            
            # Callback per la risposta al test
            def submit_test_risposta_callback():
                user_input = st.session_state.test_risposta
                if user_input:
                    # Salva la risposta dell'utente nella sessione e mostra immediatamente
                    st.session_state.test_risposta_utente = user_input
                    st.session_state.test_fase = "valutazione"
                    
                    # Chiama la funzione di valutazione
                    punteggi_df_updated, stato_argomenti_df_updated, valutazione, chat_log_updated = submit_test_risposta(
                        user_input,
                        st.session_state.test_argomento,
                        st.session_state.test_domanda,
                        st.session_state.test_risposta_modello,
                        st.session_state.test_file_path,
                        punteggi_df,
                        punteggi_file,
                        stato_argomenti_df,
                        stato_file,
                        chat_log
                    )
                    
                    # Aggiorna le variabili di stato
                    st.session_state.test_valutazione = valutazione
                    
                    # Restituisci i dataframe aggiornati
                    return punteggi_df_updated, stato_argomenti_df_updated, chat_log_updated
            
            # Text area per la risposta al test
            st.text_area(
                "Scrivi la tua risposta al test...", 
                key="test_risposta",
                height=150
            )
            
            # Pulsante per inviare la risposta
            if st.button("Invia risposta"):
                punteggi_df, stato_argomenti_df, chat_log = submit_test_risposta_callback()
                st.rerun()
            
            return punteggi_df, stato_argomenti_df, chat_log
            
        elif "test_fase" in st.session_state and st.session_state.test_fase == "valutazione":
            # Mostra la valutazione in un box evidenziato
            with st.container(border=True):
                st.info(f"📊 **Valutazione del test su: {st.session_state.test_argomento}**")
                st.markdown(f"**Domanda**: {st.session_state.test_domanda}")
                st.markdown(f"**La tua risposta**: {st.session_state.test_risposta_utente}")
                st.markdown(f"**Valutazione**: {st.session_state.test_valutazione}")
                
                # Mostra la risposta modello
                with st.expander("Mostra risposta modello", expanded=True):
                    st.markdown("**Risposta modello**:")
                    st.markdown(st.session_state.test_risposta_modello)
                
                # Pulsante per terminare il test
                if st.button("Chiudi valutazione"):
                    st.session_state.test_in_corso = False
                    st.session_state.test_fase = None
                    st.rerun()
    else:
        # Use a callback to handle chat submission
        def submit_chat():
            user_input = st.session_state.chat_input
            if user_input:
                # Add instruction to respond in English
                enhanced_prompt = f"{user_input}\n\nPlease respond in English only."
                risposta = chiamata_llm(enhanced_prompt, max_tokens=500, temperature=0.7)
                chat_log.append({"utente": user_input, "llm": risposta})
                # Clear input after processing
                st.session_state.chat_input = ""
        
        # Chat input with on_submit handler
        st.text_input(
            "Scrivi il tuo messaggio...", 
            key="chat_input",
            on_change=submit_chat
        )
    
    return punteggi_df, stato_argomenti_df, chat_log

def mostra_storico_punteggi(punteggi_df, punteggi_file):
    """
    Display test scores history.
    
    Args:
        punteggi_df (pandas.DataFrame): DataFrame containing scores
        punteggi_file (str): Path to scores file
        
    Returns:
        pandas.DataFrame: Updated DataFrame containing scores
    """
    st.markdown("### 📊 Storico Punteggi Test")
    
    # Aggiorna punteggi_df dalla sessione se disponibile
    if "punteggi_df" in st.session_state:
        punteggi_df = st.session_state.punteggi_df
    else:
        # Inizializza nella sessione
        st.session_state.punteggi_df = punteggi_df
    
    if punteggi_df.empty:
        st.info("Non hai ancora completato nessun test. Inizia a testare la tua conoscenza!")
    else:
        # Ordina per data più recente
        df_sorted = punteggi_df.sort_values(by="Data", ascending=False).reset_index(drop=True)
        
        # Crea una tabella interattiva con pulsanti di eliminazione
        for i, row in df_sorted.iterrows():
            col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
            with col1:
                st.write(f"**{row['Argomento']}**")
            with col2:
                st.write(f"**{row['Punteggio']}/100**")
            with col3:
                st.write(f"{row['Data']}")
            with col4:
                if st.button("🗑️", key=f"delete_test_{i}", help="Elimina questo test"):
                    # Passa l'argomento e la data per identificare univocamente il test
                    punteggi_df = elimina_test(punteggi_df, row['Argomento'], row['Data'], punteggi_file)
                    # Forza il refresh della pagina
                    st.rerun()
        
        # Visualizza grafico dell'andamento
        if len(df_sorted) > 1:
            st.markdown("#### Andamento Punteggi")
            df_plot = df_sorted.copy()
            df_plot["Data"] = pd.to_datetime(df_plot["Data"])
            df_plot = df_plot.sort_values(by="Data")
            
            # Crea grafico con plotly.graph_objects
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_plot["Data"].dt.strftime("%d/%m %H:%M"),
                y=df_plot["Punteggio"],
                mode='lines+markers',
                line=dict(color='#3366CC', shape='linear'),
                name='Punteggio'
            ))
            
            # Personalizza layout
            fig.update_layout(
                xaxis_title="Data",
                yaxis_title="Punteggio",
                yaxis=dict(range=[0, 100]),
                height=300,
                margin=dict(l=20, r=20, t=30, b=20)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Statistiche
            media = df_sorted["Punteggio"].mean()
            ultimo = df_sorted.iloc[0]["Punteggio"]
            miglioramento = ultimo - df_sorted.iloc[-1]["Punteggio"] if len(df_sorted) > 1 else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Punteggio medio", f"{media:.1f}/100")
            col2.metric("Ultimo punteggio", f"{ultimo}/100")
            col3.metric("Trend", f"{miglioramento:+.1f}", delta_color="normal")
        
        # Aggiungi visualizzazione dei file di test salvati
        st.markdown("#### 📝 Storico Dettagliato Test")
        
        temp_dir = "temp_test_files"
        if os.path.exists(temp_dir):
            test_files = [f for f in os.listdir(temp_dir) if f.startswith("test_") and f.endswith(".txt")]
            
            if test_files:
                for idx, file in enumerate(sorted(test_files, reverse=True)):
                    # Estrai l'argomento dal nome del file
                    argomento = file.replace("test_", "").split("_")[0].replace("_", " ")
                    file_path = os.path.join(temp_dir, file)
                    
                    # Crea un expander con pulsante di eliminazione
                    with st.expander(f"Test: {argomento}"):
                        col1, col2 = st.columns([10, 1])
                        with col2:
                            if st.button("🗑️", key=f"delete_file_{idx}", help="Elimina questo file di test"):
                                # Trova la riga corrispondente nel dataframe dei punteggi
                                matching_rows = df_sorted[df_sorted["Argomento"] == argomento]
                                if not matching_rows.empty:
                                    # Prendi la prima corrispondenza
                                    row = matching_rows.iloc[0]
                                    punteggi_df = elimina_test(punteggi_df, row['Argomento'], row['Data'], punteggi_file, file_path)
                                else:
                                    # Se non c'è corrispondenza nel dataframe, elimina solo il file
                                    os.remove(file_path)
                                    st.toast("✅ File di test eliminato con successo")
                                    st.success("File di test eliminato con successo! La pagina verrà aggiornata.")
                                # Forza il refresh della pagina
                                st.rerun()
                        
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                            st.text_area("Dettagli del test", content, height=300, disabled=True)
                        except Exception as e:
                            st.error(f"Errore nel leggere il file: {str(e)}")
            else:
                st.info("Nessun file di test dettagliato disponibile.")
        else:
            st.info("La directory per i file di test dettagliati non esiste ancora. Completa un test per generarla.")
    
    return punteggi_df
