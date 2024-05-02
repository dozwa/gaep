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


# Read API key for OpenAI
OPENAI_API_KEY = ''

# Specify the GPT model to be used
model = "gpt-4-turbo-preview"

# Username and password for HTTP basic authentication
USER_01_name = ""
USER_01_pass = ""

#----------------------------------------------------
# Logging configuration

# Create Loggin Writer class
class LoggingWriter:
    """
    A class that redirects the standard output to a logger.

    Args:
        logger (logging.Logger): The logger object to which the output is redirected.
        level (int, optional): The logging level to be used. By default logging.INFO.

    Methods:
        write(message): Writes the message to the logger if it is not a newline character.
        flush(): A method that does nothing, as the logger has no buffer that needs to be emptied.
    """

    def __init__(self, logger, level=logging.INFO):
        """
        Initializes an instance of LoggingWriter.

        Args:
            logger (logging.Logger): The logger object to which the output is redirected.
            level (int, optional): The logging level to be used. By default logging.INFO.
        """
        self.logger = logger
        self.level = level

    def write(self, message):
        if message != '\n':
            self.logger.log(self.level, message)

    def flush(self):
        pass

# Create current date and time in the format year-month-day_hour-minute-second for the log
current_time = datetime.now().strftime('%Y-%m-%d')

# Generate file names for the log dynamically
log_filename = f'gaep_server_{current_time}.log'

# Logging configuration
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

# Redirect the standard output to logging
sys.stdout = LoggingWriter(logging.getLogger(), logging.INFO)

# Create path for logging the requests
json_path = ("json_logs/")
os.makedirs(json_path, exist_ok=True)


#----------------------------------------------------
# Create vector database

# Read path to the data source
data_path = "/Empfehlung_Kreuzschmerz_COPD.xlsx"

# Import data
df = pd.read_excel("/Datenquellen/Empfehlung_Kreuzschmerz_COPD.xlsx")

# Prepare data
documents = df['Empfehlungstext'].tolist() # Liste von Empfehlungstexten
metadata_columns = [col for col in df.columns if col.startswith("metadata_")] # Liste von Metadaten
metadatas = df[metadata_columns].to_dict(orient='records') # Liste in Dictionary umwandeln
ids = df['Ids'].tolist() # Liste von IDs

# Create in-memory database
chroma_client = chromadb.Client()

# Create OpenAI embedding function
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=OPENAI_API_KEY,
                model_name="text-embedding-3-large"
            )

# Create collection
collection = chroma_client.create_collection(name="leitlinien_collection", embedding_function=openai_ef)

# Fill ChromaDB with data
collection.add(
    documents=documents,
    metadatas=metadatas,
    ids=ids   
)

print("Datenbank erstellt, warte auf Anfrage...")


#----------------------------------------------------
# Establish database connection

# Read variable DB_KEY and save it in the variable db_key
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
# Define functions for data processing

# Function for searching the database
def search_in_db(question, n_results=4, ll=None):
    """
    Searches for a question in the vector database (chroma-db) and returns the search results.

    Args:
        question (str): The question to be searched for.
        n_results (int, optional): The number of search results returned. By default 4.
        ll (str, optional): The guideline to be used for filtering. None by default.

    Returns:
        list: A list with the search results.
    """
    search_results = collection.query(query_texts=question, n_results=n_results, where= {"metadata_Leitlinie" : ll})
    print("INFO: Search in the database successful.")
    print("INFO: Results:", search_results)
    return search_results

# Define prompt for optimizing the user question
def get_optimize_prompt():
    """
    Returns the optimization prompt used for the user question.

    Returns:
        optimize_prompt (PromptTemplate): The optimization prompt for the user question.
    """
    from prompt_helper import prompt_template_optimize
    optimize_prompt = PromptTemplate(template=prompt_template_optimize, input_variables=["context", "question"])
    return optimize_prompt

# Classification Prompt definieren
def get_classification_prompt():
    """
    Returns the classification prompt.

    This function imports the `prompt_helper` module and uses the `prompt_template_classification` template.
    The function does not expect any arguments.

    Return value:
    - classification_prompt: The classification prompt as a `PromptTemplate` object.
    """
    from prompt_helper import prompt_template_classification
    classification_prompt = PromptTemplate(template=prompt_template_classification, input_variables=["context", "question"])
    return classification_prompt

