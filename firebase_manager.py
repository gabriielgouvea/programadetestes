# --- firebase_manager.py ---
# Este é o nosso "Setor de Banco de Dados" (ATUALIZADO PARA MARCAS)

import firebase_admin
from firebase_admin import credentials, db
from tkinter import messagebox
import os
import traceback

# --- Variáveis Globais de Conexão ---
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
KEY_FILE_PATH = os.path.join(SCRIPT_PATH, "data", "firebase-key.json")
DATABASE_URL = "https://sistema-veritas-default-rtdb.firebaseio.com/"

# --- Função de Inicialização ---
def init_firebase():
    """Conecta-se ao banco de dados na nuvem."""
    try:
        cred = credentials.Certificate(KEY_FILE_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': DATABASE_URL
        })
        print("Conexão com Firebase estabelecida com sucesso!")
        return True
    except ValueError:
        print("Firebase já foi inicializado.")
        return True
    except FileNotFoundError:
        messagebox.showerror("Erro Crítico de Firebase", 
                             f"O arquivo-chave 'firebase-key.json' não foi encontrado em:\n{KEY_FILE_PATH}\n\nO aplicativo não pode se conectar à nuvem.")
        return False
    except Exception as e:
        messagebox.showerror("Erro de Conexão Firebase", 
                             f"Não foi possível conectar ao Firebase:\n{e}\n\n{traceback.format_exc()}")
        return False

# --- Funções de Consultores ---
def carregar_consultores():
    """Lê a lista de consultores do Firebase."""
    try:
        ref = db.reference('/consultores')
        data = ref.get()
        return data if data else []
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao carregar consultores: {e}")
        return []

def salvar_consultores(lista_consultores):
    """Salva a lista de consultores no Firebase."""
    try:
        ref = db.reference('/consultores')
        ref.set(lista_consultores)
        return True
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao salvar consultores: {e}")
        return False

# --- Funções de Folgas ---
def carregar_folgas():
    """Lê o dicionário de folgas do Firebase."""
    try:
        ref = db.reference('/folgas')
        data = ref.get()
        return data if data else {}
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao carregar folgas: {e}")
        return {}

def salvar_folgas(dados_folgas):
    """Salva o dicionário de folgas no Firebase."""
    try:
        ref = db.reference('/folgas')
        ref.set(dados_folgas)
        return True
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao salvar folgas: {e}")
        return False

# --- Funções de Marcas (NOVA LÓGICA) ---
def carregar_marcas():
    """Lê o DICIONÁRIO de marcas do Firebase."""
    try:
        # 1. Novo caminho no Firebase
        ref = db.reference('/marcas_liberadas') 
        data = ref.get()
        # 2. Retorna um dicionário vazio se nada for encontrado
        return data if data else {} 
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao carregar marcas: {e}")
        return {} # Retorna um dicionário vazio em caso de erro

def salvar_marcas(dados_marcas):
    """Salva o DICIONÁRIO de marcas no Firebase."""
    try:
        # 1. Novo caminho no Firebase
        ref = db.reference('/marcas_liberadas')
        ref.set(dados_marcas)
        return True
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao salvar marcas: {e}")
        return False