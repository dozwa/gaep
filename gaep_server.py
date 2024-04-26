import os
import sys
import pandas as pd
import chromadb
import logging
import concurrent.futures
import time
import hashlib
import json
import mysql.connector
from datetime import datetime
from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from chromadb.utils import embedding_functions
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
from langchain import PromptTemplate
from mysql.connector import errors


# API Key für OpenAI einlesen
OPENAI_API_KEY = ''

# Festlegen des zu verwendenden GPT-Modells
model = "gpt-4-turbo-preview"

# Benutzername und Passwort für die HTTP-Basisauthentifizierung
USER_01_name = ""
USER_01_pass = ""

#----------------------------------------------------
# Logging-Konfiguration

# Loggin Writer Klasse erstellen
class LoggingWriter:
    """
    Eine Klasse, die die Standardausgabe auf einen Logger umleitet.

    Args:
        logger (logging.Logger): Das Logger-Objekt, auf das die Ausgabe umgeleitet wird.
        level (int, optional): Das Logging-Level, das verwendet werden soll. Standardmäßig logging.INFO.

    Methods:
        write(message): Schreibt die Nachricht in den Logger, wenn es sich nicht um ein Zeilenumbruchzeichen handelt.
        flush(): Eine Methode, die nichts tut, da der Logger keinen Puffer hat, der geleert werden muss.
    """

    def __init__(self, logger, level=logging.INFO):
        """
        Initialisiert eine Instanz von LoggingWriter.

        Args:
            logger (logging.Logger): Das Logger-Objekt, auf das die Ausgabe umgeleitet wird.
            level (int, optional): Das Logging-Level, das verwendet werden soll. Standardmäßig logging.INFO.
        """
        self.logger = logger
        self.level = level

    def write(self, message):
        if message != '\n':
            self.logger.log(self.level, message)

    def flush(self):
        pass

# Aktuelles Datum und Uhrzeit im Format Jahr-Monat-Tag_Stunde-Minute-Sekunde für das Log erstellen
current_time = datetime.now().strftime('%Y-%m-%d')

# Dateinamen für das Log dynamisch generieren
log_filename = f'gaep_server_{current_time}.log'

# Logging-Konfiguration
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

# Umlenken der Standardausgabe auf das Logging
sys.stdout = LoggingWriter(logging.getLogger(), logging.INFO)

# Pfad für das Loggen der Anfragen erstellen
json_path = ("json_logs/")
os.makedirs(json_path, exist_ok=True)


#----------------------------------------------------
# Vektordatenbank erstellen

# Pfad zur Datenquelle einlesen
data_path = "/Datenquellen/Empfehlung_Kreuzschmerz_COPD.xlsx"

# Daten importieren
df = pd.read_excel("/Datenquellen/Empfehlung_Kreuzschmerz_COPD.xlsx")

# Daten aufbereiten
documents = df['Empfehlungstext'].tolist() # Liste von Empfehlungstexten
metadata_columns = [col for col in df.columns if col.startswith("metadata_")] # Liste von Metadaten
metadatas = df[metadata_columns].to_dict(orient='records') # Liste in Dictionary umwandeln
ids = df['Ids'].tolist() # Liste von IDs

# In-memory Datenbank erstellen
chroma_client = chromadb.Client()

# OpenAI-Embedding Funktion erstellen
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=OPENAI_API_KEY,
                model_name="text-embedding-3-large"
            )

# Collection erstellen
collection = chroma_client.create_collection(name="leitlinien_collection", embedding_function=openai_ef)

# ChromaDB mit Daten füllen
collection.add(
    documents=documents,
    metadatas=metadatas,
    ids=ids   
)

print("Datenbank erstellt, warte auf Anfrage...")


#----------------------------------------------------
# Datenbankverbindung herstellen

# Umgebungsvariable DB_KEY einlesen und in die Variable db_key speichern
db_key = ''

def connect_to_database():
    try:
        mydb = mysql.connector.connect(
        host="localhost",
        user="leitlinien",
        password=db_key,
        database="leitlinien"
    )
        return mydb
    except errors.OperationalError as e:
        if 'Lost connection to MySQL server' in str(e):
            # Versuchen Sie, die Verbindung erneut herzustellen
            return connect_to_database()
        else:
            raise


#----------------------------------------------------
# Funktionen für die Datenverabeitung definieren