# Define analysis prompt
def get_analyse_prompt():
    """
    Returns the analysis prompt.

    The analysis prompt is imported from the help file prompt_helper and uses the template prompt_template_analyse.
    It expects the input variables "context" and "question".

    Returns:
        analysis_prompt (PromptTemplate): The analysis prompt.
    """
    from prompt_helper import prompt_template_analyse
    analyse_prompt = PromptTemplate(template=prompt_template_analyse, input_variables=["context", "question"])
    return analyse_prompt

# Define prompt summary
def get_summarize_prompt(detail=0):
    """
    Returns a prompt template that can be used to summarize the given context and question.

    Parameters:
    detail (int or bool): Specifies whether a short (0 or False) or a detailed (other values) prompt template should be returned.

    Return value:
    summarize_prompt (PromptTemplate): The corresponding prompt template for the summary.

    Example:
    summarize_prompt = get_summarize_prompt(detail=1)
    """

    from prompt_helper import prompt_template_summarize_long , prompt_template_summarize_short

    if detail == 0 or detail == False:
        summarize_prompt = PromptTemplate(template=prompt_template_summarize_short, input_variables=["context", "question"])
    else:
        summarize_prompt = PromptTemplate(template=prompt_template_summarize_long, input_variables=["context", "question"])

    return summarize_prompt

# Create LLM chain for optimization of the user question
def optimize_question_chain(optimize_prompt):
    """
    Creates the optimization chain to optimize the user question based on the given optimization prompt.

    Args:
        optimize_prompt (str): The optimization prompt used to optimize the question chain.

    Returns:
        LLMChain: The optimized question chain.
    """
    optimize_model = ChatOpenAI(temperature=0.0, model=model)
    optimize_chain = LLMChain(llm=optimize_model, prompt=optimize_prompt)
    return optimize_chain

# Create LLM chain for classification
def classify_recommendations_chain(classification_prompt):
    """
    Creates a classification chain for recommendations.

    Parameters:
        classification_prompt (str): The classification prompt for the chain.

    Returns:
        LLMChain: The created classification chain.
    """
    classification_model = ChatOpenAI(temperature=0.0, model=model)
    classification_chain = LLMChain(llm=classification_model, prompt=classification_prompt)
    return classification_chain

# LLM-Chain für Analyse erstellen
def analyse_recommendations_chain(analyse_prompt):
    """
    Analyzes a recommendation chain based on an analysis prompt.

    Args:
        analyze_prompt (str): The analysis prompt used to analyze the recommendation chain.

    Returns:
        LLMChain: The analyzed recommendation chain.

    """
    analyse_model = ChatOpenAI(temperature=0.0, model=model)
    analyse_chain = LLMChain(llm=analyse_model, prompt=analyse_prompt)
    return analyse_chain

# Create LLM chain for summary
def summarize_recommendations_chain(summarize_prompt):
    """
    Creates a summary chain for recommendations.

    Parameters:
        summarize_prompt (str): The text used as input for the summary.

    Returns:
        LLMChain: The summary chain created.
    """
    summarize_model = ChatOpenAI(temperature=0.0, model=model)
    summarize_chain = LLMChain(llm=summarize_model, prompt=summarize_prompt)
    return summarize_chain

# Go through and classify all recommendations
def classify_recommendations(results, question, classification_chain):
    """
    Classifies recommendations based on the results, the question asked and the classification chain.

    Args:
        results (dict): The results to be classified.
        question (str): The question asked.
        classification_chain (obj): The classification chain to be used.

    Returns:
        dict: A dictionary containing the classifications of the recommendations.
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

# Reformat recommendation levels so that they can be sorted
def sort_level(level):
    """
    Returns the sortable level based on the given level.

    Args:
        level (str): The level to be sorted.

    Returns:
        str: The sorted level.

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

# Create sortable reference
def sort_reference(reference):
    """
    Creates a sortable reference number.

    Args:
        reference (str): The reference number to be sorted.

    Returns:
        int: The sorted reference number as an integer.

    """
    reference = reference.replace("-", "")
    if len(reference) == 2:
        reference = reference[0]+ "0" + reference[1]
    return int(reference)

