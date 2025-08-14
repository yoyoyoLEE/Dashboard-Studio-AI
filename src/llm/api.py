"""
LLM API integration for the Dashboard Studio application.
"""

import requests
import toml
import asyncio
import aiohttp
import streamlit as st
import os
import time

def chiamata_llm(prompt, max_tokens=500, temperature=0.7):
    """
    Call LLM API.
    
    Args:
        prompt (str): Prompt text
        max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 500.
        temperature (float, optional): Temperature parameter. Defaults to 0.7.
        
    Returns:
        str: LLM response
    """
    try:
        # Carica il file secrets.toml
        secrets = toml.load(".streamlit/secrets.toml")
        
        # Access to the secrets structure
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
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            if response.status_code == 200:
                json_response = response.json()
                if "choices" in json_response and len(json_response["choices"]) > 0:
                    return json_response["choices"][0]["message"]["content"]
                else:
                    return f"❌ Errore API: Risposta non valida: {json_response}"
            else:
                return f"❌ Errore API: {response.status_code}: {response.text}"
        except Exception as e:
            return f"❌ Errore nella chiamata API: {str(e)}"
    
    except FileNotFoundError:
        return f"❌ File secrets.toml non trovato. Assicurati che il file esista nella directory .streamlit"
    
    except Exception as e:
        return f"❌ Errore nella configurazione LLM: {str(e)}"


async def async_chiamata_llm(prompt, max_tokens=500, temperature=0.7):
    """
    Asynchronous version of LLM API call.
    
    Args:
        prompt (str): Prompt text
        max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 500.
        temperature (float, optional): Temperature parameter. Defaults to 0.7.
        
    Returns:
        str: LLM response
    """
    try:
        # Carica il file secrets.toml
        secrets = toml.load(".streamlit/secrets.toml")
        
        # Access to the secrets structure
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
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions", 
                headers=headers, 
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    else:
                        return f"❌ Errore API: Risposta non valida: {result}"
                else:
                    text = await response.text()
                    return f"❌ Errore API: {response.status}: {text}"
    
    except Exception as e:
        return f"❌ Errore nella chiamata API asincrona: {str(e)}"


async def parallel_llm_calls(prompts):
    """
    Execute multiple LLM calls in parallel.
    
    Args:
        prompts (list): List of prompts
        
    Returns:
        list: List of LLM responses
    """
    tasks = [async_chiamata_llm(prompt) for prompt in prompts]
    return await asyncio.gather(*tasks)


def run_parallel_llm_calls(prompts):
    """
    Wrapper to execute parallel LLM calls from synchronous code.
    
    Args:
        prompts (list): List of prompts
        
    Returns:
        list: List of LLM responses
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(parallel_llm_calls(prompts))
    finally:
        loop.close()
    return results


@st.cache_data
def cached_llm_studio(argomento):
    """
    Cached version of LLM call for topic study.
    
    Args:
        argomento (str): Topic name
        
    Returns:
        str: LLM response
    """
    prompt = f"""You are an English language tutor. Explain the following topic as if it were a lesson:

Topic: {argomento}

Structure your explanation in 3 parts:
1. Theoretical introduction
2. Detailed explanation with examples
3. Brief questions to verify student understanding

Use a clear and professional tone. RESPOND ONLY IN ENGLISH."""
    return chiamata_llm(prompt, max_tokens=800, temperature=0.7)


def interazione_llm_su_argomento(argomento, modalita, stato_argomenti_df, stato_file, punteggi_df, punteggi_file, chat_log):
    """
    Interact with LLM on a topic.
    
    Args:
        argomento (str): Topic name
        modalita (str): Interaction mode ('studio' or 'test')
        stato_argomenti_df (pandas.DataFrame): DataFrame containing topics state
        stato_file (str): Path to state file
        punteggi_df (pandas.DataFrame): DataFrame containing scores
        punteggi_file (str): Path to scores file
        chat_log (list): Chat history
        
    Returns:
        tuple: Updated state and session variables
    """
    from src.utils.state import aggiorna_stato_argomento
    from src.data.loader import salva_punteggio
    
    if modalita == "studio":
        # Usa la versione cached per lo studio
        stato_argomenti_df = aggiorna_stato_argomento(stato_argomenti_df, argomento, "da ripassare", stato_file)
        risposta = cached_llm_studio(argomento)
        chat_log.append({"utente": f"Richiesta su '{argomento}' [{modalita}]", "llm": risposta})
    elif modalita == "test":
        # Imposta lo stato della sessione per il test
        st.session_state.test_in_corso = True
        st.session_state.test_argomento = argomento
        st.session_state.test_fase = "domanda"
        
        # Usa metodo sequenziale per maggiore affidabilità
        with st.spinner("Generazione domanda di test..."):
            # Prepara il prompt per la domanda
            prompt_domanda = f"""English examiner. Create an oral exam question on:
