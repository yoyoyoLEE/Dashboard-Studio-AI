# dashboard_studio_orale.py

import time
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta
import streamlit as st
import os
import requests
import toml

# === PARAMETRI STUDIO ===
st.set_page_config(page_title="Studio Orale AS2B", layout="wide")
DATA_ESAME = datetime(2025, 9, 24)
OGGI = datetime.now().date()
GIORNI_STUDIO = (DATA_ESAME.date() - OGGI).days
STATO_FILE = "stato_argomenti.csv"
PUNTEGGI_FILE = "punteggi_test.csv"

# === CARICAMENTO ARGOMENTI ===
@st.cache_data
def carica_argomenti():
    df = pd.read_csv("argomenti_orali.csv")
    return df

@st.cache_data
def inizializza_punteggi():
    if not os.path.exists(PUNTEGGI_FILE):
        punteggi_df = pd.DataFrame(columns=["Argomento", "Punteggio", "Data", "Commento"])
        punteggi_df.to_csv(PUNTEGGI_FILE, index=False)
    else:
        punteggi_df = pd.read_csv(PUNTEGGI_FILE)
    return punteggi_df

@st.cache_data
def inizializza_stato_argomenti(df):
    if not os.path.exists(STATO_FILE):
        stato_df = pd.DataFrame({"Argomento": df["Argomento"], "Stato": "non iniziato"})
        stato_df.to_csv(STATO_FILE, index=False)
    else:
        stato_df = pd.read_csv(STATO_FILE)
        # Add any new topics that are not in the state file
        new_topics = df[~df["Argomento"].isin(stato_df["Argomento"])]
        if not new_topics.empty:
            new_rows = pd.DataFrame({
                "Argomento": new_topics["Argomento"],
                "Stato": "non iniziato"
            })
            stato_df = pd.concat([stato_df, new_rows], ignore_index=True)
            stato_df.to_csv(STATO_FILE, index=False)
    return stato_df

argomenti_df = carica_argomenti()
stato_argomenti_df = inizializza_stato_argomenti(argomenti_df)
punteggi_df = inizializza_punteggi()

# === CALENDARIO STUDIO AUTOMATICO MIGLIORATO ===
@st.cache_data
def genera_calendario_studio(df):
    # Calcola giorni totali e giorni di revisione
    giorni_totali = GIORNI_STUDIO
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
    
    giorni = [OGGI + timedelta(days=i) for i in range(giorni_totali)]
    calendario = pd.DataFrame({"Data": giorni, "Argomenti": distribuzione})
    return calendario

calendario_studio = genera_calendario_studio(argomenti_df)

# === SALVATAGGIO STATO ===
def aggiorna_stato_argomento(argomento, nuovo_stato):
    stato_argomenti_df.loc[stato_argomenti_df.Argomento == argomento, "Stato"] = nuovo_stato
    stato_argomenti_df.to_csv(STATO_FILE, index=False)
    st.toast(f"✅ Stato aggiornato: {argomento} → {nuovo_stato}")

# === CHAT LLM ===
def chiamata_llm(prompt):
    secrets = toml.load(".streamlit/secrets.toml")
    api_key = secrets["openrouter_api_key"]["openrouter_api_key"]
    model_id = secrets["openrouter_api_key"]["model"]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourapp.com",
        "X-Title": "Studio Orale AS2B"
    }

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ Errore LLM {response.status_code}: {response.text}"
    except Exception as e:
        return f"❌ Eccezione nella chiamata all'LLM: {str(e)}"


def salva_punteggio(argomento, punteggio, commento):
    global punteggi_df
    nuova_riga = pd.DataFrame({
        "Argomento": [argomento],
        "Punteggio": [punteggio],
        "Data": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Commento": [commento]
    })
    punteggi_df = pd.concat([punteggi_df, nuova_riga], ignore_index=True)
    punteggi_df.to_csv(PUNTEGGI_FILE, index=False)
    st.toast(f"✅ Punteggio salvato: {argomento} → {punteggio}/10")

