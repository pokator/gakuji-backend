import os
import openai
from supabase.client import Client, create_client
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders.pdf import PyPDFLoader  
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv())

openai.api_key = os.environ['OPENAI_API_KEY']
supabase_url = os.environ['SUPABASE_URL']
supabase_key = os.environ['SUPABASE_API']

supabase: Client = create_client(supabase_url, supabase_key)

# Function to remove null characters from a Document object
def remove_null_chars(document):
    document.page_content = document.page_content.replace('\u0000', '')
    print(document.page_content)
    return document

# add your file name with the path
loader = PyPDFLoader("./documents/SPAAlliance-CaregiverToolkit-FINAL.pdf")
documents = loader.load()

# Remove null characters from each document
documents = [remove_null_chars(doc) for doc in documents]

text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
docs = text_splitter.split_documents(documents)

embeddings = OpenAIEmbeddings()

vector_store = SupabaseVectorStore.from_documents(docs, embeddings, client=supabase, table_name="documents", query_name="match_documents")