# Analyze and summarize all details of the recommendations with appropriate sensitivity
def analyse_recommendations(search_results, results_classifications, question, analyse_chain, relevance=2):
    """
    Analyzes and filters recommendations based on their relevance and returns a summary of relevant recommendations.
    Uses concurrent.futures to speed up the analysis of recommendations by parallelizing API requests.

    Args:
        search_results (dict): A dictionary with the search results.
        results_classifications (dict): A dictionary with the classifications of the recommendations.
        question (str): The question to which the recommendations answer.
        analysis_chain (obj): An instance of the analysis chain.
        relevance (int, optional): The sensitivity of the relevance filtering. It is set to 2 by default.

    Returns:
        dict: A dictionary with the summarized relevant recommendations.
    """
    ids_list = search_results['ids'][0]
    metadatas_list = search_results['metadatas'][0]
    summaries = {}

    # Translate the sensitivity into a list of relevance levels
    if relevance == 0:
        relevance = ['HOCH']
    elif relevance == 1:
        relevance = ['HOCH', 'MITTEL']
    elif relevance == 2:
        relevance = ['HOCH', 'MITTEL', 'NIEDRIG']

    # Remove the irrelevant recommendations
    for key, value in results_classifications.copy().items():
        if value not in relevance:
            del results_classifications[key]
            print("INFO: Recommendation", key, "not relevant and removed.")

    # Find the relevant recommendations
    def analyse_task(key):
        index = ids_list.index(key) if key in ids_list else -1
        if index != -1:
            context_detail = metadatas_list[index]['metadata_String']
            recommendation_text = metadatas_list[index]['metadata_Empfehlungstext']
            return key, f"{recommendation_text}; Summary of the recommendation details: {analyse_chain.run(context=context_detail, question=question)}"
        else:
            print("ID", key, "not found")
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

# Create Dict with the Ids and the reference numbers
def create_id_ref_dict(search_results, results_classifications):
    """
    Creates a dictionary that links the IDs from the search results with the corresponding references.

    Args:
        search_results (dict): A dictionary with the search results that contains the IDs and metadata.
        results_classifications (dict): A dictionary with the classifications of the search results.

    Returns:
        dict: A dictionary that links the IDs with the corresponding references.
    """
    ids_list = search_results['ids'][0]
    metadatas_list = search_results['metadatas'][0]
    ref_dict = {}

    # Find the relevant recommendations
    for key in results_classifications.keys():
        # Find the index
        index = ids_list.index(key) if key in ids_list else -1
        # Access to the corresponding 'metadata' dictionary and extraction of 'metadata_Reference'
        if index != -1:
            ref_dict[key] = metadatas_list[index]['metadata_Referenz']
            print("INFO: ID", key, "found")
        else:
            print("INFO: ID", key, "not found")
    return ref_dict

# Combine summaries of the relevant recommendations into a response
def summarize_recommendations(summarize_chain, summaries, frage):
    """
    Summary of recommendations.

    This function accepts a summary chain, a collection of summaries and a question.
    It creates a context that contains the relevant recommendations for the user question.
    It then uses the summary chain to answer the question based on the context.

    Args:
        summarize_chain (object): The summary chain used to answer the question.
        summaries (dict): A collection of summaries where the key is the reference and the value is the content.
        question (str): The question to be answered.

    Returns:
        str: The answer to the question based on the context and the summary chain.
    """
    context = ("The following recommendations from the guideline were identified as relevant to the user question: ")
    n = 1
    for key, value in summaries.items():
        context = context + "Start Empfehlung Nr." + str(n) + "; Referenz: " + key + "; Content: " + summaries[key] + "Ende Empfehlung Nr." + str(n) + ";;;;; "
        n = n + 1
    answer = summarize_chain.run(context=context, question=frage)
    return answer


#----------------------------------------------------
# Create Flask server

# Initialize the Flask application and the HTTP basic authentication object
app = Flask(__name__)
auth = HTTPBasicAuth()

# Generate the hashed password for the user and store it in a user dictionary
users = {
    USER_01_name: generate_password_hash(USER_01_pass)
}

# Verify the user name and password
@auth.verify_password
def verify_password(username, password):
    """
    Checks the username and password.

    Args:
        username (str): The username to be verified.
        password (str): The password to be checked.

    Returns:
        str: The user name if the check is successful.
    """
    if username in users and check_password_hash(users.get(username), password):
        return username