# Funktion für die Suche in der Datenbank
def search_in_db(question, n_results=4, ll=None):
    """
    Sucht in der Vektor-Datenbank (chroma-db) nach einer Frage und gibt die Suchergebnisse zurück.

    Args:
        question (str): Die Frage, nach der gesucht werden soll.
        n_results (int, optional): Die Anzahl der zurückgegebenen Suchergebnisse. Standardmäßig 4.
        ll (str, optional): Die Leitlinie, nach der gefiltert werden soll. Standardmäßig None.

    Returns:
        list: Eine Liste mit den Suchergebnissen.
    """
    search_results = collection.query(query_texts=question, n_results=n_results, where= {"metadata_Leitlinie" : ll})
    print("INFO: Suche in der Datenbank erfolgreich.")
    print("INFO: Ergebnisse:", search_results)
    return search_results

# Prompt für die Optimierung der Nutzerfrage definieren
def get_optimize_prompt():
    """
    Gibt das Optimierungsprompt zurück, das für die Nutzerfrage verwendet wird.

    Returns:
        optimize_prompt (PromptTemplate): Das Optimierungsprompt für die Nutzerfrage.
    """
    from prompt_helper import prompt_template_optimize
    optimize_prompt = PromptTemplate(template=prompt_template_optimize, input_variables=["context", "question"])
    return optimize_prompt

# Classification Prompt definieren
def get_classification_prompt():
    """
    Gibt die Klassifikations-Prompt zurück.

    Diese Funktion importiert das Modul `prompt_helper` und verwendet die Vorlage `prompt_template_classification`.
    Die Funktion erwartet keine Argumente.

    Rückgabewert:
    - classification_prompt: Die Klassifikationsaufforderung als `PromptTemplate`-Objekt.
    """
    from prompt_helper import prompt_template_classification
    classification_prompt = PromptTemplate(template=prompt_template_classification, input_variables=["context", "question"])
    return classification_prompt

# Analyse Prompt definieren
def get_analyse_prompt():
    """
    Gibt das Analyse-Prompt zurück.

    Das Analyse-Prompt wird aus der Hilfsdatei prompt_helper importiert und verwendet das Template prompt_template_analyse.
    Es erwartet die Eingabevariablen "context" und "question".

    Returns:
        analyse_prompt (PromptTemplate): Das Analyse-Prompt.
    """
    from prompt_helper import prompt_template_analyse
    analyse_prompt = PromptTemplate(template=prompt_template_analyse, input_variables=["context", "question"])
    return analyse_prompt

# Zusammenfassung Prompt definieren
def get_summarize_prompt(detail=0):
    """
    Gibt eine Prompt-Vorlage zurück, die für die Zusammenfassung der gegebenen Kontext- und Fragestellung verwendet werden kann.

    Parameter:
    detail (int oder bool): Gibt an, ob eine kurze (0 oder False) oder eine ausführliche (andere Werte) Prompt-Vorlage zurückgegeben werden soll.

    Rückgabewert:
    summarize_prompt (PromptTemplate): Die entsprechende Prompt-Vorlage für die Zusammenfassung.

    Beispiel:
    summarize_prompt = get_summarize_prompt(detail=1)
    """

    from prompt_helper import prompt_template_summarize_long , prompt_template_summarize_short

    if detail == 0 or detail == False:
        summarize_prompt = PromptTemplate(template=prompt_template_summarize_short, input_variables=["context", "question"])
    else:
        summarize_prompt = PromptTemplate(template=prompt_template_summarize_long, input_variables=["context", "question"])

    return summarize_prompt

# LLM-Chain für Optimierung der Nutzerfrage erstellen
def optimize_question_chain(optimize_prompt):
    """
    Erstellt die Optimierungskette zur Optimierung der Nutzerfrage basierend auf dem gegebenen Optimierungsprompt.

    Args:
        optimize_prompt (str): Der Optimierungsprompt, der verwendet wird, um die Fragekette zu optimieren.

    Returns:
        LLMChain: Die optimierte Fragekette.
    """
    optimize_model = ChatOpenAI(temperature=0.0, model=model)
    optimize_chain = LLMChain(llm=optimize_model, prompt=optimize_prompt)
    return optimize_chain

# LLM-Chain für Klassifizierung erstellen
def classify_recommendations_chain(classification_prompt):
    """
    Erstellt eine Klassifizierungskette für Empfehlungen.

    Parameters:
        classification_prompt (str): Der Klassifizierungs-Prompt für die Kette.

    Returns:
        LLMChain: Die erstellte Klassifizierungskette.
    """
    classification_model = ChatOpenAI(temperature=0.0, model=model)
    classification_chain = LLMChain(llm=classification_model, prompt=classification_prompt)
    return classification_chain