def interazione_llm_su_argomento(argomento, modalita):
    if modalita == "studio":
        prompt = f"""Sei un tutor di lingua inglese. Spiega l'argomento seguente come se fosse una lezione:

Titolo: {argomento}

Struttura la spiegazione in 3 parti:
1. Introduzione teorica
2. Spiegazione dettagliata con esempi
3. Brevi domande per verificare la comprensione dello studente

Usa un tono chiaro e professionale."""
        aggiorna_stato_argomento(argomento, "completato")
        risposta = chiamata_llm(prompt)
        st.session_state.chat_log.append({"utente": f"Richiesta su '{argomento}' [{modalita}]", "llm": risposta})
    elif modalita == "test":
        # Imposta lo stato della sessione per il test
        st.session_state.test_in_corso = True
        st.session_state.test_argomento = argomento
        st.session_state.test_fase = "domanda"
        
        prompt = f"""Sei un esaminatore di lingua inglese. Crea una domanda di esame orale per il concorso AS2B basata sull'argomento:

"{argomento}"

Formula una singola domanda complessa che richieda conoscenza approfondita dell'argomento. La domanda deve essere chiara e specifica.
Rispondi SOLO con la domanda, senza introduzioni o spiegazioni aggiuntive."""
        
        aggiorna_stato_argomento(argomento, "da ripassare")
        risposta = chiamata_llm(prompt)
        st.session_state.test_domanda = risposta
        st.session_state.chat_log.append({"utente": f"Richiesta test su '{argomento}'", "llm": risposta})
    else:
        prompt = ""
        risposta = chiamata_llm(prompt)
        st.session_state.chat_log.append({"utente": f"Richiesta su '{argomento}' [{modalita}]", "llm": risposta})

# === CALENDARIO TRADIZIONALE ===
def mostra_calendario_tradizionale():
    st.subheader("📆 Calendario Studio Preparatorio")
    
    # Convert calendar dates to datetime
    calendario_studio['Data'] = pd.to_datetime(calendario_studio['Data'])
    
    # Get the start and end dates
    start_date = OGGI
    end_date = DATA_ESAME.date()
    
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
        default_index = months.index(OGGI.replace(day=1)) if OGGI.replace(day=1) in months else 0
        
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
                    style = "background: #e6f7ff; border-radius: 5px; padding: 5px;" if cell_date.date() == OGGI else ""
                    
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
                                        interazione_llm_su_argomento(topic, "studio")
                                        st.rerun()
                                    if st.button("📝", key=f"test_{cell_date.strftime('%Y%m%d')}_{topic}", 
                                                 help="Test questo argomento", 
                                                 use_container_width=True):
                                        interazione_llm_su_argomento(topic, "test")
                                        st.rerun()
                                    st.markdown("---")
                            else:
                                st.caption("Nessun argomento")
                    
                    current_day += 1
                    if current_day > max_days:
                        break
        
# === LISTA COMPLETA ARGOMENTI (SCORREVOLE) ===
def mostra_lista_completa_argomenti():
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
                    etichetta = {"non iniziato": "⚪ Critico", "da ripassare": "🟠 Da ripassare", "completato": "🟢 Completato"}.get(stato_corrente, "⚪ Critico")
                    
                    col1, col2, col3 = st.columns([5, 1, 1])
                    with col1:
                        st.markdown(f"{arg} - **{etichetta}**")
                    with col2:
                        if st.button("📖", key=f"studia_{full_arg}"):
                            interazione_llm_su_argomento(full_arg, "studio")
                    with col3:
                        if st.button("📝", key=f"test_{full_arg}"):
                            interazione_llm_su_argomento(full_arg, "test")