# Log the request information
@app.before_request
def log_request_info():
    """
    This function is called before each incoming request and logs information about the request.

    Parameters:
        None

    Returns:
        None
    """
    data = request.get_data()
    logging.info('Timestamp: %s, IP: %s, Headers: %s, Data: %s, Method: %s, Path: %s', 
                 request.date, request.remote_addr, request.headers, data, request.method, request.path)
    print('Timestamp: %s, IP: %s, Headers: %s, Data: %s, Method: %s, Path: %s' % (request.date, request.remote_addr, request.headers, data, request.method, request.path))

# Log the response data
@app.after_request
def after_request(response):
    """
    This function is called after each request and adds information about the timestamp, IP address and response.
    
    :param response: The HTTP response from the server.
    :return: The modified HTTP response.
    """
    response_data = response.get_data(as_text=True) if response.data else 'No data'
    logging.info('Timestamp: %s, IP: %s, response: %s', request.date, request.remote_addr, response_data)
    print('Timestamp: %s, IP: %s, response: %s' % (request.date, request.remote_addr, response_data))
    print("End of request ")
    print("-"*30)
    return response

@app.route('/gaep_server', methods=['POST'])
@auth.login_required
def handle_request():
    """
    Handles the POST request to the '/gaep_server' endpoint.
    Checks that the request contains JSON data and that all required input features are present.
    Connects to the SQL database and performs various operations to generate a response to the request.
    Creates a response with the relevant information and returns it.
    """
    # Log request information
    timestamp = time.time()     # Create timestamp for the request
    request_id = hashlib.sha256(str(timestamp).encode()).hexdigest() # Create unique request ID
    print("-"*30)
    print("Anfrage %s erhalten um %s" % (request_id, datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'))) # Anfrage-Informationen in der Konsole ausgeben
          
    if request.method == 'POST':
        print("Request received: ")
        print(request.is_json)
        # Check whether the request contains JSON data
        if not request.is_json:
            return jsonify({"message": "Bad Request: JSON required."}), 400
        data = request.get_json() # Extract request data from the request object
        input_features = ["frage","ll","detail"] # List of required input features for the request
        for feature in input_features: # Check whether the request contains all required input features
            if feature not in data:
                return jsonify({"message": "Bad Request: 'question' and 'leitlinie' are required."}), 400

        # Establish connection
        mydb = connect_to_database()
        print("Connection to the SQL database established")

        # Create cursor
        mycursor = mydb.cursor()

        # Optimize user question
        question_original = data["frage"]
        optimize_prompt = get_optimize_prompt()
        optimize_chain = optimize_question_chain(optimize_prompt)
        optimized_question = optimize_chain.run(context=data["ll"], question=data["frage"])
        data["frage"] = optimized_question

        # Search collection based on the user question
        results = search_in_db(data["frage"], n_results=10, ll=data["ll"])

        # Classify recommendations from the search
        classification_prompt = get_classification_prompt()
        classification_chain = classify_recommendations_chain(classification_prompt)
        results_classifications = classify_recommendations(results, data["frage"], classification_chain)

        # Analyze detailed texts of the relevant recommendations
        analyse_prompt = get_analyse_prompt()
        analyse_chain = analyse_recommendations_chain(analyse_prompt)
        analysed_recommendation_details = analyse_recommendations(results, results_classifications, data["frage"], analyse_chain)

        # Combine summaries of the relevant recommendations into a response
        summarize_prompt = get_summarize_prompt(detail=data["detail"])
        summarize_chain = summarize_recommendations_chain(summarize_prompt)
        answer = summarize_recommendations(summarize_chain, analysed_recommendation_details, data["frage"])

        # Create Dict with the Ids and the reference numbers
        ref_dict = create_id_ref_dict(results, results_classifications)
        
        # Search answer for key from ref_dict and replace it with value
        for key, value in ref_dict.items():
            answer = answer.replace(key, value)

        # Compose string for the answer

        # Prepare data for the answer
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

        # Add references to the response string
        
        for key, value in ref_dict.items():

            # Retrieve data from the database table tbl_empfehlungen
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
                "reference_text": str(reference_info[0][0]), # Add recommendation text for the reference
                "reference_sort": int(sort_reference(value)), # Add sortable reference number for the reference
                "level": str(reference_info[0][1]), # Add recommendation level for the reference
                "level_sort": str(sort_level(reference_info[0][1])), # Add sortable recommendation grade for the reference
                "semantic_sort": 1, # Add semantic sorting for the reference, current fixed value
                "base": str(reference_info[0][2]), # Add recommendation base for the reference
                "guideline_url": str(reference_info[0][3]), # Add URL for the reference
                "chapter": str(", ".join([i for i in reference_info[0][4:7] if i != "<NA>"])), # Add main topic for the reference
                "sources": [],
                "details": []
                }
            
            # Create string for searching through all text information
            search_string = reference_data["reference_text"] + \
                            reference_data["base"] + \
                            reference_data["chapter"] + \
                            reference_data["generated_summary"]

            # Add sources for the recommendation

            # Retrieve data from the database table tbl_sources
            # Retrieve all sources for a recommendation
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
                
            # Retrieve data from the database table tbl_recommendation_details
            query = ("SELECT tbl_empfehlungsdetails.empfehlungsdetail_uid, tbl_empfehlungsdetails.ueberschrift, tbl_empfehlungsdetails.detailtext, tbl_empfehlungsdetails.bild\
                            FROM tbl_empfehlungen_empfehlungsdetails \
                            JOIN tbl_empfehlungen ON tbl_empfehlungen_empfehlungsdetails.empfehlung_Uid = tbl_empfehlungen.empfehlung_Uid \
                            JOIN tbl_empfehlungsdetails ON tbl_empfehlungen_empfehlungsdetails.empfehlungsdetail_uid = tbl_empfehlungsdetails.empfehlungsdetail_uid \
                            WHERE tbl_empfehlungen.Empfehlung_Uid=%s")
            mycursor.execute(query, (key,))
            # Ergebnis abrufen
            reference_detail = mycursor.fetchall()

            # Add details
            for detail in reference_detail:
                detail_data = {
                    "position": int(detail[0].split('/')[1]),
                    "title": str(detail[1]),
                    "content": str(detail[2]),
                    "image_base64": str(detail[3]),
                    "sources": []
                }

                search_string += detail_data["title"] + detail_data["content"]
 
                # Add sources for the recommendation details

                # Retrieve data from the database table tbl_recommendation_details_sources

                detail_key = detail[0]
                query = ("SELECT tbl_empfehlungsdetails.empfehlungsdetail_uid, tbl_quellen.nummer, tbl_quellen.details, tbl_quellen.link \
                                FROM tbl_quellen \
                                JOIN tbl_quellen_empfehlungsdetails ON tbl_quellen_empfehlungsdetails.Quelle_Uid = tbl_quellen.Quelle_Uid \
                                JOIN tbl_empfehlungsdetails ON tbl_empfehlungsdetails.empfehlungsdetail_uid = tbl_quellen_empfehlungsdetails.empfehlungsdetail_uid \
                                WHERE tbl_empfehlungsdetails.empfehlungsdetail_uid=%s")
                mycursor.execute(query, (detail_key,))
                # Ergebnis abrufen
                sources = mycursor.fetchall()

                # Add sources for the details
                for source in sources:
                    detail_data["sources"].append({
                        "source_id": int(source[1]),
                        "content": str(source[2]),
                        "url": str(source[3])
                    })
                    
                reference_data["details"].append(detail_data)

            answer_data["references"].append(reference_data)

            # Add search_string to the reference_data
            reference_data["search_string"] = search_string

        # Create response string
        answer_string = json.dumps(answer_data)

        print("-"*10 + "Response string successfully created:")
        print("Answer_string: " + answer_string)

        json_data = json.dumps(answer_data) # Konvertieren Sie die Daten in einen JSON-String

        # Close the database connection
        mydb.close()

        # Save the data in a file with the name of the request_id
        timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        with open(os.path.join(json_path, f'gaep-log_{timestamp}_{request_id[0:10]}.json'), 'w') as file:
            file.write(json_data)

        # Return the answer
        try:
            return answer_data, 200
        except:
            print("Fehler:", 500)


#----------------------------------------------------
# Start Flask Server
        
if __name__ == "__main__":
    # Starten der Flask-Anwendung
    app.run(port=5000, host='0.0.0.0', debug=False)
    print("Server gestoppt...")