# LLM-Chain für Analyse erstellen
def analyse_recommendations_chain(analyse_prompt):
    """
    Analysiert eine Empfehlungskette basierend auf einem Analyse-Prompt.

    Args:
        analyse_prompt (str): Der Analyse-Prompt, der verwendet wird, um die Empfehlungskette zu analysieren.

    Returns:
        LLMChain: Die analysierte Empfehlungskette.

    """
    analyse_model = ChatOpenAI(temperature=0.0, model=model)
    analyse_chain = LLMChain(llm=analyse_model, prompt=analyse_prompt)
    return analyse_chain

# LLM-Chain für Zusammenfassung erstellen
def summarize_recommendations_chain(summarize_prompt):
    """
    Erstellt eine Zusammenfassungskette für Empfehlungen.

    Parameters:
        summarize_prompt (str): Der Text, der als Eingabe für die Zusammenfassung verwendet wird.

    Returns:
        LLMChain: Die erstellte Zusammenfassungskette.
    """
    summarize_model = ChatOpenAI(temperature=0.0, model=model)
    summarize_chain = LLMChain(llm=summarize_model, prompt=summarize_prompt)
    return summarize_chain

# Alle Empfehlungen durchgehen und klassifizieren
def classify_recommendations(results, question, classification_chain):
    """
    Klassifiziert Empfehlungen basierend auf den Ergebnissen, der gestellten Frage und der Klassifikationskette.

    Args:
        results (dict): Die Ergebnisse, die klassifiziert werden sollen.
        question (str): Die gestellte Frage.
        classification_chain (obj): Die Klassifikationskette, die verwendet werden soll.

    Returns:
        dict: Ein Wörterbuch, das die Klassifikationen der Empfehlungen enthält.
    """
    results_classifications = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for i in range(len(results["documents"][0])):
            context = results["documents"][0][i]
            id = results["ids"][0][i]
            futures.append(executor.submit(classification_chain.run, context=context, question=question))
        
        for future, id in zip(concurrent.futures.as_completed(futures), results["ids"][0]):
            results_classifications[id] = future.result()
            print("INFO: Empfehlung", id, "klassifiziert als", results_classifications[id])
    
    return results_classifications

# Empfehlungslevel neu formatieren, damit diese sortierbar sind
def sort_level(level):
    """
    Gibt den sortierbaren Level basierend auf dem gegebenen Level zurück.

    Args:
        level (str): Der Level, der sortiert werden soll.

    Returns:
        str: Der sortierte Level.

    """
    levels = {
        "soll": "1soll",
        "sollte": "2sollte",
        "kann": "3kann",
        "sollte nicht": "4sollte_nicht",
        "soll nicht": "5soll_nicht",
        "Statement": "6statement"
    }
    return levels.get(level, level)

# Sortierbare Reference erstellen
def sort_reference(reference):
    """
    Erstellt eine sortierbare Referenznummer.

    Args:
        reference (str): Die zu sortierende Referenznummer.

    Returns:
        int: Die sortierte Referenznummer als Ganzzahl.

    """
    reference = reference.replace("-", "")
    if len(reference) == 2:
        reference = reference[0]+ "0" + reference[1]
    return int(reference)