"{argomento}"
Complex question requiring in-depth knowledge. Clear and specific.
QUESTION ONLY. NO INTRODUCTION. ENGLISH ONLY."""
            
            # Genera la domanda
            domanda = chiamata_llm(prompt_domanda, max_tokens=300, temperature=0.7)
            
            # Verifica se la domanda è stata generata correttamente
            if domanda.startswith("Errore") or "❌" in domanda:
                # Se c'è un errore nella generazione della domanda, usa una domanda predefinita
                domanda = f"Explain the key concepts of {argomento} and provide examples."
            
            # Prepara il prompt per la risposta modello
            prompt_risposta_modello = f"""English expert. Answer this question about {argomento}:
Question: {domanda}
Comprehensive, well-structured answer (perfect score). Include terminology, examples.
250-300 words. ENGLISH ONLY."""
            
            # Genera la risposta modello
            risposta_modello = chiamata_llm(prompt_risposta_modello, max_tokens=800, temperature=0.5)
            
            # Verifica se la risposta modello è stata generata correttamente
            if risposta_modello.startswith("Errore") or "❌" in risposta_modello:
                # Se c'è un errore nella generazione della risposta modello, usa una risposta predefinita
                risposta_modello = f"This would be a model answer for the question about {argomento}. In a real scenario, this would contain a comprehensive explanation of the topic with examples and proper terminology."
        
        # Salva i risultati nella sessione
        st.session_state.test_domanda = domanda
        st.session_state.test_risposta_modello = risposta_modello
        
        # Aggiungi la risposta modello alla sessione per mostrarla nell'interfaccia
        st.session_state.mostra_risposta_modello = True
        
        # Salva la domanda e la risposta modello in un file temporaneo
        import tempfile
        import os
        
        # Crea una directory temporanea se non esiste
        temp_dir = "temp_test_files"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # Crea un nome file basato sull'argomento e timestamp
        timestamp = int(time.time())
        filename = f"{temp_dir}/test_{argomento.replace(' ', '_').replace(':', '_')}_{timestamp}.txt"
        
        # Salva domanda e risposta modello nel file
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"ARGOMENTO: {argomento}\n\n")
            f.write(f"DOMANDA: {domanda}\n\n")
            f.write(f"RISPOSTA MODELLO: {risposta_modello}\n\n")
            f.write("RISPOSTA UTENTE: [Sarà aggiunta dopo la risposta dell'utente]\n\n")
            f.write("VALUTAZIONE: [Sarà aggiunta dopo la valutazione]\n\n")
        
        # Salva il percorso del file nella sessione
        st.session_state.test_file_path = filename
        
        # Aggiungi alla chat log solo la domanda
        chat_log.append({"utente": f"Richiesta test su '{argomento}'", "llm": domanda})
    else:
        prompt = "Please respond in English only."
        risposta = chiamata_llm(prompt, max_tokens=300, temperature=0.7)
        chat_log.append({"utente": f"Richiesta su '{argomento}' [{modalita}]", "llm": risposta})
    
    return stato_argomenti_df, chat_log


def submit_test_risposta(user_input, test_argomento, test_domanda, test_risposta_modello, test_file_path, 
                         punteggi_df, punteggi_file, stato_argomenti_df, stato_file, chat_log):
    """
    Submit test response.
    
    Args:
        user_input (str): User's response
        test_argomento (str): Topic name
        test_domanda (str): Test question
        test_risposta_modello (str): Model answer
        test_file_path (str): Path to test file
        punteggi_df (pandas.DataFrame): DataFrame containing scores
        punteggi_file (str): Path to scores file
        stato_argomenti_df (pandas.DataFrame): DataFrame containing topics state
        stato_file (str): Path to state file
        chat_log (list): Chat history
        
    Returns:
        tuple: Updated state and session variables
    """
    from src.utils.state import aggiorna_stato_argomento
    from src.data.loader import salva_punteggio
    
    # Aggiorna il file temporaneo con la risposta dell'utente
    content = ""
    if os.path.exists(test_file_path):
        try:
            with open(test_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            content = content.replace("RISPOSTA UTENTE: [Sarà aggiunta dopo la risposta dell'utente]", f"RISPOSTA UTENTE: {user_input}")
            
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            st.error(f"Errore nell'aggiornamento del file: {str(e)}")
    else:
        # Se il file non esiste, crea un nuovo file
        content = f"ARGOMENTO: {test_argomento}\n\n"
        content += f"DOMANDA: {test_domanda}\n\n"
        content += f"RISPOSTA MODELLO: {test_risposta_modello}\n\n"
        content += f"RISPOSTA UTENTE: {user_input}\n\n"
        content += "VALUTAZIONE: [Sarà aggiunta dopo la valutazione]\n\n"
        
        # Crea una directory temporanea se non esiste
        temp_dir = "temp_test_files"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # Crea un nuovo file
        timestamp = int(time.time())
        test_file_path = f"{temp_dir}/test_{test_argomento.replace(' ', '_').replace(':', '_')}_{timestamp}.txt"
        
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Aggiorna il percorso del file nella sessione
        st.session_state.test_file_path = test_file_path
    
    # Richiedi valutazione all'LLM confrontando con la risposta modello (versione ottimizzata)
    prompt = f"""English examiner. Evaluate student response vs model answer.