# === STUDIO GIORNALIERO (OGGI) ===
def mostra_tabella_oggi():
    st.markdown("### 📋 Studio del giorno: **" + str(OGGI.strftime("%A %d %B %Y")) + "**")
    oggi_row = calendario_studio[calendario_studio["Data"] == OGGI]
    if oggi_row.empty:
        st.success("Hai completato tutti gli argomenti! Usa il tempo per ripassare.")
    else:
        lista = oggi_row.iloc[0]["Argomenti"]
        for arg in lista:
            # Handle missing topics
            matches = stato_argomenti_df.loc[stato_argomenti_df.Argomento == arg, "Stato"]
            stato_corrente = matches.values[0] if not matches.empty else "non iniziato"
            etichetta = {"non iniziato": "⚪ Critico", "da ripassare": "🟠 Da ripassare", "completato": "🟢 Completato"}.get(stato_corrente, "⚪ Critico")
            
            col1, col2, col3 = st.columns([5, 1, 1])
            with col1:
                st.markdown(f"{arg} - **{etichetta}**")
            with col2:
                if st.button("📖", key=f"studia_oggi_{arg}"):
                    interazione_llm_su_argomento(arg, "studio")
            with col3:
                if st.button("📝", key=f"test_oggi_{arg}"):
                    interazione_llm_su_argomento(arg, "test")

# === BARRA AVANZAMENTO ===
def mostra_avanzamento():
    totale = len(stato_argomenti_df)
    completati = (stato_argomenti_df["Stato"] == "completato").sum()
    da_ripassare = (stato_argomenti_df["Stato"] == "da ripassare").sum()
    critici = totale - completati - da_ripassare
    percentuale = completati / totale if totale > 0 else 0
    st.markdown("### 📈 Avanzamento Complessivo")
    st.progress(percentuale, text=f"{int(percentuale*100)}% completato")
    st.write(f"🟢 Completati: {completati} | 🟠 Da ripassare: {da_ripassare} | ⚪ Critici: {critici}")

# === INTERFACCIA ===
def mostra_chat():
    st.markdown("### 💬 Chat con AI")
    
    # Chat history container with fixed height
    with st.container(height=400):
        for turno in st.session_state.chat_log:
            st.markdown(f"**🧑 Utente**: {turno['utente']}")
            st.markdown(f"**🤖 AI**: {turno['llm']}")
            st.divider()
    
    # Gestione del test in corso
    if "test_in_corso" in st.session_state and st.session_state.test_in_corso:
        if st.session_state.test_fase == "domanda":
            st.info(f"📝 **Test in corso su: {st.session_state.test_argomento}**")
            st.markdown(f"**Domanda**: {st.session_state.test_domanda}")
            
            # Callback per la risposta al test
            def submit_test_risposta():
                user_input = st.session_state.test_risposta
                if user_input:
                    st.session_state.test_risposta_utente = user_input
                    st.session_state.test_fase = "valutazione"
                    
                    # Richiedi valutazione all'LLM
                    prompt = f"""Sei un esaminatore di lingua inglese. Valuta la seguente risposta a una domanda di esame orale sul tema "{st.session_state.test_argomento}".

Domanda: {st.session_state.test_domanda}

Risposta dello studente: {user_input}

Valuta la risposta su una scala da 1 a 10 considerando:
- Accuratezza del contenuto (40%)
- Correttezza linguistica (30%)
- Chiarezza espositiva (30%)

Fornisci un punteggio numerico da 1 a 10 e un breve commento costruttivo che evidenzi punti di forza e aree di miglioramento.
Formatta la risposta così:
PUNTEGGIO: [numero da 1 a 10]
COMMENTO: [tuo commento]"""

                    risposta = chiamata_llm(prompt)
                    st.session_state.test_valutazione = risposta
                    
                    # Estrai punteggio e commento
                    try:
                        punteggio_match = risposta.split("PUNTEGGIO:")[1].split("\n")[0].strip()
                        punteggio = int(punteggio_match)
                        commento = risposta.split("COMMENTO:")[1].strip()
                    except:
                        punteggio = 5  # Default in caso di errore nel parsing
                        commento = risposta
                    
                    # Salva il punteggio
                    salva_punteggio(st.session_state.test_argomento, punteggio, commento)
                    
                    # Aggiorna chat log
                    st.session_state.chat_log.append({"utente": f"Risposta al test: {user_input}", "llm": risposta})
                    
                    # Reset test state
                    st.session_state.test_in_corso = False
                    st.session_state.test_fase = None
                    
                    # Forza refresh
                    st.rerun()
            
            # Text area per la risposta al test
            st.text_area(
                "Scrivi la tua risposta al test...", 
                key="test_risposta",
                height=150
            )
            
            # Pulsante per inviare la risposta
            st.button("Invia risposta", on_click=submit_test_risposta)
            
        elif st.session_state.test_fase == "valutazione":
            st.info(f"📊 **Valutazione del test su: {st.session_state.test_argomento}**")
            st.markdown(f"**Domanda**: {st.session_state.test_domanda}")
            st.markdown(f"**La tua risposta**: {st.session_state.test_risposta_utente}")
            st.markdown(f"**Valutazione**: {st.session_state.test_valutazione}")
            
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
                risposta = chiamata_llm(user_input)
                st.session_state.chat_log.append({"utente": user_input, "llm": risposta})
                # Clear input after processing
                st.session_state.chat_input = ""
        
        # Chat input with on_submit handler
        st.text_input(
            "Scrivi il tuo messaggio...", 
            key="chat_input",
            on_change=submit_chat
        )