# Alle Details der Empfehlungen mit entsprechenden Sensitivät analysieren und zusammenfassen
def analyse_recommendations(search_results, results_classifications, question, analyse_chain, relevance=2):
    """
    Analysiert und filtert Empfehlungen basierend auf ihrer Relevanz und gibt eine Zusammenfassung der relevanten Empfehlungen zurück.
    Verwendet concurrent.futures, um die Analyse der Empfehlungen durch Parallelisierung der API Anfragen zu beschleunigen.

    Args:
        search_results (dict): Ein Wörterbuch mit den Suchergebnissen.
        results_classifications (dict): Ein Wörterbuch mit den Klassifizierungen der Empfehlungen.
        question (str): Die Frage, auf die die Empfehlungen antworten.
        analyse_chain (obj): Eine Instanz der Analyse-Kette.
        relevance (int, optional): Die Sensitivität der Relevanzfilterung. Standardmäßig ist sie auf 2 eingestellt.

    Returns:
        dict: Ein Wörterbuch mit den zusammengefassten relevanten Empfehlungen.
    """
    ids_list = search_results['ids'][0]
    metadatas_list = search_results['metadatas'][0]
    summaries = {}

    # Übersetzen der Sensitivität in eine Liste von Relevanzstufen
    if relevance == 0:
        relevance = ['HOCH']
    elif relevance == 1:
        relevance = ['HOCH', 'MITTEL']
    elif relevance == 2:
        relevance = ['HOCH', 'MITTEL', 'NIEDRIG']

    # Entfernen der nicht relevanten Empfehlungen
    for key, value in results_classifications.copy().items():
        if value not in relevance:
            del results_classifications[key]
            print("INFO: Empfehlung", key, "nicht relevant und entfernt.")

    # Finden der relevanten Empfehlungen
    def analyse_task(key):
        index = ids_list.index(key) if key in ids_list else -1
        if index != -1:
            context_detail = metadatas_list[index]['metadata_String']
            recommendation_text = metadatas_list[index]['metadata_Empfehlungstext']
            return key, f"{recommendation_text}; Zusammenfassung der Empfehlungsdetails: {analyse_chain.run(context=context_detail, question=question)}"
        else:
            print("ID", key, "nicht gefunden")
            return key, None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(analyse_task, key) for key in results_classifications.keys()]

        for future in concurrent.futures.as_completed(futures):
            key, result = future.result()
            if result is not None:
                if result != "SKIP":
                    summaries[key] = result
                    print("INFO: Empfehlung", key, "analysiert und zusammengefasst.")
                else:
                    del results_classifications[key]
                    print("INFO: Empfehlung", key, "nicht relevant und entfernt.")

    print("Summaries:", results_classifications)

    return summaries

# Dict mit den Ids und den Referenznummern erstellen
def create_id_ref_dict(search_results, results_classifications):
    """
    Erstellt ein Wörterbuch, das die IDs aus den Suchergebnissen mit den entsprechenden Referenzen verknüpft.

    Args:
        search_results (dict): Ein Wörterbuch mit den Suchergebnissen, das die IDs und Metadaten enthält.
        results_classifications (dict): Ein Wörterbuch mit den Klassifikationen der Suchergebnisse.

    Returns:
        dict: Ein Wörterbuch, das die IDs mit den entsprechenden Referenzen verknüpft.
    """
    ids_list = search_results['ids'][0]
    metadatas_list = search_results['metadatas'][0]
    ref_dict = {}

    # Finden der relevanten Empfehlungen
    for key in results_classifications.keys():
        # Finden des Indexes
        index = ids_list.index(key) if key in ids_list else -1
        # Zugriff auf das entsprechende 'metadata' Dictionary und Extraktion von 'metadata_Referenz'
        if index != -1:
            ref_dict[key] = metadatas_list[index]['metadata_Referenz']
            print("INFO: ID", key, "gefunden")
        else:
            print("ID", key, "nicht gefunden")
    return ref_dict

# Zusammenfassungen der relevanten Empfehlungen zu einer Antwort zusammenfügen
def summarize_recommendations(summarize_chain, summaries, frage):
    """
    Zusammenfassung der Empfehlungen.

    Diese Funktion nimmt eine Zusammenfassungskette, eine Sammlung von Zusammenfassungen und eine Frage entgegen.
    Sie erstellt einen Kontext, der die relevanten Empfehlungen für die Nutzerfrage enthält.
    Dann wird die Zusammenfassungskette verwendet, um die Frage basierend auf dem Kontext zu beantworten.

    Args:
        summarize_chain (objekt): Die Zusammenfassungskette, die verwendet wird, um die Frage zu beantworten.
        summaries (dict): Eine Sammlung von Zusammenfassungen, wobei der Schlüssel die Referenz und der Wert der Inhalt ist.
        frage (str): Die Frage, die beantwortet werden soll.

    Returns:
        str: Die Antwort auf die Frage basierend auf dem Kontext und der Zusammenfassungskette.
    """
    context = ("Die folgenden Empfehlungen aus der Leitlinie wurden als relevant für die Nutzerfrage identifiziert: ")
    n = 1
    for key, value in summaries.items():
        context = context + "Start Empfehlung Nr." + str(n) + "; Referenz: " + key + "; Content: " + summaries[key] + "Ende Empfehlung Nr." + str(n) + ";;;;; "
        n = n + 1
    answer = summarize_chain.run(context=context, question=frage)
    return answer


