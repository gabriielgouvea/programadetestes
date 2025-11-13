# -*- coding: utf-8 -*-

"""
Arquivo: firebase_manager.py
Descrição: Gerencia toda a comunicação com o Firebase (RTDB) e ImageKit.io.
(v5.4.2 - Correção final do upload para v4.2.0)
"""

import firebase_admin
from firebase_admin import credentials, db 
from tkinter import messagebox
import os
import traceback
import io
from PIL import Image

# --- IMPORTAÇÃO CORRETA ---
# Só precisamos do ImageKit, nada mais
from imagekitio import ImageKit

# --- Variáveis Globais de Conexão ---
db_ref = None # Para o Realtime Database
imagekit = None # Para o ImageKit
FIREBASE_CONECTADO = False

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
KEY_FILE_PATH = os.path.join(SCRIPT_PATH, "data", "firebase-key.json")

# --- URL DO SEU RTDB ---
DATABASE_URL = "https://sistema-veritas-default-rtdb.firebaseio.com/" 

# --- SUAS CHAVES DO IMAGEKIT ---
IMAGEKIT_PUBLIC_KEY = "public_XBK11UgP67lvAoT5ECT+uH3V7Vo="
IMAGEKIT_PRIVATE_KEY = "private_TfSk2SKzt+spb7ankn77WybmUlg="
IMAGEKIT_URL_ENDPOINT = "https://ik.imagekit.io/2ewjhonqc"


def init_firebase():
    """Conecta-se ao Realtime Database E ao ImageKit."""
    global db_ref, imagekit, FIREBASE_CONECTADO
    
    if FIREBASE_CONECTADO:
        return True

    try:
        # 1. Conecta ao Firebase (RTDB)
        cred = credentials.Certificate(KEY_FILE_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': DATABASE_URL
        })
        db_ref = db.reference() # Pega a referência do Realtime Database
        
        # Testa a conexão
        db_ref.child('consultores').order_by_key().limit_to_first(1).get() 
        
        # 2. Conecta ao ImageKit
        global imagekit
        imagekit = ImageKit(
            public_key=IMAGEKIT_PUBLIC_KEY,
            private_key=IMAGEKIT_PRIVATE_KEY,
            url_endpoint=IMAGEKIT_URL_ENDPOINT
        )
        
        print("Conexão com Firebase (RTDB) e ImageKit estabelecida com sucesso!")
        FIREBASE_CONECTADO = True
        return True
        
    except ValueError:
         # Se já foi inicializado (erro comum)
        print("Firebase já foi inicializado.")
        db_ref = db.reference()
        FIREBASE_CONECTADO = True
        return True
    except FileNotFoundError:
        messagebox.showerror("Erro Crítico de Firebase", 
                             f"O arquivo-chave 'firebase-key.json' não foi encontrado em:\n{KEY_FILE_PATH}\n\nO aplicativo não pode se conectar à nuvem.")
        return False
    except Exception as e:
        messagebox.showerror("Erro de Conexão Firebase", 
                             f"Não foi possível conectar ao Firebase:\n{e}\n\n{traceback.format_exc()}")
        return False

# --- Funções de Consultores (RTDB) ---
def carregar_consultores():
    if not db_ref: return []
    try:
        ref = db_ref.child('consultores')
        data = ref.get()
        return data if data else []
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao carregar consultores: {e}")
        return []

def salvar_consultores(lista_consultores):
    if not db_ref: return False
    try:
        ref = db_ref.child('consultores')
        ref.set(lista_consultores)
        return True
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao salvar consultores: {e}")
        return False

# --- Funções de Folgas (RTDB) ---
def carregar_folgas():
    if not db_ref: return {}
    try:
        ref = db_ref.child('folgas')
        data = ref.get()
        return data if data else {}
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao carregar folgas: {e}")
        return {}

def salvar_folgas(dados_folgas):
    if not db_ref: return False
    try:
        ref = db_ref.child('folgas')
        ref.set(dados_folgas)
        return True
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao salvar folgas: {e}")
        return False

# --- Funções de Marcas (RTDB) ---
def carregar_marcas():
    if not db_ref: return {}
    try:
        ref = db_ref.child('marcas_liberadas') 
        data = ref.get()
        return data if data else {} 
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao carregar marcas: {e}")
        return {} 

def salvar_marcas(dados_marcas):
    if not db_ref: return False
    try:
        ref = db_ref.child('marcas_liberadas')
        ref.set(dados_marcas)
        return True
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao salvar marcas: {e}")
        return False

# --- NOVO: Funções de Achados e Perdidos ---

def upload_foto_item_imagekit(imagem_pil, n_controle):
    """
    (ImageKit) Faz o upload de uma imagem (PIL) para o ImageKit.io.
    Retorna a URL pública da imagem. (Compatível com v4.2.0)
    """
    if not imagekit:
        messagebox.showerror("Erro de Upload", "ImageKit não inicializado.")
        return None
        
    try:
        # Converte a imagem PIL para bytes
        img_byte_arr = io.BytesIO()
        imagem_pil.save(img_byte_arr, format='JPEG', quality=85)
        img_bytes = img_byte_arr.getvalue() # Pega os bytes crus

        # --- ESTA É A CORREÇÃO (v4.2.0) ---
        # A v4.2.0 espera um dicionário 'options'
        options = {
            "folder": "achados_e_perdidos/",
            "is_private_file": False
        }
        
        # 2. Faz o upload passando o objeto
        upload_response = imagekit.upload(
            file=img_bytes,
            file_name=f"item_{n_controle}.jpg",
            options=options # Passa o dicionário de opções
        )
        
        # 3. A v4.2.0 retorna um objeto, então acessamos com .url
        return upload_response.url
        # --- FIM DA CORREÇÃO ---

    except Exception as e:
        messagebox.showerror("Erro de Upload (ImageKit)", f"Não foi possível salvar a foto no ImageKit.\n\nErro: {e}")
        return None

def salvar_novo_item_achado(item_data):
    """
    (RTDB) Salva os dados do novo item na coleção 'achados_e_perdidos'.
    Usa o 'id_controle' como o ID do documento.
    """
    if not db_ref: return False
    try:
        id_documento = item_data['id_controle']
        # Salva os dados no Realtime Database
        ref = db_ref.child(f'achados_e_perdidos/{id_documento}')
        ref.set(item_data)
        return True
    except Exception as e:
        messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar os dados do item no RTDB.\n\nErro: {e}")
        return False