def mostra_storico_punteggi():
    st.markdown("### 📊 Storico Punteggi Test")
    
    if punteggi_df.empty:
        st.info("Non hai ancora completato nessun test. Inizia a testare la tua conoscenza!")
    else:
        # Ordina per data più recente
        df_sorted = punteggi_df.sort_values(by="Data", ascending=False)
        
        # Visualizza in una tabella interattiva
        st.dataframe(
            df_sorted[["Argomento", "Punteggio", "Data"]],
            use_container_width=True,
            hide_index=True
        )
        
        # Visualizza grafico dell'andamento
        if len(df_sorted) > 1:
            st.markdown("#### Andamento Punteggi")
            df_plot = df_sorted.copy()
            df_plot["Data"] = pd.to_datetime(df_plot["Data"])
            df_plot = df_plot.sort_values(by="Data")
            
            # Crea grafico
            fig = ff.create_line_chart(
                df_plot["Data"].dt.strftime("%d/%m %H:%M"),
                df_plot["Punteggio"],
                colors=['#3366CC'],
                line_shape='linear'
            )
            
            # Personalizza layout
            fig.update_layout(
                xaxis_title="Data",
                yaxis_title="Punteggio",
                yaxis=dict(range=[0, 10]),
                height=300,
                margin=dict(l=20, r=20, t=30, b=20)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Statistiche
            media = df_sorted["Punteggio"].mean()
            ultimo = df_sorted.iloc[0]["Punteggio"]
            miglioramento = ultimo - df_sorted.iloc[-1]["Punteggio"] if len(df_sorted) > 1 else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Punteggio medio", f"{media:.1f}/10")
            col2.metric("Ultimo punteggio", f"{ultimo}/10")
            col3.metric("Trend", f"{miglioramento:+.1f}", delta_color="normal")

def main():
    st.title("🧠 Dashboard Studio Prova Orale – Classe AS2B")

    if "chat_log" not in st.session_state:
        st.session_state.chat_log = []

    col_sinistra, col_destra = st.columns([2, 1])
    
    with col_sinistra:
        tab1, tab2, tab3 = st.tabs(["📅 Oggi", "📚 Tutti gli argomenti", "📊 Storico Test"])
        
        with tab1:
            mostra_tabella_oggi()
            mostra_calendario_tradizionale()
            mostra_avanzamento()
            
        with tab2:
            mostra_lista_completa_argomenti()
            
        with tab3:
            mostra_storico_punteggi()
    
    with col_destra:
        mostra_chat()

main()