#----------------------------------------------------
# Flask Server erstellen

# Initialisieren der Flask-Anwendung und des HTTP-Basisauthentifizierungsobjekts
app = Flask(__name__)
auth = HTTPBasicAuth()

# Generieren des gehashten Passworts für den Benutzer und Speichern in einem Benutzer-Wörterbuch
users = {
    USER_01_name: generate_password_hash(USER_01_pass)
}

# Überprüfen des Benutzernamens und Passworts
@auth.verify_password
def verify_password(username, password):
    """
    Überprüft den Benutzernamen und das Passwort.

    Args:
        username (str): Der Benutzername, der überprüft werden soll.
        password (str): Das Passwort, das überprüft werden soll.

    Returns:
        str: Der Benutzername, wenn die Überprüfung erfolgreich ist.
    """
    if username in users and check_password_hash(users.get(username), password):
        return username

# Loggen der Anfrageinformationen
@app.before_request
def log_request_info():
    """
    Diese Funktion wird vor jedem eingehenden Request aufgerufen und protokolliert Informationen über den Request.

    Parameters:
        None

    Returns:
        None
    """
    data = request.get_data()
    logging.info('Timestamp: %s, IP: %s, Headers: %s, Data: %s, Method: %s, Path: %s', 
                 request.date, request.remote_addr, request.headers, data, request.method, request.path)
    print('Timestamp: %s, IP: %s, Headers: %s, Data: %s, Method: %s, Path: %s' % (request.date, request.remote_addr, request.headers, data, request.method, request.path))

# Loggen der Antwortdaten
@app.after_request
def after_request(response):
    """
    Diese Funktion wird nach jeder Anfrage aufgerufen und fügt Informationen zum Zeitstempel, der IP-Adresse und der Antwort hinzu.
    
    :param response: Die HTTP-Antwort des Servers.
    :return: Die modifizierte HTTP-Antwort.
    """
    response_data = response.get_data(as_text=True) if response.data else 'Keine Daten'
    logging.info('Zeitstempel: %s, IP: %s, Antwort: %s', request.date, request.remote_addr, response_data)
    print('Zeitstempel: %s, IP: %s, Antwort: %s' % (request.date, request.remote_addr, response_data))
    print("Ende der Anfrage ")
    print("-"*30)
    return response

