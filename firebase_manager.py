# -*- coding: utf-8 -*-

"""
Arquivo: firebase_manager.py
Descrição: Gerencia toda a comunicação com o Firebase (RTDB) e ImageKit.io.
(v5.7.1 - Corrige crash silencioso na inicialização)
"""

import firebase_admin
from firebase_admin import credentials, db 
from tkinter import messagebox
import os
import traceback # <-- Importado para mostrar o erro completo
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
TEMP_UPLOAD_PATH = os.path.join(SCRIPT_PATH, "temp_upload.jpg") # Caminho do arquivo temporário

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
        # --- ***** CORREÇÃO ***** ---
        # MUDADO DE MESSAGEBOX PARA PRINT
        print("="*50)
        print("ERRO CRÍTICO DE FIREBASE")
        print(f"O arquivo-chave 'firebase-key.json' não foi encontrado em:\n{KEY_FILE_PATH}")
        print("O aplicativo não pode se conectar à nuvem.")
        print("="*50)
        # --- ***** FIM DA CORREÇÃO ***** ---
        return False
    except Exception as e:
        # --- ***** CORREÇÃO ***** ---
        # MUDADO DE MESSAGEBOX PARA PRINT
        print("="*50)
        print("ERRO DE CONEXÃO FIREBASE")
        print(f"Não foi possível conectar ao Firebase:\n{e}")
        print("="*50)
        traceback.print_exc() # Imprime o traceback completo
        # --- ***** FIM DA CORREÇÃO ***** ---
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

# --- Funções de Achados e Perdidos ---

def upload_foto_item_imagekit(imagem_pil, n_controle):
    """
    (ImageKit) Faz o upload de uma imagem (PIL) para o ImageKit.io.
    RETORNA: (url_da_imagem, file_id_da_imagem)
    MÉTODO: Salva em disco e faz upload do arquivo (Plano B).
    """
    if not imagekit:
        messagebox.showerror("Erro de Upload", "ImageKit não inicializado.")
        return None, None
        
    try:
        # 1. Salva a imagem PIL em um arquivo temporário
        imagem_pil.save(TEMP_UPLOAD_PATH, format='JPEG', quality=85)

        # 2. Prepara as opções como um OBJETO
        class OpcoesDeUpload:
            pass
            
        options = OpcoesDeUpload()
        options.folder = "achados_e_perdidos/"
        options.is_private_file = False
        
        # 3. Faz o upload abrindo o ARQUIVO salvo
        with open(TEMP_UPLOAD_PATH, "rb") as f:
            upload_response = imagekit.upload(
                file=f, # Passa o arquivo aberto
                file_name=f"item_{n_controle}.jpg",
                options=options
            )
        
        # 4. Pega a URL e o FILE_ID
        url_da_imagem = upload_response.url
        file_id_da_imagem = upload_response.file_id
        
        return url_da_imagem, file_id_da_imagem # <-- RETORNA OS DOIS

    except Exception as e:
        messagebox.showerror("Erro de Upload (ImageKit)", f"Não foi possível salvar a foto no ImageKit.\n\nTraceback: {e}\n\n{traceback.format_exc()}")
        return None, None
        
    finally:
        # 5. SEMPRE apaga o arquivo temporário, mesmo se falhar
        if os.path.exists(TEMP_UPLOAD_PATH):
            try:
                os.remove(TEMP_UPLOAD_PATH)
            except Exception as e:
                print(f"AVISO: Não foi possível apagar o arquivo temporário: {e}")


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

def carregar_itens_achados():
    """
    (RTDB) Carrega TODOS os itens da coleção 'achados_e_perdidos'.
    """
    if not db_ref: return {}
    try:
        ref = db_ref.child('achados_e_perdidos')
        data = ref.get()
        return data if data else {}
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao carregar itens de Achados e Perdidos: {e}")
        return {}

def excluir_item_achado(item_id):
    """
    (RTDB) Exclui um item da coleção 'achados_e_perdidos'
    """
    if not db_ref: return False
    try:
        ref = db_ref.child(f'achados_e_perdidos/{item_id}')
        ref.delete()
        return True
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao excluir item do RTDB: {e}")
        return False

def excluir_foto_item_imagekit(file_id):
    """
    (ImageKit) Exclui um arquivo de foto do ImageKit usando seu file_id.
    """
    if not imagekit: return False
    try:
        imagekit.delete_file(file_id)
        return True
    except Exception as e:
        # Não mostra um erro, só avisa no console
        print(f"AVISO: Falha ao excluir foto do ImageKit (ID: {file_id}). Erro: {e}")
        return False
        
# --- ***** NOVAS FUNÇÕES: CAIXA DE COMISSÃO ***** ---

def carregar_caixa_comissao():
    """
    (RTDB) Carrega TODOS os registros do caixa de comissão.
    """
    if not db_ref: return {}
    try:
        ref = db_ref.child('caixa_comissao') 
        data = ref.get()
        return data if data else {} 
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao carregar o caixa de comissão: {e}")
        return {} 

def salvar_caixa_comissao(dados_caixa):
    """
    (RTDB) Salva os dados completos do caixa de comissão.
    """
    if not db_ref: return False
    try:
        ref = db_ref.child('caixa_comissao')
        ref.set(dados_caixa)
        return True
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao salvar o caixa de comissão: {e}")
        return False

def carregar_pins_consultores():
    """
    (RTDB) Carrega a lista de PINs dos consultores.
    """
    if not db_ref: return {}
    try:
        ref = db_ref.child('pins_consultores') 
        data = ref.get()
        return data if data else {} 
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao carregar PINs: {e}")
        return {} 

def salvar_pins_consultores(dados_pins):
    """
    (RTDB) Salva a lista de PINs dos consultores.
    """
    if not db_ref: return False
    try:
        ref = db_ref.child('pins_consultores')
        ref.set(dados_pins)
        return True
    except Exception as e:
        messagebox.showerror("Erro Firebase", f"Erro ao salvar PINs: {e}")
        return False