TOPIC: {test_argomento}
QUESTION: {test_domanda}
MODEL: {test_risposta_modello}
STUDENT: {user_input}

Evaluate on scale 0-100:
- Content (40%): Key points coverage
- Language (30%): Grammar, vocabulary
- Structure (30%): Organization, clarity

Format: SCORE: [0-100]
COMMENT: [strengths and areas for improvement]
ENGLISH ONLY."""

    risposta = chiamata_llm(prompt, max_tokens=600, temperature=0.4)
    
    # Aggiorna il file temporaneo con la valutazione
    if os.path.exists(test_file_path):
        try:
            with open(test_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            content = content.replace("VALUTAZIONE: [Sarà aggiunta dopo la valutazione]", f"VALUTAZIONE: {risposta}")
            
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            st.error(f"Errore nell'aggiornamento del file di valutazione: {str(e)}")
    
    # Estrai punteggio e commento
    try:
        # Try to extract using English format
        if "SCORE:" in risposta:
            punteggio_match = risposta.split("SCORE:")[1].split("\n")[0].strip()
            punteggio = int(punteggio_match)  # Keep the original 0-100 scale
            commento = risposta.split("COMMENT:")[1].strip()
        else:
            # If no format is found, use default
            punteggio = 50  # Default on 0-100 scale
            commento = risposta
    except:
        punteggio = 50  # Default in caso di errore nel parsing (0-100 scale)
        commento = risposta
    
    # Salva il punteggio
    punteggi_df = salva_punteggio(punteggi_df, test_argomento, punteggio, commento, punteggi_file)
    
    # Aggiorna lo stato dell'argomento a "completato" dopo il test
    stato_argomenti_df = aggiorna_stato_argomento(stato_argomenti_df, test_argomento, "completato", stato_file)
    
    # Aggiorna chat log
    chat_log.append({"utente": f"Risposta al test: {user_input}", "llm": risposta})
    
    return punteggi_df, stato_argomenti_df, risposta, chat_log