@app.route('/gaep_server', methods=['POST'])
@auth.login_required
def handle_request():
    """
    Behandelt die POST-Anfrage an den '/gaep_server' Endpunkt.
    Überprüft, ob die Anfrage JSON-Daten enthält und alle erforderlichen Input-Features vorhanden sind.
    Stellt eine Verbindung zur SQL-Datenbank her und führt verschiedene Operationen aus, um eine Antwort auf die Anfrage zu generieren.
    Erstellt eine Antwort mit den relevanten Informationen und gibt sie zurück.
    """
    # Anfrage-Informationen loggen
    timestamp = time.time() # Zeitstempel für die Anfrage erstellen
    request_id = hashlib.sha256(str(timestamp).encode()).hexdigest() # Eindeutige Anfrage-ID erstellen
    print("-"*30)
    print("Anfrage %s erhalten um %s" % (request_id, datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'))) # Anfrage-Informationen in der Konsole ausgeben
          
    if request.method == 'POST':
        print("Anfrage erhalten: ")
        print(request.is_json)
        # Überprüfen, ob die Anfrage JSON-Daten enthält
        if not request.is_json:
            return jsonify({"message": "Bad Request: JSON required."}), 400
        data = request.get_json() # Anfrage-Daten aus dem Request-Objekt extrahieren
        input_features = ["frage","ll","detail"] # Liste der erforderlichen Input-Features für die Anfrage
        for feature in input_features: # Überprüfen, ob die Anfrage alle erforderlichen Input-Features enthält
            if feature not in data:
                return jsonify({"message": "Bad Request: 'question' and 'leitlinie' are required."}), 400

        # Verbindung herstellen
        mydb = connect_to_database()
        print("Verbindung mit der SQL Datenbank hergestellt")

        # Cursor erstellen
        mycursor = mydb.cursor()

        # Nutzerfrage optimieren
        question_original = data["frage"]
        optimize_prompt = get_optimize_prompt()
        optimize_chain = optimize_question_chain(optimize_prompt)
        optimized_question = optimize_chain.run(context=data["ll"], question=data["frage"])
        data["frage"] = optimized_question

        # Collection auf Basis der Nutzerfrage durchsuchen
        results = search_in_db(data["frage"], n_results=10, ll=data["ll"])

        # Empfehlungen aus der Suche klassifizieren
        classification_prompt = get_classification_prompt()
        classification_chain = classify_recommendations_chain(classification_prompt)
        results_classifications = classify_recommendations(results, data["frage"], classification_chain)

        # Detailtexte der relevanten Empfehlungen analysieren
        analyse_prompt = get_analyse_prompt()
        analyse_chain = analyse_recommendations_chain(analyse_prompt)
        analysed_recommendation_details = analyse_recommendations(results, results_classifications, data["frage"], analyse_chain)

        # Zusammenfassungen der relevanten Empfehlungen zu einer Antwort zusammenfügen
        summarize_prompt = get_summarize_prompt(detail=data["detail"])
        summarize_chain = summarize_recommendations_chain(summarize_prompt)
        answer = summarize_recommendations(summarize_chain, analysed_recommendation_details, data["frage"])

        # Dict mit den Ids und den Referenznummern erstellen
        ref_dict = create_id_ref_dict(results, results_classifications)
        
        # Durchsuche answer nach key aus ref_dict und ersetze ihn durch value
        for key, value in ref_dict.items():
            answer = answer.replace(key, value)

        # String für die Antwort zusammenstellen

        # Daten für die Antwort vorbereiten
        answer_data = {
            "optimized_question": str(data["frage"]),
            "generated_answer": str(answer),
            "guideline": str(data["ll"]),
            "n_references_returned": int(len(results_classifications)),
            "request_id": str(request_id),
            "timestamp_request": float(timestamp),
            "timestamp_response": float(time.time()),
            "duration": float(time.time() - timestamp),
            "model": str(model),
            "user_question": str(question_original),
            "references": []
        }

        # Referenzen zum Antwortstring hinzufügen
        
        for key, value in ref_dict.items():

            # Daten aus der Datenbanktabelle tbl_empfehlungen abrufen
            query = ("SELECT tbl_empfehlungen.empfehlungstext, tbl_empfehlungen.empfehlungsgrad, tbl_empfehlungen.empfehlungsbasis, tbl_empfehlungen.seite_url, tbl_empfehlungen.oberthema, tbl_empfehlungen.zwischenthema, tbl_empfehlungen.unterthema\
                            FROM tbl_empfehlungen\
                            WHERE tbl_empfehlungen.Empfehlung_Uid =%s")
            mycursor.execute(query, (key,))
            # Ergebnis abrufen
            reference_info = mycursor.fetchall()

            reference_data = {
                "reference_id": str(value),
                "generated_summary": str(analysed_recommendation_details[key].split("Zusammenfassung der Empfehlungsdetails: ")[1] if key in analysed_recommendation_details else "Keine Details verfügbar"),
                "relevance": str(results_classifications[key]),
                "sources": [],
                "details": [],
                "reference_text": str(reference_info[0][0]), # Empfehlungstext für die Referenz hinzufügen
                "reference_sort": int(sort_reference(value)), # sortierbare Referenznummer für die Referenz hinzufügen
                "level": str(reference_info[0][1]), # Empfehlungsgrad für die Referenz hinzufügen
                "level_sort": str(sort_level(reference_info[0][1])), # sortierbaren Empfehlungsgrad für die Referenz hinzufügen
                "semantic_sort": 1, # Semantische Sortierung für die Referenz hinzufügen, aktuell fester wert
                "base": str(reference_info[0][2]), # Empfehlungsbasis für die Referenz hinzufügen
                "guideline_url": str(reference_info[0][3]), # URL für die Referenz hinzufügen
                "chapter": str(", ".join([i for i in reference_info[0][4:7] if i != "<NA>"])), # Oberthema für die Referenz hinzufügen
                "sources": [],
                "details": []
                }
            
            # String für das Durchsuchen aller Textinfos erstellen
            search_string = reference_data["reference_text"] + \
                            reference_data["base"] + \
                            reference_data["chapter"] + \
                            reference_data["generated_summary"]

            # Quellen für die Empfehlung hinzufügen

            # Daten aus der Datenbanktabelle tbl_quellen abrufen
            # Alle Quellen zu einer Empfehlung abrufen
            query = ("SELECT tbl_quellen.nummer, tbl_quellen.details, tbl_quellen.link \
                            FROM tbl_quellen \
                            JOIN tbl_quellen_empfehlungen ON tbl_quellen_empfehlungen.Quelle_Uid = tbl_quellen.Quelle_Uid \
                            JOIN tbl_empfehlungen ON tbl_empfehlungen.Empfehlung_Uid = tbl_quellen_empfehlungen.Empfehlung_Uid \
                            WHERE tbl_empfehlungen.Empfehlung_Uid=%s")
            mycursor.execute(query, (key,))
            # Ergebnis abrufen
            sources = mycursor.fetchall()

            for source in sources:
                reference_data["sources"].append({
                    "source_id": int(source[0]),
                    "content": str(source[1]),
                    "url": str(source[2])
                })
                
            # Daten aus der Datenbanktabelle tbl_empfehlungsdetails abrufen
            query = ("SELECT tbl_empfehlungsdetails.empfehlungsdetail_uid, tbl_empfehlungsdetails.ueberschrift, tbl_empfehlungsdetails.detailtext, tbl_empfehlungsdetails.bild\
                            FROM tbl_empfehlungen_empfehlungsdetails \
                            JOIN tbl_empfehlungen ON tbl_empfehlungen_empfehlungsdetails.empfehlung_Uid = tbl_empfehlungen.empfehlung_Uid \
                            JOIN tbl_empfehlungsdetails ON tbl_empfehlungen_empfehlungsdetails.empfehlungsdetail_uid = tbl_empfehlungsdetails.empfehlungsdetail_uid \
                            WHERE tbl_empfehlungen.Empfehlung_Uid=%s")
            mycursor.execute(query, (key,))
            # Ergebnis abrufen
            reference_detail = mycursor.fetchall()

            # Details hinzufügen
            for detail in reference_detail:
                detail_data = {
                    "position": int(detail[0].split('/')[1]),
                    "title": str(detail[1]),
                    "content": str(detail[2]),
                    "image_base64": str(detail[3]),
                    "sources": []
                }

                search_string += detail_data["title"] + detail_data["content"]
 
                # Quellen für die Empfehlungsdetails hinzufügen

                # Daten aus der Datenbanktabelle tbl_empfehlungsdetailsquellen abrufen

                detail_key = detail[0]
                query = ("SELECT tbl_empfehlungsdetails.empfehlungsdetail_uid, tbl_quellen.nummer, tbl_quellen.details, tbl_quellen.link \
                                FROM tbl_quellen \
                                JOIN tbl_quellen_empfehlungsdetails ON tbl_quellen_empfehlungsdetails.Quelle_Uid = tbl_quellen.Quelle_Uid \
                                JOIN tbl_empfehlungsdetails ON tbl_empfehlungsdetails.empfehlungsdetail_uid = tbl_quellen_empfehlungsdetails.empfehlungsdetail_uid \
                                WHERE tbl_empfehlungsdetails.empfehlungsdetail_uid=%s")
                mycursor.execute(query, (detail_key,))
                # Ergebnis abrufen
                sources = mycursor.fetchall()

                # Quellen für die Details hinzufügen
                for source in sources:
                    detail_data["sources"].append({
                        "source_id": int(source[1]),
                        "content": str(source[2]),
                        "url": str(source[3])
                    })
                    
                reference_data["details"].append(detail_data)

            answer_data["references"].append(reference_data)

            # search_string dem dem reference_data hinzufügen
            reference_data["search_string"] = search_string

        # Antwort-String erstellen
        answer_string = json.dumps(answer_data)

        print("-"*10 + "Antwort-String erfolgreich erstellt:")
        print("Answer_string: " + answer_string)

        json_data = json.dumps(answer_data) # Konvertieren Sie die Daten in einen JSON-String

        # Schließen Sie die Datenbankverbindung
        mydb.close()

        # Speichern Sie die Daten in einer Datei, die den Namen der request_id hat
        timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        with open(os.path.join(json_path, f'gaep-log_{timestamp}_{request_id[0:10]}.json'), 'w') as file:
            file.write(json_data)

        # Rückgabe der Antwort
        try:
            return answer_data, 200
        except:
            print("Fehler:", 500)


#----------------------------------------------------
# Flask Server starten
        
if __name__ == "__main__":
    # Starten der Flask-Anwendung
    app.run(port=5000, host='0.0.0.0', debug=False)
    print("Server gestoppt...")
