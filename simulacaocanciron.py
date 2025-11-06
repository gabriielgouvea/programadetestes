# -*- coding: utf-8 -*-
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.toast import ToastNotification
# Importamos Panedwindow (com W maiúsculo) do ttkbootstrap, que é o correto
from ttkbootstrap.widgets import Panedwindow
from ttkbootstrap.scrolled import ScrolledFrame
from tkinter import messagebox, Toplevel, Entry, Button, StringVar, scrolledtext, \
    PhotoImage, Listbox, filedialog, END, ANCHOR
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import os
import sys
import requests
import json
import webbrowser
import platform
import csv
import traceback # Para capturar erros do PDF
try:
    from PIL import Image, ImageTk, ImageDraw, ImageOps
    import piexif
except ImportError:
    messagebox.showerror("Erro de Dependência", "Pillow e Piexif são necessários. Rode 'pip install Pillow piexif'")

# --- NOVA IMPORTAÇÃO ---
try:
    from calculadora_core import processar_pdf
except ImportError:
    messagebox.showerror("Erro de Arquivo", "Arquivo 'calculadora_core.py' não encontrado.\n\nCertifique-se que ele está na mesma pasta que 'testesimulacao.py'.")
    sys.exit()

import shutil
# --- IMPORTAÇÕES DO LOCUTOR (VOZ NATURAL EDGE) ---
import asyncio              # Necessário para o edge-tts
from edge_tts import Communicate  # O motor de voz do Edge
from playsound import playsound # O player de áudio
# (O 'os' e 'traceback' já foram importados acima)

# --- Variáveis Globais e Constantes ---
APP_VERSION = "4.0.1-Crash-Fix" # (Versão de teste, pode mudar)
VERSION_URL = "https://raw.githubusercontent.com/gabriielgouvea/veritas/main/version.json"

# CORREÇÃO: Define o caminho da pasta 'data'
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_FOLDER_PATH = os.path.join(SCRIPT_PATH, "data") # Pasta para todos os dados
CONSULTORES_JSON_PATH = os.path.join(DATA_FOLDER_PATH, "consultores.json") # Caminho completo do JSON
FOLGAS_JSON_PATH = os.path.join(DATA_FOLDER_PATH, "folgas.json")
LOCUTOR_JSON_PATH = os.path.join(DATA_FOLDER_PATH, "locutor_mensagens.json") # <-- NOVO JSON

calculo_resultado = {}
consultor_selecionado = None
consultor_logado_data = {}
PROFILE_PIC_SIZE = (96, 96)
ICON_SIZE = (22, 22)

PLANOS = {
    'Anual (12 meses)': {'valor': 359.00, 'duracao': 12},
    'Semestral (6 meses)': {'valor': 499.00, 'duracao': 6}
}
MOTIVOS_CANCELAMENTO = [
    "NÃO GOSTEI DO ATENDIMENTO DOS PROFESSORES",
    "NÃO GOSTEI DO ATENDIMENTO DA RECEPÇÃO",
    "ESTOU COM PROBLEMAS DE SAÚDE",
    "ESTOU COM DIFICULDADE FINANCEIRA",
    "MUDEI DE ENDEREÇO",
    "OUTROS"
]

# --- Lógica de Dados ---
def carregar_consultores():
    try:
        with open(CONSULTORES_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        messagebox.showerror("Erro Crítico", f"{CONSULTORES_JSON_PATH} não encontrado!")
        if not os.path.exists(DATA_FOLDER_PATH):
            os.makedirs(DATA_FOLDER_PATH)
            messagebox.showinfo("Pasta Criada", f"Pasta 'data' não encontrada. Criei ela para você.\n\nPor favor, adicione o 'consultores.json' e os ícones lá.")
        return []
    except Exception as e:
        messagebox.showerror("Erro ao Ler JSON", f"Erro ao ler {CONSULTORES_JSON_PATH}: {e}")
        return []

def salvar_consultores(lista_consultores):
    try:
        with open(CONSULTORES_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(lista_consultores, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar {CONSULTORES_JSON_PATH}: {e}")
        return False

def carregar_folgas():
    """Lê o arquivo JSON de folgas."""
    try:
        with open(FOLGAS_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        messagebox.showerror("Erro ao Ler Folgas", f"Erro ao ler {FOLGAS_JSON_PATH}: {e}")
        return {}

def salvar_folgas(dados_folgas):
    """Salva os dados de folgas no arquivo JSON."""
    try:
        with open(FOLGAS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(dados_folgas, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        messagebox.showerror("Erro ao Salvar Folgas", f"Não foi possível salvar {FOLGAS_JSON_PATH}: {e}")
        return False

# --- NOVAS FUNÇÕES DE DADOS (LOCUTOR) ---
def carregar_mensagens_locutor():
    """Lê o arquivo JSON de mensagens do locutor."""
    try:
        with open(LOCUTOR_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Se não achar, cria um arquivo com uma lista vazia
        salvar_mensagens_locutor([])
        return []
    except Exception as e:
        messagebox.showerror("Erro ao Ler Mensagens", f"Erro ao ler {LOCUTOR_JSON_PATH}: {e}")
        return []

def salvar_mensagens_locutor(lista_mensagens):
    """Salva a lista de mensagens no arquivo JSON."""
    try:
        with open(LOCUTOR_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(lista_mensagens, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        messagebox.showerror("Erro ao Salvar Mensagens", f"Não foi possível salvar {LOCUTOR_JSON_PATH}: {e}")
        return False

# --- FUNÇÕES AUXILIARES (Lógica e Validação) ---
def check_for_updates():
    try:
        response = requests.get(VERSION_URL, timeout=10); response.raise_for_status()
        online_data = response.json(); online_version = online_data["version"]; download_url = online_data["download_url"]
        if online_version > APP_VERSION:
            msg = f"Uma nova versão ({online_version}) está disponível!\n\nA sua versão atual é {APP_VERSION}.\n\nDeseja ir para a página de download?"
            if messagebox.askyesno("Atualização Disponível", msg): webbrowser.open(download_url)
        else: messagebox.showinfo("Verificar Atualizações", "Você já está com a versão mais recente do programa.")
    except Exception as e: messagebox.showerror("Erro de Conexão", f"Não foi possível verificar as atualizações.\nVerifique sua conexão com a internet.\n\nErro: {e}")
def validar_matricula(P):
    if len(P) > 6: return False
    return str.isdigit(P) or P == ""
def validar_e_formatar_cpf_input(P):
    numeros = ''.join(filter(str.isdigit, P))
    if len(numeros) > 11: return False
    return True
def limpar_cpf(cpf_sujo): return ''.join(filter(str.isdigit, cpf_sujo))
def validar_cpf_algoritmo(cpf):
    cpf = limpar_cpf(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11: return False
    try:
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9)); digito1 = (soma * 10 % 11) % 10
        if digito1 != int(cpf[9]): return False
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10)); digito2 = (soma * 10 % 11) % 10
        if digito2 != int(cpf[10]): return False
    except ValueError: return False
    return True

def formatar_data(event, entry):
    texto_atual = entry.get(); numeros = "".join(filter(str.isdigit, texto_atual)); data_formatada = ""
    if len(numeros) > 0: data_formatada = numeros[:2]
    if len(numeros) > 2: data_formatada += "/" + numeros[2:4]
    if len(numeros) > 4: data_formatada += "/" + numeros[4:8]
    entry.delete(0, 'end'); entry.insert(0, data_formatada); entry.icursor('end')

def formatar_reais(valor):
    """Formata um float para o padrão R$ 1.234,56"""
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def logica_de_calculo(data_inicio, tipo_plano_str, parcelas_em_atraso_str, pagamento_hoje_confirmado=None):
    try:
        parcelas_em_atraso = int(parcelas_em_atraso_str)
        plano_selecionado = PLANOS[tipo_plano_str]
        valor_mensalidade = plano_selecionado['valor']
        duracao_plano = plano_selecionado['duracao']
        data_hoje = date.today()
        if data_inicio < date(2024, 10, 1): return {'erro_data': "A data de início não pode ser anterior a Outubro de 2024."}
        diff = relativedelta(data_hoje, data_inicio)
        meses_passados_total = diff.years * 12 + diff.months
        ultimo_vencimento_ocorrido = data_inicio + relativedelta(months=meses_passados_total)
        if data_hoje < ultimo_vencimento_ocorrido:
            meses_efetivamente_pagos = meses_passados_total
            proximo_vencimento = ultimo_vencimento_ocorrido
        else:
            meses_efetivamente_pagos = meses_passados_total + 1
            proximo_vencimento = ultimo_vencimento_ocorrido + relativedelta(months=1)
        valor_mensalidade_adicional = 0.0; meses_a_pagar_adiantado = 0; linha_mensalidade_adicional = "Não se aplica"
        if data_hoje.day == data_inicio.day and data_hoje >= data_inicio:
            if pagamento_hoje_confirmado is False:
                valor_mensalidade_adicional = valor_mensalidade; meses_a_pagar_adiantado = 1
                linha_mensalidade_adicional = f"R$ {valor_mensalidade:.2f} (referente a hoje - {data_hoje.strftime('%d/%m/%Y')})"
        else:
            dias_para_vencimento = (proximo_vencimento - data_hoje).days
            if 0 < dias_para_vencimento <= 30:
                valor_mensalidade_adicional = valor_mensalidade; meses_a_pagar_adiantado = 1
                linha_mensalidade_adicional = f"R$ {valor_mensalidade:.2f} (em {dias_para_vencimento} dias - {proximo_vencimento.strftime('%d/%m/%Y')})"
        meses_restantes_contrato = duracao_plano - meses_efetivamente_pagos
        is_due_date_scenario = data_hoje.day == data_inicio.day and data_hoje >= data_inicio
        is_30_day_rule_scenario = meses_a_pagar_adiantado > 0 and not is_due_date_scenario
        if is_30_day_rule_scenario: meses_para_multa = max(0, meses_restantes_contrato - 1)
        else: meses_para_multa = max(0, meses_restantes_contrato)
        valor_multa = (meses_para_multa * valor_mensalidade) * 0.10
        valor_atrasado = parcelas_em_atraso * valor_mensalidade
        total_a_pagar = valor_atrasado + valor_mensalidade_adicional + valor_multa
        if data_hoje.day == data_inicio.day and data_hoje >= data_inicio: data_acesso_final = proximo_vencimento + relativedelta(days=-1)
        elif meses_a_pagar_adiantado > 0: data_acesso_final = proximo_vencimento + relativedelta(months=1, days=-1)
        else: data_acesso_final = proximo_vencimento + relativedelta(days=-1)
        return {'data_simulacao': data_hoje, 'plano': tipo_plano_str, 'valor_plano': valor_mensalidade,
                'data_inicio_contrato': data_inicio, 'parcelas_atrasadas_qtd': parcelas_em_atraso,
                'valor_atrasado': valor_atrasado, 'linha_mensalidade_a_vencer': linha_mensalidade_adicional,
                'meses_para_multa': meses_para_multa, 'valor_multa': valor_multa,
                'total_a_pagar': total_a_pagar, 'data_acesso_final': data_acesso_final,
                'valor_proxima_parcela': valor_mensalidade_adicional,
                'vencimento_proxima': proximo_vencimento.strftime('%d/%m/%Y') if valor_mensalidade_adicional > 0 else "Não se aplica"}
    except Exception as e:
        import traceback; print(traceback.format_exc()); return {'erro_geral': f"Erro no cálculo. Verifique os dados.\nDetalhe: {e}"}


# --- CLASSE PRINCIPAL DA APLICAÇÃO ---

class App(ttk.Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- Variáveis de Estilo ---
        self.FONT_MAIN = ("Helvetica", 11)
        self.FONT_BOLD = ("Helvetica", 11, "bold")
        self.FONT_TITLE = ("Helvetica", 18, "bold")
        self.FONT_TITLE_LOGIN = ("Helvetica", 32, "bold")
        self.FONT_SMALL = ("Helvetica", 9)

        self.COLOR_SIDEBAR_LIGHT = "#ffffff"
        self.COLOR_BTN_HOVER_LIGHT = "#f0f0f0"
        self.COLOR_BTN_SELECTED_LIGHT = "#e0eafb"
        self.COLOR_TEXT_LIGHT = "#212529"

        # --- Configuração da Janela ---
        self.title(f"Veritas | Sistema de Gestão v{APP_VERSION} (TESTE LOCUTOR EDGE)") # Mudei o título
        self.state('zoomed')
        self.resizable(True, True)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- Carregar Dados dos Consultores ---
        self.lista_completa_consultores = carregar_consultores()
        self.nomes_consultores = [c['nome'] for c in self.lista_completa_consultores]
        
        # --- Carregar Dados do Locutor ---
        self.lista_mensagens_locutor = carregar_mensagens_locutor()

        # --- Dados das Folgas (carregados pela tela) ---
        self.dados_folgas = {} # Agora é um dicionário

        # --- Carregar Imagens ---
        self.load_images()

        # --- Criar Estilos Customizados ---
        self.create_custom_styles()

        # --- SIDEBAR (Menu) ---
        self.sidebar_frame = ttk.Frame(self, style='Sidebar.TFrame', width=300)
        self.sidebar_frame.grid(row=0, column=0, sticky="ns")
        self.sidebar_frame.grid_propagate(False)
        self.sidebar_frame.grid_rowconfigure(9, weight=1) # Ajustado para novo layout

        # --- ÁREA DE CONTEÚDO PRINCIPAL ---
        self.main_frame = ttk.Frame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # --- WIDGETS DA SIDEBAR ---
        self.create_sidebar_widgets()

        # --- FOOTER ---
        footer_frame = ttk.Frame(self)
        footer_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.footer_label = ttk.Label(footer_frame, text="    Desenvolvido por Gabriel Gouvêa com seus parceiros GPT & Gemini 🤖", style='secondary.TLabel')
        self.footer_label.pack(fill='x')

        # --- Iniciar na Tela de Login ---
        self.show_login_view()
        self.style.theme_use('flatly')


    def load_images(self):
        """Carrega todas as imagens e ícones."""

        placeholder_img = Image.new('RGBA', PROFILE_PIC_SIZE, (0,0,0,0))
        draw = ImageDraw.Draw(placeholder_img)
        draw.ellipse((0, 0, PROFILE_PIC_SIZE[0], PROFILE_PIC_SIZE[1]), fill='#cccccc')
        self.default_profile_photo = ImageTk.PhotoImage(placeholder_img)
        self.dev_preview_photo_tk = self.default_profile_photo

        self.default_icon = ImageTk.PhotoImage(Image.new('RGBA', ICON_SIZE, (0,0,0,0)))

        self.profile_photo = self.default_profile_photo

        try:
            self.icon_simulador = ImageTk.PhotoImage(Image.open(os.path.join(DATA_FOLDER_PATH, "calculator.png")).resize(ICON_SIZE))
            self.icon_comissao = ImageTk.PhotoImage(Image.open(os.path.join(DATA_FOLDER_PATH, "commission.png")).resize(ICON_SIZE))
            self.icon_folgas = ImageTk.PhotoImage(Image.open(os.path.join(DATA_FOLDER_PATH, "days_off.png")).resize(ICON_SIZE))
            self.icon_updates = ImageTk.PhotoImage(Image.open(os.path.join(DATA_FOLDER_PATH, "updates.png")).resize(ICON_SIZE))
            self.icon_developer = ImageTk.PhotoImage(Image.open(os.path.join(DATA_FOLDER_PATH, "developer.png")).resize(ICON_SIZE))
        except Exception as e:
            messagebox.showerror("Erro ao Carregar Ícones", f"Não foi possível carregar alguns ícones da pasta 'data'.\n\nVerifique se os ícones necessários estão na pasta 'data'.\n\nErro: {e}")
            self.icon_simulador = self.icon_comissao = self.icon_folgas = self.default_icon
            self.icon_updates = self.icon_developer = self.default_icon

        # --- *** CORREÇÃO: REDIMENSIONAR A LOGO *** ---
        try:
            img_logo_original = Image.open(os.path.join(DATA_FOLDER_PATH, "logo_completa.png"))

            # Pega o tamanho original
            original_width, original_height = img_logo_original.size

            # Define a largura máxima que queremos para a logo
            max_width = 500

            # Calcula a nova altura mantendo a proporção
            ratio = max_width / float(original_width)
            new_height = int(float(original_height) * float(ratio))

            # Redimensiona a imagem com alta qualidade (LANCZOS)
            img_logo_resized = img_logo_original.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Converte para PhotoImage
            self.logo_login = ImageTk.PhotoImage(img_logo_resized)

        except Exception as e:
            print(f"AVISO: Não foi possível carregar a logo_completa.png: {e}")
            self.logo_login = None # Define como None se falhar

        # --- Ícone 'fantasma' para o Locutor (temporário) ---
        # (Você pode trocar por um "microphone.png" depois)
        self.icon_locutor = self.icon_developer # Vamos usar o ícone do dev por enquanto


    def load_profile_picture(self, foto_path, size=PROFILE_PIC_SIZE, is_dev_preview=False):
        """Carrega e aplica a foto de perfil do consultor, agora circular."""
        try:
            path_completo = os.path.join(DATA_FOLDER_PATH, foto_path)
            if not os.path.exists(path_completo):
                print(f"Aviso: Foto não encontrada em {path_completo}. Usando placeholder.")
                placeholder_path = os.path.join(DATA_FOLDER_PATH, "default_profile.png")
                img_profile = Image.open(placeholder_path)
                print("Usando 'default_profile.png'")
            else:
                img_profile = Image.open(path_completo)

            img_profile = self.fix_image_rotation(img_profile)

            mask = Image.new("L", size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size[0], size[1]), fill=255)
            img_circular = Image.new("RGBA", size, (0,0,0,0))
            img_circular.paste(img_profile.resize(size), (0, 0), mask)
            loaded_photo = ImageTk.PhotoImage(img_circular)

        except Exception as e:
            print(f"Erro ao carregar a foto de perfil {foto_path}: {e}")
            placeholder_img = Image.new('RGBA', PROFILE_PIC_SIZE, (0,0,0,0))
            draw = ImageDraw.Draw(placeholder_img)
            draw.ellipse((0, 0, PROFILE_PIC_SIZE[0], PROFILE_PIC_SIZE[1]), fill='#cccccc')
            loaded_photo = ImageTk.PhotoImage(placeholder_img)

        if is_dev_preview:
            self.dev_preview_photo_tk = loaded_photo
            self.dev_foto_label.config(image=self.dev_preview_photo_tk)
        else:
            self.profile_photo = loaded_photo
            self.profile_pic_label.config(image=self.profile_photo)

    def fix_image_rotation(self, img):
        """Lê os dados EXIF de uma imagem e a rotaciona corretamente."""
        try:
            exif = piexif.load(img.info['exif'])
            orientation = exif['0th'][piexif.ImageIFD.Orientation]
        except (KeyError, AttributeError, TypeError, ValueError):
            orientation = 1
        if orientation == 3: img = img.rotate(180, expand=True)
        elif orientation == 6: img = img.rotate(270, expand=True)
        elif orientation == 8: img = img.rotate(90, expand=True)
        return img


    def create_custom_styles(self):
        """Cria os estilos customizados para os botões da sidebar."""
        style = self.style

        style.configure('Sidebar.TFrame', background=self.COLOR_SIDEBAR_LIGHT)
        style.configure('Sidebar.TLabel', background=self.COLOR_SIDEBAR_LIGHT, foreground=self.COLOR_TEXT_LIGHT, font=self.FONT_BOLD)

        style.configure('Nav.Toolbutton',
                        background=self.COLOR_SIDEBAR_LIGHT,
                        foreground=self.COLOR_TEXT_LIGHT,
                        anchor='w', compound='left', padding=(15, 10),
                        font=self.FONT_MAIN, borderwidth=0)
        style.map('Nav.Toolbutton',
                  background=[('active', self.COLOR_BTN_HOVER_LIGHT),
                              ('selected', self.COLOR_BTN_SELECTED_LIGHT)],
                  foreground=[('selected', self.COLOR_TEXT_LIGHT)])


    def create_sidebar_widgets(self):
        """Cria todos os widgets dentro da sidebar."""

        self.profile_frame = ttk.Frame(self.sidebar_frame, style='Sidebar.TFrame')
        self.profile_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.profile_frame.grid_columnconfigure(0, weight=1)

        self.profile_pic_label = ttk.Label(self.profile_frame, image=self.profile_photo, background=self.COLOR_SIDEBAR_LIGHT)
        self.profile_pic_label.grid(row=0, column=0, pady=(0, 10))

        self.consultant_label = ttk.Label(self.profile_frame, text="Bem-vindo", style='Sidebar.TLabel', font=self.FONT_BOLD)
        self.consultant_label.grid(row=1, column=0, pady=(0, 5))

        self.trocar_consultor_button = ttk.Button(self.profile_frame, text="Fazer Login",
                                                  command=self.show_login_view, style='Link.TButton')
        self.trocar_consultor_button.grid(row=2, column=0, pady=(0, 10))

        ttk.Separator(self.sidebar_frame).grid(row=1, column=0, sticky='ew', padx=10, pady=10)

        # --- BOTÕES DE NAVEGAÇÃO ---
        self.nav_var = StringVar()
        self.nav_buttons = {}

        def create_nav_button(row, text, value, icon):
            btn = ttk.Radiobutton(self.sidebar_frame,
                                  text=text,
                                  image=icon,
                                  variable=self.nav_var,
                                  value=value,
                                  command=self.on_nav_select,
                                  style='Nav.Toolbutton') # Estilo principal
            btn.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
            self.nav_buttons[value] = btn

        # --- BOTÕES DO MENU ATUALIZADOS ---
        # (Ordem corrigida conforme sua solicitação)
        create_nav_button(2, "Simulador", "simulador", self.icon_simulador)
        create_nav_button(3, "Calculadora Comissão", "comissao", self.icon_comissao)
        create_nav_button(4, "Folgas", "folgas", self.icon_folgas)
        create_nav_button(5, "Locutor", "locutor", self.icon_locutor) # <-- LINHA 5
        create_nav_button(6, "Área do Desenvolvedor", "developer", self.icon_developer) # <-- LINHA 6
        create_nav_button(7, "Verificar Atualizações", "updates", self.icon_updates) # <-- LINHA 7

        self.sidebar_frame.grid_rowconfigure(8, weight=1) # <-- LINHA 8
        ttk.Separator(self.sidebar_frame).grid(row=9, column=0, sticky='sew', padx=10, pady=10) # <-- LINHA 9


    def on_nav_select(self):
        """Chamado quando um botão de navegação é clicado."""
        view_name = self.nav_var.get()

        if view_name == "updates":
            check_for_updates()
            if hasattr(self, '_last_selected_nav'): self.nav_var.set(self._last_selected_nav)
            else: self.nav_var.set("")
        elif view_name == "developer":
            pin_ok = self.show_developer_login()
            if pin_ok:
                self.show_view("developer_area")
                self._last_selected_nav = "developer_area"
            else:
                if hasattr(self, '_last_selected_nav'): self.nav_var.set(self._last_selected_nav)
                else: self.nav_var.set("")
        # --- Lógica 'locutor' simplificada ---
        elif view_name == "locutor":
            self.show_view(view_name)
            self._last_selected_nav = view_name
        else:
            self.show_view(view_name)
            self._last_selected_nav = view_name # Guarda a última seleção válida

    def show_toast(self, title, message, bootstyle='success'):
        toast = ToastNotification(title=title, message=message, duration=3000, bootstyle=bootstyle, position=(20, 20, 'se'))
        toast.show_toast()

    def show_view(self, view_name):
        """Limpa o frame principal e carrega a nova 'tela'."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # --- DICIONÁRIO DE VIEWS ATUALIZADO ---
        view_creators = {
            "simulador": self.create_cancellation_view,
            "comissao": self.create_comissao_view,
            "folgas": self.create_folgas_view,
            "developer_area": self.create_developer_area_view,
            "locutor": self.create_locutor_view # <-- ADICIONADO
        }

        creator_func = view_creators.get(view_name)
        if creator_func:
            creator_func()

    def show_login_view(self):
        """Mostra a tela de login, escondendo a sidebar."""
        self.sidebar_frame.grid_remove()
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        login_container = ttk.Frame(self.main_frame)
        login_container.pack(expand=True)

        # --- MOSTRA A LOGO OU O TEXTO ---
        if hasattr(self, 'logo_login') and self.logo_login:
            # Se a imagem da logo foi carregada, mostre-a
            ttk.Label(login_container, image=self.logo_login).pack(pady=(0, 25))
        else:
            # Senão, mostre o texto original como fallback
            ttk.Label(login_container, text="Sistema Veritas", font=self.FONT_TITLE_LOGIN).pack(pady=(0, 25))

        form_frame = ttk.Frame(login_container)
        form_frame.pack(pady=10)

        ttk.Label(form_frame, text="Selecione seu nome:", font=self.FONT_MAIN).pack(anchor='w')

        self.combo_consultor_login = ttk.Combobox(form_frame, values=self.nomes_consultores, width=35, font=self.FONT_MAIN, state="readonly")
        self.combo_consultor_login.pack(pady=(5, 15))

        def on_login():
            global consultor_selecionado, consultor_logado_data
            consultor_selecionado = self.combo_consultor_login.get()
            if not consultor_selecionado:
                messagebox.showwarning("Atenção", "Por favor, selecione um consultor para continuar."); return

            if consultor_selecionado not in self.nomes_consultores:
                 messagebox.showwarning("Consultor Inválido", "O nome digitado não está na lista de consultores.")
                 return

            consultor_logado_data = next((c for c in self.lista_completa_consultores if c['nome'] == consultor_selecionado), None)

            if not consultor_logado_data:
                messagebox.showerror("Erro", "Não foi possível encontrar os dados do consultor.")
                return

            self.consultant_label.config(text=consultor_logado_data['nome'])
            self.load_profile_picture(consultor_logado_data['foto_path'])
            self.trocar_consultor_button.config(text="Trocar Consultor")

            self.sidebar_frame.grid()
            self.nav_var.set("simulador")
            self._last_selected_nav = "simulador"
            self.show_view("simulador")

        ttk.Button(form_frame, text="Entrar", command=on_login, style='success.TButton', width=35, bootstyle="success-solid").pack(pady=10, ipady=5)

    # --- Popups (Seus métodos originais) ---
    def _center_popup(self, popup, width, height):
        self.update_idletasks(); main_x = self.winfo_x(); main_y = self.winfo_y()
        main_width = self.winfo_width(); main_height = self.winfo_height()
        pos_x = main_x + (main_width // 2) - (width // 2)
        pos_y = main_y + (main_height // 2) - (height // 2)
        popup.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        popup.resizable(False, False); popup.transient(self); popup.grab_set()

    def _ask_for_reason_popup(self):
        self.popup_motivo = None; popup = Toplevel(self); popup.title("Motivo do Cancelamento")
        popup_width = 550; popup_height = 450
        self._center_popup(popup, popup_width, popup_height)
        container = ttk.Frame(popup, padding=20); container.pack(fill='both', expand=True)
        ttk.Label(container, text="Selecione o motivo do cancelamento:", font=("-weight bold")).pack(pady=(0, 10), anchor='w')
        selected_reason = StringVar(value=""); self.entry_other_reason = None
        radio_frame = ttk.Frame(container); radio_frame.pack(fill='x', anchor='w')

        def update_other_entry_state():
            if selected_reason.get() == "OUTROS":
                if self.entry_other_reason is None:
                    other_entry_container = ttk.Frame(container)
                    other_entry_container.pack(fill='both', expand=True, pady=5, anchor='w')
                    ttk.Label(other_entry_container, text="Descreva:").pack(side='top', anchor='w')
                    self.entry_other_reason = scrolledtext.ScrolledText(other_entry_container, height=5, width=60, font=self.FONT_MAIN)
                    self.entry_other_reason.pack(side='left', fill='both', expand=True)
                    self.entry_other_reason.focus_set()
            else:
                if self.entry_other_reason is not None:
                    self.entry_other_reason.master.destroy()
                    self.entry_other_reason = None

        for motivo in MOTIVOS_CANCELAMENTO:
            rb = ttk.Radiobutton(radio_frame, text=motivo, variable=selected_reason, value=motivo, command=update_other_entry_state, style='Toolbutton')
            rb.pack(anchor='w', pady=2)

        def on_confirm():
            motivo_selecionado = selected_reason.get(); final_motivo = ""
            if not motivo_selecionado: messagebox.showwarning("Campo Vazio", "Por favor, selecione ou descreva um motivo.", parent=popup); return
            if motivo_selecionado == "OUTROS":
                motivo_digitado = self.entry_other_reason.get("1.0", "end-1c").strip()
                if not motivo_digitado:
                    messagebox.showwarning("Campo Vazio", "Por favor, descreva o motivo em 'Outros'.", parent=popup); return
                final_motivo = f"OUTROS: {motivo_digitado.upper()}"
            else: final_motivo = motivo_selecionado
            self.popup_motivo = final_motivo; popup.destroy()

        ttk.Button(container, text="Confirmar e Copiar", style="success.TButton", command=on_confirm).pack(pady=15, side='bottom')
        self.wait_window(popup)

    def copiar_texto_gerencia(self):
        global consultor_selecionado
        if 'total_a_pagar' not in calculo_resultado: messagebox.showerror("Erro", "Execute um cálculo válido primeiro."); return

        matricula = self.entry_matricula.get()
        nome_cliente = self.entry_nome_cliente.get()

        if not matricula or not nome_cliente: messagebox.showerror("Erro", "Preencha a Matrícula e o Nome do Cliente."); return
        self._ask_for_reason_popup()
        motivo = self.popup_motivo
        if not motivo: return
        data_acesso_str = calculo_resultado['data_acesso_final'].strftime('%d/%m/%Y')
        texto_formatado = (f"*CANCELAMENTO*\n\nMatrícula: {matricula}\nNome: {nome_cliente}\n\nMotivo: {motivo}\nAcesso até: {data_acesso_str}\n\n> {consultor_selecionado}")
        self.clipboard_clear(); self.clipboard_append(texto_formatado)
        self.show_toast("Texto Copiado!", "Mensagem para pendências copiada com sucesso.")

    def copiar_texto_cliente(self):
        if 'total_a_pagar' not in calculo_resultado: messagebox.showerror("Erro", "Execute um cálculo válido primeiro."); return

        matricula = self.entry_matricula.get()
        nome_cliente = self.entry_nome_cliente.get()

        if not matricula or not nome_cliente: messagebox.showerror("Erro", "Preencha a Matrícula e o Nome do Cliente."); return
        linha_proxima_parcela = ""
        if calculo_resultado['valor_proxima_parcela'] > 0: linha_proxima_parcela = (f"- Próxima parcela: R$ {calculo_resultado['valor_proxima_parcela']:.2f} (dia {calculo_resultado['vencimento_proxima']})\n")
        texto_formatado = (f"*INFORMAÇÕES CANCELAMENTO*\n\n- Nome: {nome_cliente}\n- Matricula: {matricula}\n\n*💸 VALORES*\n- Parcelas vencidas: R$ {calculo_resultado['valor_atrasado']:.2f} ({calculo_resultado['parcelas_atrasadas_qtd']} Parcelas)\n{linha_proxima_parcela}- Valor da multa: R$ {calculo_resultado['valor_multa']:.2f} (10% de {calculo_resultado['meses_para_multa']} Meses)\n> TOTAL A SER PAGO: *R$ {calculo_resultado['total_a_pagar']:.2f}*\n\nApós o cancelamento, *seu acesso permanecerá ativo até*: {calculo_resultado['data_acesso_final'].strftime('%d/%m/%Y')}")
        self.clipboard_clear(); self.clipboard_append(texto_formatado)
        self.show_toast("Texto Copiado!", "Detalhes do cancelamento copiados com sucesso.")

    def mostrar_janela_com_link(self, link):
        janela_link = Toplevel(self); janela_link.title("Link Gerado com Sucesso!")
        popup_width = 450; popup_height = 180
        self._center_popup(janela_link, popup_width, popup_height)
        container = ttk.Frame(janela_link, padding=20); container.pack(fill='both', expand=True)
        ttk.Label(container, text="Envie este link para o cliente:", font=("-weight bold")).pack(pady=(0, 10))
        entry_link = ttk.Entry(container, width=60); entry_link.insert(0, link)
        entry_link.pack(padx=10, pady=5); entry_link.config(state="readonly")
        def copiar_link_e_mensagem():

            nome_cliente = self.entry_nome_cliente.get().split(' ')[0]

            mensagem_completa = (f"Para prosseguir com o cancelamento da sua matrícula, "
                                 "Preciso que preencha as informações e assine "
                                 f"através deste link: {link}\n\n"
                                 "Por favor, me mande o PDF assim que finalizar, ok? 😉")
            self.clipboard_clear(); self.clipboard_append(mensagem_completa)
            self.show_toast("Mensagem Copiada!", "O link e a mensagem para o cliente foram copiados!")
            janela_link.destroy()
        ttk.Button(container, text="Copiar Mensagem e Link", command=copiar_link_e_mensagem, style='primary.TButton').pack(pady=10)
        self.wait_window(janela_link)

    def gerar_documento_popup(self):
        if 'total_a_pagar' not in calculo_resultado: messagebox.showerror("Erro", "Execute um cálculo válido primeiro."); return

        nome_cliente = self.entry_nome_cliente.get()
        matricula = self.entry_matricula.get()

        if not nome_cliente or not matricula: messagebox.showerror("Erro", "Preencha Nome e Matrícula para gerar o documento."); return
        popup = Toplevel(self); popup.title("Informação Adicional")
        popup_width = 450; popup_height = 200
        self._center_popup(popup, popup_width, popup_height)
        container = ttk.Frame(popup, padding=20); container.pack(fill='both', expand=True)
        ttk.Label(container, text="Digite o CPF do Cliente:", font=("-weight bold")).pack(pady=(0, 10))
        vcmd_cpf = (self.register(validar_e_formatar_cpf_input), '%P')
        entry_cpf_popup = ttk.Entry(container, width=30, validate="key", validatecommand=vcmd_cpf); entry_cpf_popup.pack(pady=5); entry_cpf_popup.focus_set()

        def on_paste_cpf(event):
            try:
                texto_colado = self.clipboard_get(); cpf_limpo = limpar_cpf(texto_colado)
                entry_cpf_popup.delete(0, 'end'); entry_cpf_popup.insert(0, cpf_limpo[:11])
            except: pass
            return "break"
        entry_cpf_popup.bind("<<Paste>>", on_paste_cpf)

        def finalizar_geracao():
            cpf_limpo = limpar_cpf(entry_cpf_popup.get())
            if not validar_cpf_algoritmo(cpf_limpo):
                messagebox.showerror("CPF Inválido", "O CPF digitado não é válido.", parent=popup); return
            dados_para_enviar = {"nome": nome_cliente.upper(), "cpf": cpf_limpo, "matricula": matricula, "valor_multa": f"{calculo_resultado['total_a_pagar']:.2f}", "data_inicio_contrato": calculo_resultado['data_inicio_contrato'].strftime('%d/%m/%Y'),"consultor": consultor_selecionado.upper()}
            popup.destroy()
            try:
                url_api = "https://assinagym.onrender.com/api/gerar-link"
                self.config(cursor="watch"); self.update_idletasks()
                response = requests.post(url_api, json=dados_para_enviar, timeout=20)
                self.config(cursor="")
                if response.status_code == 200:
                    self.mostrar_janela_com_link(response.json().get("link_assinatura"))
                else:
                    messagebox.showerror("Erro de Servidor", f"O servidor respondeu com um erro: {response.status_code}\n{response.text}")
            except requests.exceptions.RequestException as e:
                self.config(cursor=""); messagebox.showerror("Erro de Conexão", "Não foi possível conectar ao servidor. Verifique sua conexão e se o servidor AssinaGym está online.")
        ttk.Button(container, text="Confirmar e Gerar Link", command=finalizar_geracao, style='success.TButton').pack(pady=10)

    # --- VIEWS (Telas) ---

    def create_cancellation_view(self):
        """Cria a tela do Simulador de Cancelamento."""
        ttk.Label(self.main_frame, text="Simulador de Cancelamento", font=self.FONT_TITLE).pack(pady=(0, 10), anchor='w')

        frame_form = ttk.Frame(self.main_frame)
        frame_form.pack(padx=0, pady=5, fill="x", anchor='w')

        ttk.Label(frame_form, text="Data de Início (dd/mm/aaaa):", width=25, anchor='w').grid(row=0, column=0, sticky="w", pady=5)
        self.entry_data_inicio = ttk.Entry(frame_form, width=30)
        self.entry_data_inicio.grid(row=0, column=1, sticky="w", pady=5)
        self.entry_data_inicio.bind("<KeyRelease>", lambda e: formatar_data(e, self.entry_data_inicio))

        ttk.Label(frame_form, text="Tipo de Plano:", width=25, anchor='w').grid(row=1, column=0, sticky="w", pady=5)
        self.combo_plano = ttk.Combobox(frame_form, values=list(PLANOS.keys()), width=27, state="readonly")
        self.combo_plano.grid(row=1, column=1, sticky="w", pady=5); self.combo_plano.set('Anual (12 meses)')

        ttk.Label(frame_form, text="Mensalidades em Atraso:", width=25, anchor='w').grid(row=2, column=0, sticky="w", pady=5)
        self.entry_parcelas_atraso = ttk.Entry(frame_form, width=30)
        self.entry_parcelas_atraso.grid(row=2, column=1, sticky="w", pady=5)

        frame_botoes = ttk.Frame(frame_form)
        frame_botoes.grid(row=3, column=0, columnspan=2, sticky='w', pady=10)

        ttk.Button(frame_botoes, text="Calcular", command=self.do_calculation, style='success.TButton', width=20).pack(side="left", expand=False, padx=(0, 5), ipady=5)
        ttk.Button(frame_botoes, text="Nova Simulação", command=self.clear_fields, style='danger.TButton', width=20).pack(side="left", expand=False, padx=5, ipady=5)

        self.frame_resultado = ttk.Frame(self.main_frame, padding=(20, 15), relief="solid", borderwidth=1)
        self.frame_resultado.pack(pady=5, padx=10, fill="both", expand=True, anchor='w')

        self.placeholder_label = ttk.Label(self.frame_resultado, text="O resultado aparecerá aqui...", font=self.FONT_MAIN, style="secondary.TLabel")
        self.placeholder_label.pack(expand=True)

        self.frame_whatsapp = ttk.LabelFrame(self.frame_resultado, text=" Ações Finais ", padding=(15, 10))

        vcmd_matricula = (self.register(validar_matricula), '%P')
        ttk.Label(self.frame_whatsapp, text="Matrícula:").grid(row=0, column=1, sticky="w", pady=4)

        self.entry_matricula = ttk.Entry(self.frame_whatsapp, width=35, validate="key",
                                         validatecommand=vcmd_matricula)
        self.entry_matricula.grid(row=0, column=2, sticky="w", pady=4)

        ttk.Label(self.frame_whatsapp, text="Nome do Cliente:").grid(row=1, column=1, sticky="w", pady=4)
        self.entry_nome_cliente = ttk.Entry(self.frame_whatsapp, width=35)
        self.entry_nome_cliente.grid(row=1, column=2, sticky="w", pady=4)

        frame_botoes_copiar = ttk.Frame(self.frame_whatsapp)
        frame_botoes_copiar.grid(row=2, column=1, columnspan=2, pady=15)

        ttk.Button(frame_botoes_copiar, text="Copiar (Pendências)", style='success.Outline.TButton', command=self.copiar_texto_gerencia).pack(side="left", padx=5)
        ttk.Button(frame_botoes_copiar, text="Copiar Detalhes", style='info.Outline.TButton', command=self.copiar_texto_cliente).pack(side="right", padx=5)

        ttk.Button(self.frame_whatsapp, text="Gerar Link de Assinatura", style='danger.TButton', command=self.gerar_documento_popup).grid(row=3, column=1, columnspan=2, pady=(5,0), sticky='ew')

        self.frame_whatsapp.columnconfigure(0, weight=1); self.frame_whatsapp.columnconfigure(3, weight=1)

    def do_calculation(self):
        """Função de cálculo (agora um método da classe)."""

        data_inicio_str = self.entry_data_inicio.get()
        try:
            dia, mes, ano = map(int, data_inicio_str.split('/')); data_inicio = date(ano, mes, dia)
        except Exception:
            messagebox.showerror("Erro", "Formato de data inválido. Use dd/mm/aaaa."); return

        tipo_plano = self.combo_plano.get()
        parcelas_atrasadas_str = self.entry_parcelas_atraso.get() or "0"
        if not data_inicio_str or not tipo_plano: messagebox.showerror("Erro", "Preencha a Data de Início e o Tipo de Plano."); return

        data_simulacao_hoje = date.today()
        if data_inicio > data_simulacao_hoje: messagebox.showerror("Data Inválida", "A Data de Início do contrato não pode ser uma data no futuro."); return

        def processar_calculo(pagamento_hoje_status=None):
            global calculo_resultado
            calculo_resultado = logica_de_calculo(data_inicio, tipo_plano, parcelas_atrasadas_str, pagamento_hoje_status)

            for widget in self.frame_resultado.winfo_children():
                if widget != self.frame_whatsapp: widget.destroy()

            if 'erro_data' in calculo_resultado:
                messagebox.showerror("Data Inválida", calculo_resultado['erro_data'])
                ttk.Label(self.frame_resultado, text="O resultado aparecerá aqui...", font=self.FONT_MAIN, style="secondary.TLabel").pack(expand=True); self.frame_whatsapp.pack_forget(); return
            elif 'erro_geral' in calculo_resultado:
                messagebox.showerror("Erro", calculo_resultado['erro_geral'])
                ttk.Label(self.frame_resultado, text="O resultado aparecerá aqui...").pack(expand=True); self.frame_whatsapp.pack_forget(); return

            ttk.Label(self.frame_resultado, text=f"Data da Simulação: {calculo_resultado['data_simulacao'].strftime('%d/%m/%Y')}").pack(fill='x', anchor='w')
            ttk.Label(self.frame_resultado, text=f"Plano: {calculo_resultado['plano']} (R$ {calculo_resultado['valor_plano']:.2f})").pack(fill='x', anchor='w')
            ttk.Label(self.frame_resultado, text=f"Início do Contrato: {calculo_resultado['data_inicio_contrato'].strftime('%d/%m/%Y')}").pack(fill='x', anchor='w')
            ttk.Separator(self.frame_resultado).pack(fill='x', pady=5)
            ttk.Label(self.frame_resultado, text=f"Valor por parcelas em atraso ({calculo_resultado['parcelas_atrasadas_qtd']}x): R$ {calculo_resultado['valor_atrasado']:.2f}", font=self.FONT_BOLD).pack(fill='x', anchor='w')
            ttk.Label(self.frame_resultado, text=f"Mensalidade a vencer: {calculo_resultado['linha_mensalidade_a_vencer']}", font=self.FONT_BOLD).pack(fill='x', anchor='w')
            ttk.Label(self.frame_resultado, text=f"Multa contratual (10% sobre {calculo_resultado['meses_para_multa']} meses): R$ {calculo_resultado['valor_multa']:.2f}", font=self.FONT_BOLD).pack(fill='x', anchor='w')
            ttk.Separator(self.frame_resultado).pack(fill='x', pady=5)
            ttk.Label(self.frame_resultado, text=f"TOTAL A SER PAGO: R$ {calculo_resultado['total_a_pagar']:.2f}", font=self.FONT_BOLD).pack(fill='x', anchor='w')
            ttk.Separator(self.frame_resultado).pack(fill='x', pady=5)
            ttk.Label(self.frame_resultado, text=f"O acesso à academia será encerrado em: {calculo_resultado['data_acesso_final'].strftime('%d/%m/%Y')}").pack(fill='x', anchor='w')

            self.frame_whatsapp.pack(pady=20, padx=10, fill="x", side='bottom')

        if data_simulacao_hoje.day == data_inicio.day and data_simulacao_hoje >= data_inicio:
            resposta = messagebox.askyesno("Verificação de Pagamento", "A parcela de hoje já foi debitada do cartão do cliente?")
            processar_calculo(resposta)
        else:
            processar_calculo()

    def clear_fields(self):
        """Limpa os campos do simulador (agora um método da classe)."""
        global calculo_resultado
        self.entry_data_inicio.delete(0, 'end'); self.entry_parcelas_atraso.delete(0, 'end'); self.combo_plano.set('Anual (12 meses)')

        self.frame_whatsapp.pack_forget()
        for widget in self.frame_resultado.winfo_children():
            if widget != self.frame_whatsapp: widget.destroy()

        ttk.Label(self.frame_resultado, text="O resultado aparecerá aqui...", font=self.FONT_MAIN, style="secondary.TLabel").pack(expand=True)
        self.entry_data_inicio.focus_set()

        self.entry_matricula.delete(0, 'end')
        self.entry_nome_cliente.delete(0, 'end')

        calculo_resultado = {}

    # --- TELA: CALCULADORA COMISSÃO (REESCRITA) ---
    def create_comissao_view(self):
        """Cria a tela da Calculadora de Comissão (Nativa)."""
        ttk.Label(self.main_frame, text="Calculadora de Comissão", font=self.FONT_TITLE).pack(pady=(0, 10), anchor='w')

        # Frame de Cima: Upload
        frame_upload = ttk.Frame(self.main_frame)
        frame_upload.pack(side='top', fill='x', pady=(0, 10))

        btn_upload = ttk.Button(frame_upload, text="Fazer Upload do PDF de Fechamento",
                                command=self.processar_pdf_comissao,
                                style='primary.TButton',
                                width=40)
        btn_upload.pack(side='left', ipady=5, pady=5)

        self.lbl_pdf_selecionado = ttk.Label(frame_upload, text="Nenhum arquivo selecionado.", style='secondary.TLabel')
        self.lbl_pdf_selecionado.pack(side='left', padx=10)

        # Frame de Baixo: Resultados
        self.frame_resultado_comissao = ScrolledFrame(self.main_frame, autohide=True)
        self.frame_resultado_comissao.pack(side='top', fill='both', expand=True, pady=(10, 0))

        ttk.Label(self.frame_resultado_comissao.container,
                  text="Selecione um PDF para calcular a comissão.",
                  style='secondary.TLabel').pack(expand=True)

    def processar_pdf_comissao(self):
        """Função chamada pelo botão de upload."""
        filepath = filedialog.askopenfilename(
            title="Selecione o PDF de Fechamento de Caixa",
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if not filepath:
            return

        self.lbl_pdf_selecionado.config(text=os.path.basename(filepath))

        # Limpa resultados antigos
        for widget in self.frame_resultado_comissao.container.winfo_children():
            widget.destroy()

        # Mostra o cursor de "carregando"
        self.config(cursor="watch")
        self.update_idletasks()

        try:
            # Chama a lógica do calculadora_core.py
            resultados = processar_pdf(filepath)

            # Devolve o cursor ao normal
            self.config(cursor="")
            self.update_idletasks()

            # Exibe os resultados
            self.exibir_resultados_comissao(resultados)

        except Exception as e:
            # Devolve o cursor ao normal
            self.config(cursor="")
            self.update_idletasks()
            # Mostra o erro
            messagebox.showerror("Erro ao Processar PDF",
                                 f"Ocorreu um erro ao ler o arquivo:\n\n{e}\n\nTraceback:\n{traceback.format_exc()}")
            # Limpa o frame de resultados
            for widget in self.frame_resultado_comissao.container.winfo_children():
                widget.destroy()
            ttk.Label(self.frame_resultado_comissao.container,
                      text=f"Falha ao ler o PDF.\n{e}",
                      style='danger.TLabel').pack(expand=True)

    def _create_metric_widget(self, parent, label_text, value_text, bootstyle):
        """Função helper para criar um card de métrica."""
        frame = ttk.Frame(parent, bootstyle=bootstyle, padding=10, borderwidth=1, relief="raised")

        # Usar 'inverse' para o texto ficar com a cor oposta (ex: branco no azul)
        lbl_title = ttk.Label(frame, text=label_text,
                              font=(self.FONT_MAIN[0], 9, 'bold'),
                              bootstyle=f'inverse-{bootstyle}')
        lbl_title.pack(side='top', anchor='nw')

        lbl_value = ttk.Label(frame, text=value_text,
                              font=(self.FONT_MAIN[0], 16, 'bold'),
                              bootstyle=f'inverse-{bootstyle}')
        lbl_value.pack(side='bottom', anchor='se', pady=(5,0))
        return frame

    def exibir_resultados_comissao(self, resultados):
        """Pega o dicionário de resultados e exibe na tela."""

        container = self.frame_resultado_comissao.container

        # --- Seção 0: Info Cabeçalho ---
        info_cabecalho = resultados.get("info_cabecalho", {})
        operador = info_cabecalho.get("operador", "Não identificado")
        periodo = info_cabecalho.get("periodo", "Não identificado")

        frame_info = ttk.Frame(container, bootstyle='info', padding=10)
        frame_info.pack(fill='x', pady=5)
        ttk.Label(frame_info, text=f"Fechamento: {operador}    |    Período: {periodo}",
                  font=self.FONT_BOLD, bootstyle='inverse-info').pack()

        # --- Seção 1: Resumo do Cálculo ---
        frame_resumo = ttk.LabelFrame(container, text=" Resumo do Cálculo de Comissão ", padding=15)
        frame_resumo.pack(fill='x', pady=10)

        # Criar 4 colunas para os Metrics
        frame_metrics = ttk.Frame(frame_resumo)
        frame_metrics.pack(fill='x')
        frame_metrics.grid_columnconfigure((0,1,2,3), weight=1)

        # Substituído o 'Metric' inexistente pela nossa função helper
        m1 = self._create_metric_widget(frame_metrics, "Valor Total",
                                        formatar_reais(resultados.get('valor_total_bruto', 0)),
                                        'secondary')
        m1.grid(row=0, column=0, padx=5, sticky='ew')

        m2 = self._create_metric_widget(frame_metrics, "Descontos",
                                        formatar_reais(resultados.get('total_deducoes', 0)),
                                        'warning')
        m2.grid(row=0, column=1, padx=5, sticky='ew')

        m3 = self._create_metric_widget(frame_metrics, "Valor Comissionável",
                                        formatar_reais(resultados.get('base_comissionavel', 0)),
                                        'primary')
        m3.grid(row=0, column=2, padx=5, sticky='ew')

        m4 = self._create_metric_widget(frame_metrics, "SUA COMISSÃO (3%)",
                                        formatar_reais(resultados.get('comissao_final', 0)),
                                        'success')
        m4.grid(row=0, column=3, padx=5, sticky='ew')

        # --- Seção 2: Resumo de Vendas ---
        frame_vendas = ttk.LabelFrame(container, text=" Resumo de Vendas e Atendimentos ", padding=15)
        frame_vendas.pack(fill='x', expand=True, pady=10)

        resumo = resultados.get("resumo_vendas", {})
        total_atendimentos = resumo.get("total_atendimentos", 0)

        ttk.Label(frame_vendas, text=f"Total de Atendimentos: {total_atendimentos} transações").pack(anchor='w')
        ttk.Separator(frame_vendas).pack(fill='x', pady=10)

        cols = ('metodo', 'qtd', 'valor')
        tree_vendas = ttk.Treeview(frame_vendas, columns=cols, show='headings', height=7)
        tree_vendas.heading('metodo', text='Forma de Pagamento')
        tree_vendas.heading('qtd', text='Qtd.')
        tree_vendas.heading('valor', text='Valor Total')
        tree_vendas.column('metodo', anchor='w', width=250)
        tree_vendas.column('qtd', anchor='center', width=50)
        tree_vendas.column('valor', anchor='e', width=120)

        for metodo, dados in resumo.items():
            if isinstance(dados, dict) and dados.get('qtd', 0) > 0:
                nome_metodo = metodo.replace("_", " ").title().replace('(Ccc)', '(CCC)')
                tree_vendas.insert('', 'end', values=(nome_metodo, dados.get('qtd'), formatar_reais(dados.get('valor'))))
        tree_vendas.pack(fill='x', expand=True)

        # --- Seção 3: Detalhes das Deduções ---
        frame_deducoes = ttk.LabelFrame(container, text=" Detalhamento das Deduções Encontradas ", padding=15)
        frame_deducoes.pack(fill='x', expand=True, pady=10)

        detalhes = resultados.get('detalhes', {})
        deducoes_encontradas = {k: v for k, v in detalhes.items() if v > 0}

        if not deducoes_encontradas:
            ttk.Label(frame_deducoes, text="Nenhuma dedução aplicável foi encontrada.").pack()
        else:
            cols_deduc = ('motivo', 'valor')
            tree_deduc = ttk.Treeview(frame_deducoes, columns=cols_deduc, show='headings', height=len(deducoes_encontradas))
            tree_deduc.heading('motivo', text='Motivo da Dedução')
            tree_deduc.heading('valor', text='Valor Deduzido')
            tree_deduc.column('motivo', anchor='w', width=300)
            tree_deduc.column('valor', anchor='e', width=120)

            for nome, valor in deducoes_encontradas.items():
                tree_deduc.insert('', 'end', values=(nome, formatar_reais(valor)))
            tree_deduc.pack(fill='x', expand=True)

    # --- TELA: FOLGAS (REESCRITA PARA USAR JSON) ---

    def get_folgas_por_data(self, data_obj):
        """Função HElPER. Retorna uma lista de nomes em folga para uma data específica."""
        folgas_lista = []
        # Itera no dicionário de folgas
        for consultor_nome, lista_de_datas in self.dados_folgas.items():
            # Tenta encontrar a data na lista daquele consultor
            for data_str in lista_de_datas:
                try:
                    # Converte a string da data (ex: "01/11/2025") em um objeto date
                    data_folga = datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
                    if data_folga == data_obj:
                        # CORREÇÃO 1: Usar .upper() para MAIÚSCULAS
                        folgas_lista.append(consultor_nome.upper())
                        break # Para de procurar nas datas desta pessoa
                except ValueError:
                    # Ignora datas mal formatadas no JSON
                    print(f"Aviso: Data mal formatada '{data_str}' para {consultor_nome}")
                    pass
        return folgas_lista

    def create_folgas_view(self):
        """Cria a tela de Folgas (lendo do folgas.json)."""
        # *** CORREÇÃO DE LAYOUT: Configurar o grid do self.main_frame ***
        self.main_frame.grid_rowconfigure(1, weight=1) # Faz a linha 1 (resultados) expandir
        self.main_frame.grid_columnconfigure(0, weight=1) # Faz a coluna 0 expandir

        ttk.Label(self.main_frame, text="Controle de Folgas", font=self.FONT_TITLE).grid(row=0, column=0, pady=(0, 10), sticky='w')

        # --- Frame de Cima: Consultas ---
        frame_consulta = ttk.Frame(self.main_frame, padding=10)
        # *** CORREÇÃO DE LAYOUT: MUDADO PARA GRID ***
        frame_consulta.grid(row=0, column=0, sticky='new')

        # 1. Carregar os dados
        self.dados_folgas = carregar_folgas()
        if not self.dados_folgas:
            msg = "Nenhum dado de folga cadastrado.\n\nVá para a Área do Desenvolvedor para adicionar as folgas."
            # Coloca a mensagem no frame de consulta mesmo
            ttk.Label(frame_consulta, text=msg, style='secondary.TLabel', font=self.FONT_MAIN).pack(expand=True)
            # Esconde o frame de resultado que não será criado
            self.frame_resultado_folgas = ttk.Frame(self.main_frame) # Cria um frame vazio
            self.frame_resultado_folgas.grid(row=1, column=0, sticky='nsew')
            return

        hoje_obj = date.today()
        hoje_formatado = hoje_obj.strftime("%d/%m/%Y")

        # 2. Folgas de Hoje
        frame_hoje = ttk.LabelFrame(frame_consulta, text=" Folgas de Hoje ", padding=(15, 10))
        frame_hoje.pack(fill='x', expand=True, side='top', pady=(0, 5))

        folgas_hoje_lista = self.get_folgas_por_data(hoje_obj)
        folgas_hoje_str = ", ".join(folgas_hoje_lista) if folgas_hoje_lista else "Ninguém de folga hoje."

        ttk.Label(frame_hoje, text=f"Data: {hoje_formatado}", font=self.FONT_BOLD).pack(anchor='w')
        ttk.Label(frame_hoje, text=f"Consultores: {folgas_hoje_str}", font=self.FONT_MAIN).pack(anchor='w', pady=(5,0))

        # 3. NOVO: Folgas de Amanhã (Recurso 7)
        frame_amanha = ttk.LabelFrame(frame_consulta, text=" Folgas de Amanhã ", padding=(15, 10))
        frame_amanha.pack(fill='x', expand=True, side='top', pady=5)

        amanha_obj = hoje_obj + relativedelta(days=1)
        amanha_formatado = amanha_obj.strftime("%d/%m/%Y")
        folgas_amanha_lista = self.get_folgas_por_data(amanha_obj)
        folgas_amanha_str = ", ".join(folgas_amanha_lista) if folgas_amanha_lista else "Ninguém de folga amanhã."

        ttk.Label(frame_amanha, text=f"Data: {amanha_formatado}", font=self.FONT_BOLD).pack(anchor='w')
        ttk.Label(frame_amanha, text=f"Consultores: {folgas_amanha_str}", font=self.FONT_MAIN).pack(anchor='w', pady=(5,0))

        # 4. Consultar por Consultor
        frame_buscar = ttk.LabelFrame(frame_consulta, text=" Consultar por Consultor ", padding=(15, 10))
        frame_buscar.pack(fill='x', expand=True, pady=5, side='top')

        ttk.Label(frame_buscar, text="Selecione o Consultor:").pack(anchor='w', side='left', padx=(0, 10))

        nomes_com_folga = sorted(list(self.dados_folgas.keys()))

        self.combo_consultor_folga = ttk.Combobox(frame_buscar, values=nomes_com_folga, state="readonly", width=30)
        self.combo_consultor_folga.pack(side='left', padx=10)

        btn_consultar = ttk.Button(frame_buscar, text="Consultar", command=self.mostrar_folgas_consultor, style='primary.TButton')
        btn_consultar.pack(side='left', padx=10)

        # NOVO: Botão Limpar (Recurso 4)
        btn_limpar = ttk.Button(frame_buscar, text="Limpar", command=self.limpar_consulta_folgas, style='secondary.Outline.TButton')
        btn_limpar.pack(side='left', padx=10)

        btn_ver_tabela = ttk.Button(frame_buscar, text="Ver Tabela Completa", command=self.mostrar_tabela_completa_folgas, style='info.Outline.TButton')
        btn_ver_tabela.pack(side='right', padx=10)

        # 5. NOVO: Consultar por Data (Recurso 5)
        frame_buscar_data = ttk.LabelFrame(frame_consulta, text=" Consultar por Data ", padding=(15, 10))
        frame_buscar_data.pack(fill='x', expand=True, pady=5, side='top')

        ttk.Label(frame_buscar_data, text="Digite a Data (dd/mm/aaaa):").pack(anchor='w', side='left', padx=(0, 10))

        self.entry_data_folga = ttk.Entry(frame_buscar_data, width=20)
        self.entry_data_folga.pack(side='left', padx=10)
        self.entry_data_folga.bind("<KeyRelease>", lambda e: formatar_data(e, self.entry_data_folga))
        # NOVO: Data Padrão (Recurso 6)
        self.entry_data_folga.insert(0, hoje_formatado)

        btn_consultar_data = ttk.Button(frame_buscar_data, text="Consultar Data", command=self.mostrar_folgas_por_data, style='primary.TButton')
        btn_consultar_data.pack(side='left', padx=10)

        # --- Parte de Baixo: Resultado ---
        self.frame_resultado_folgas = ScrolledFrame(self.main_frame, padding=10, autohide=True)
        # *** CORREÇÃO DE LAYOUT: MUDADO PARA GRID ***
        self.frame_resultado_folgas.grid(row=1, column=0, sticky='nsew', pady=(10, 0))

        ttk.Label(self.frame_resultado_folgas.container, text="Selecione um consultor ou data para consultar.").pack()

    def limpar_consulta_folgas(self):
        """Limpa os campos de consulta e o frame de resultado."""
        self.combo_consultor_folga.set("")
        self.entry_data_folga.delete(0, END)
        self.entry_data_folga.insert(0, date.today().strftime("%d/%m/%Y"))

        # Limpa o frame de resultado
        for widget in self.frame_resultado_folgas.container.winfo_children():
            widget.destroy()
        ttk.Label(self.frame_resultado_folgas.container, text="Selecione um consultor ou data para consultar.").pack()

    def mostrar_folgas_consultor(self):
        """Mostra a lista de folgas do consultor selecionado."""
        for widget in self.frame_resultado_folgas.container.winfo_children():
            widget.destroy()

        nome_consultor = self.combo_consultor_folga.get()
        if not nome_consultor:
            messagebox.showwarning("Atenção", "Selecione um consultor para consultar.")
            return

        datas_folga = self.dados_folgas.get(nome_consultor, [])

        container = self.frame_resultado_folgas.container
        # CORREÇÃO 1: Usar .upper()
        ttk.Label(container, text=f"Folgas Cadastradas - {nome_consultor.upper()}:", font=self.FONT_BOLD).pack(anchor='w', pady=(0, 10))

        if not datas_folga:
            ttk.Label(container, text="Nenhuma folga cadastrada para este consultor.").pack(anchor='w')
            return

        try:
            datas_folga_sorted = sorted(datas_folga, key=lambda d: datetime.strptime(d.strip(), "%d/%m/%Y"))
        except ValueError:
            datas_folga_sorted = datas_folga

        for dia in datas_folga_sorted:
            ttk.Label(container, text=f"• {dia}").pack(anchor='w')

    def mostrar_folgas_por_data(self):
        """Mostra a lista de consultores em folga na data selecionada."""
        for widget in self.frame_resultado_folgas.container.winfo_children():
            widget.destroy()

        data_str = self.entry_data_folga.get()
        if not data_str or len(data_str) != 10:
            messagebox.showwarning("Data Inválida", "Digite uma data válida (dd/mm/aaaa).")
            return

        try:
            data_obj = datetime.strptime(data_str, "%d/%m/%Y").date()
        except ValueError:
            messagebox.showwarning("Data Inválida", "A data digitada não é válida (dd/mm/aaaa).")
            return

        folgas_lista = self.get_folgas_por_data(data_obj)

        container = self.frame_resultado_folgas.container
        ttk.Label(container, text=f"Consultores em Folga - {data_str}:", font=self.FONT_BOLD).pack(anchor='w', pady=(0, 10))

        if not folgas_lista:
            ttk.Label(container, text="Ninguém cadastrado para folga nesta data.").pack(anchor='w')
            return

        for nome in folgas_lista:
            # .upper() já foi aplicado em get_folgas_por_data
            ttk.Label(container, text=f"• {nome}").pack(anchor='w')

    def mostrar_tabela_completa_folgas(self):
        """Mostra a tabela completa de folgas do JSON."""
        for widget in self.frame_resultado_folgas.container.winfo_children():
            widget.destroy()

        container = self.frame_resultado_folgas.container

        colunas = ('consultor', 'datas')
        tree_folgas = ttk.Treeview(container, columns=colunas, show='headings', height=15)

        tree_folgas.heading('consultor', text='Consultor')
        tree_folgas.heading('datas', text='Datas de Folga')

        tree_folgas.column('consultor', width=200, anchor='w', stretch=False)
        tree_folgas.column('datas', width=500, anchor='w')

        # Preencher Dados
        for nome, lista_de_datas in sorted(self.dados_folgas.items()):
            try:
                datas_folga_sorted = sorted(lista_de_datas, key=lambda d: datetime.strptime(d.strip(), "%d/%m/%Y"))
            except ValueError:
                datas_folga_sorted = lista_de_datas

            datas_str = ", ".join(datas_folga_sorted)
            # CORREÇÃO 1: Usar .upper()
            tree_folgas.insert('', 'end', values=(nome.upper(), datas_str))

        tree_folgas.pack(fill='both', expand=True)

    # --- ÁREA DO DESENVOLVEDOR ---
    def show_developer_login(self):
        """Mostra um popup para o login na área do desenvolvedor.
           Retorna True se o login for bem-sucedido, False caso contrário."""

        self.pin_success = False

        popup = Toplevel(self)
        popup.title("Área do Desenvolvedor - Login")
        popup_width = 350
        popup_height = 180
        self._center_popup(popup, popup_width, popup_height)

        container = ttk.Frame(popup, padding=20)
        container.pack(fill='both', expand=True)

        ttk.Label(container, text="Digite o PIN para acessar a Área do Desenvolvedor:", font=self.FONT_MAIN).pack(pady=(0, 10))

        pin_entry_var = StringVar()
        pin_entry = ttk.Entry(container, width=20, show="*", textvariable=pin_entry_var)
        pin_entry.pack(pady=5)
        pin_entry.focus_set()

        def verify_pin():
            if pin_entry_var.get() == "8274":
                self.pin_success = True
                popup.destroy()
            else:
                messagebox.showerror("PIN Inválido", "PIN incorreto. Acesso negado.", parent=popup)
                pin_entry_var.set("")
                pin_entry.focus_set()

        ttk.Button(container, text="Acessar", command=verify_pin, style='success.TButton').pack(pady=10)
        popup.bind("<Return>", lambda event: verify_pin())
        self.wait_window(popup)

        return self.pin_success

    def create_developer_area_view(self):
        """Cria a tela da Área do Desenvolvedor com funcionalidade."""
        ttk.Label(self.main_frame, text="Área do Desenvolvedor", font=self.FONT_TITLE).pack(pady=(0, 10), anchor='w')

        pw = Panedwindow(self.main_frame, orient='horizontal')
        pw.pack(fill='both', expand=True)

        # --- Lado Esquerdo: Lista de Consultores ---
        frame_lista = ttk.Frame(pw, padding=10)
        pw.add(frame_lista, weight=1)

        ttk.Label(frame_lista, text="Consultores", font=self.FONT_BOLD).pack(anchor='w')

        cols = ('nome', 'foto_path')
        self.dev_tree = ttk.Treeview(frame_lista, columns=cols, show='headings', height=15, selectmode='browse')
        self.dev_tree.heading('nome', text='Nome do Consultor')
        self.dev_tree.heading('foto_path', text='Caminho da Foto')
        self.dev_tree.column('nome', width=200)
        self.dev_tree.column('foto_path', width=150)
        self.dev_tree.pack(fill='both', expand=True, pady=10)

        self.dev_tree.bind('<<TreeviewSelect>>', self.on_dev_tree_select)

        frame_lista_botoes = ttk.Frame(frame_lista)
        frame_lista_botoes.pack(fill='x', pady=5)
        ttk.Button(frame_lista_botoes, text="Adicionar Novo", style="success.TButton", command=self.dev_adicionar_novo).pack(side='left', padx=5)
        ttk.Button(frame_lista_botoes, text="Excluir Selecionado", style="danger.Outline.TButton", command=self.dev_excluir_selecionado).pack(side='left', padx=5)

        # --- Lado Direito: Formulário de Edição ---
        frame_form = ttk.Frame(pw, padding=10)
        pw.add(frame_form, weight=2)

        ttk.Label(frame_form, text="Editar Consultor", font=self.FONT_BOLD).pack(anchor='w')

        ttk.Label(frame_form, text="Foto de Perfil:").pack(anchor='w', pady=(10, 2))
        self.dev_foto_label = ttk.Label(frame_form, image=self.default_profile_photo)
        self.dev_foto_label.pack(anchor='w', pady=5)
        ttk.Button(frame_form, text="Fazer Upload de Nova Foto...", command=self.dev_fazer_upload).pack(anchor='w', pady=5)

        ttk.Label(frame_form, text="Nome:").pack(anchor='w', pady=(10, 2))
        self.dev_nome_var = StringVar()
        self.dev_nome_entry = ttk.Entry(frame_form, width=50, font=self.FONT_MAIN, textvariable=self.dev_nome_var)
        self.dev_nome_entry.pack(anchor='w', fill='x', pady=5)

        ttk.Label(frame_form, text="Caminho do Arquivo da Foto:").pack(anchor='w', pady=(10, 2))
        self.dev_foto_path_var = StringVar()
        self.dev_foto_path_entry = ttk.Entry(frame_form, width=50, font=self.FONT_MAIN, textvariable=self.dev_foto_path_var, state='readonly')
        self.dev_foto_path_entry.pack(anchor='w', fill='x', pady=5)

        ttk.Button(frame_form, text="Salvar Alterações", style="primary.TButton", command=self.dev_salvar_alteracoes).pack(anchor='w', pady=20)

        self.dev_folgas_button = ttk.Button(frame_form, text="Ajustar Folgas",
                                            command=self.show_folgas_popup,
                                            style="info.TButton",
                                            state='disabled')
        self.dev_folgas_button.pack(anchor='w', pady=5, ipady=4)

        self.populate_consultor_tree()

    def populate_consultor_tree(self):
        """Limpa e preenche a Treeview com os dados atuais."""
        for item in self.dev_tree.get_children():
            self.dev_tree.delete(item)

        for consultor in self.lista_completa_consultores:
            self.dev_tree.insert('', 'end', values=(consultor['nome'], consultor['foto_path']))

        self.dev_nome_var.set("")
        self.dev_foto_path_var.set("")
        self.load_profile_picture("", size=PROFILE_PIC_SIZE, is_dev_preview=True)
        # Desabilita o botão de folgas
        if hasattr(self, 'dev_folgas_button'):
            self.dev_folgas_button.config(state='disabled')

    # --- Funções da Área do Desenvolvedor ---

    def on_dev_tree_select(self, event=None):
        """Chamado quando um item é selecionado na Treeview."""
        selected_iid = self.dev_tree.focus()
        if not selected_iid:
            self.dev_folgas_button.config(state='disabled') # Desabilita se nada for selecionado
            return

        values = self.dev_tree.item(selected_iid, 'values')
        nome, foto_path = values[0], values[1]

        self.dev_nome_var.set(nome)
        self.dev_foto_path_var.set(foto_path)
        self.load_profile_picture(foto_path, size=PROFILE_PIC_SIZE, is_dev_preview=True)
        self.dev_folgas_button.config(state='normal') # Habilita o botão de folgas

    def dev_fazer_upload(self):
        """Abre a janela de diálogo para o upload de uma nova foto."""
        filepath = filedialog.askopenfilename(
            title="Selecionar foto",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp"), ("Todos os arquivos", "*.*")]
        )
        if not filepath:
            return

        filename = os.path.basename(filepath)
        dest_path = os.path.join(DATA_FOLDER_PATH, filename)

        try:
            shutil.copy(filepath, dest_path)
            self.dev_foto_path_var.set(filename)
            self.load_profile_picture(filename, size=PROFILE_PIC_SIZE, is_dev_preview=True)
            self.show_toast("Upload Concluído", f"Arquivo {filename} salvo em 'data'.")

        except Exception as e:
            messagebox.showerror("Erro no Upload", f"Não foi possível copiar o arquivo: {e}")

    def dev_salvar_alteracoes(self):
        """Salva as mudanças feitas no formulário no consultor selecionado."""
        selected_iid = self.dev_tree.focus()
        if not selected_iid:
            messagebox.showwarning("Nenhum Consultor", "Selecione um consultor na lista para salvar.")
            return

        original_nome = self.dev_tree.item(selected_iid, 'values')[0]

        novo_nome = self.dev_nome_var.get()
        nova_foto = self.dev_foto_path_var.get()

        if not novo_nome:
            messagebox.showwarning("Campo Vazio", "O nome do consultor não pode estar vazio.")
            return

        # Atualiza a lista de dados
        for consultor in self.lista_completa_consultores:
            if consultor['nome'] == original_nome:
                consultor['nome'] = novo_nome
                consultor['foto_path'] = nova_foto
                break

        # Salva no JSON e atualiza a UI
        if salvar_consultores(self.lista_completa_consultores):
            # Recarrega a lista de nomes principal (para o login)
            self.nomes_consultores = [c['nome'] for c in self.lista_completa_consultores]
            self.combo_consultor_login.config(values=self.nomes_consultores)

            self.populate_consultor_tree()
            self.show_toast("Sucesso!", "Consultor atualizado.")

            # ATUALIZA O JSON DE FOLGAS (se o nome mudou)
            self.dados_folgas = carregar_folgas()
            if original_nome in self.dados_folgas and original_nome != novo_nome:
                if messagebox.askyesno("Atualizar Folgas", f"Você renomeou '{original_nome}' para '{novo_nome}'.\n\nDeseja transferir os dados de folgas para o novo nome?"):
                    self.dados_folgas[novo_nome] = self.dados_folgas.pop(original_nome)
                    salvar_folgas(self.dados_folgas)
                    self.show_toast("Sucesso!", "Folgas transferidas para o novo nome.")


    def dev_adicionar_novo(self):
        """Adiciona um novo consultor à lista."""
        novo_nome = "NOVO CONSULTOR"
        nova_foto = "default_profile.png"

        if any(c['nome'] == novo_nome for c in self.lista_completa_consultores):
            messagebox.showwarning("Erro", "Já existe um 'NOVO CONSULTOR'. Renomeie-o antes de adicionar outro.")
            return

        self.lista_completa_consultores.append({"nome": novo_nome, "foto_path": nova_foto})

        if salvar_consultores(self.lista_completa_consultores):
            # Recarrega a lista de nomes principal (para o login)
            self.nomes_consultores = [c['nome'] for c in self.lista_completa_consultores]
            self.combo_consultor_login.config(values=self.nomes_consultores)

            self.populate_consultor_tree()
            try:
                last_item = self.dev_tree.get_children()[-1]
                self.dev_tree.selection_set(last_item)
                self.dev_tree.focus(last_item)
            except:
                pass
            self.show_toast("Adicionado", "Novo consultor criado. Edite-o e salve.")

    def dev_excluir_selecionado(self):
        """Exclui o consultor selecionado da lista."""
        selected_iid = self.dev_tree.focus()
        if not selected_iid:
            messagebox.showwarning("Nenhum Consultor", "Selecione um consultor na lista para excluir.")
            return

        original_nome = self.dev_tree.item(selected_iid, 'values')[0]

        if not messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir o consultor:\n\n{original_nome}\n\nEsta ação não pode ser desfeita."):
            return

        self.lista_completa_consultores = [c for c in self.lista_completa_consultores if c['nome'] != original_nome]

        if salvar_consultores(self.lista_completa_consultores):
            # Recarrega a lista de nomes principal (para o login)
            self.nomes_consultores = [c['nome'] for c in self.lista_completa_consultores]
            self.combo_consultor_login.config(values=self.nomes_consultores)

            self.populate_consultor_tree()
            self.show_toast("Excluído", f"{original_nome} foi removido.")

            # Remove as folgas do JSON
            self.dados_folgas = carregar_folgas()
            if original_nome in self.dados_folgas:
                if messagebox.askyesno("Remover Folgas", f"Deseja também remover as folgas cadastradas para '{original_nome}'?"):
                    self.dados_folgas.pop(original_nome)
                    salvar_folgas(self.dados_folgas)
                    self.show_toast("Sucesso!", "Folgas removidas.")

    # --- POPUP DE GERENCIAR FOLGAS ---
    def show_folgas_popup(self):
        """Mostra um popup para gerenciar a lista de folgas de um consultor."""

        selected_iid = self.dev_tree.focus()
        if not selected_iid:
            return # Segurança, embora o botão deva estar desabilitado

        consultor_nome = self.dev_tree.item(selected_iid, 'values')[0]

        # Carrega os dados mais recentes
        self.dados_folgas = carregar_folgas()
        # Pega a lista de datas para este consultor (ou uma lista vazia)
        lista_de_datas = self.dados_folgas.get(consultor_nome, [])

        # --- Cria o Popup ---
        popup = Toplevel(self)
        popup.title(f"Ajustar Folgas: {consultor_nome}")
        self._center_popup(popup, 500, 400) # (popup, largura, altura)

        container = ttk.Frame(popup, padding=15)
        container.pack(fill='both', expand=True)
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # --- Frame de Adicionar Data ---
        frame_add = ttk.Frame(container)
        frame_add.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))

        ttk.Label(frame_add, text="Nova Data (dd/mm/aaaa):").pack(side='left')

        entry_data = ttk.Entry(frame_add, width=15)
        entry_data.pack(side='left', padx=10)
        entry_data.bind("<KeyRelease>", lambda e: formatar_data(e, entry_data))

        def on_add_data():
            data_str = entry_data.get()
            if len(data_str) != 10:
                messagebox.showwarning("Data Inválida", "Digite a data completa (dd/mm/aaaa).", parent=popup)
                return
            try:
                # Valida a data
                datetime.strptime(data_str, "%d/%m/%Y")
            except ValueError:
                messagebox.showwarning("Data Inválida", "A data digitada não é válida.", parent=popup)
                return

            if data_str in listbox_folgas.get(0, END):
                messagebox.showwarning("Data Duplicada", "Esta data já está na lista.", parent=popup)
                return

            listbox_folgas.insert(END, data_str)
            entry_data.delete(0, END)

        btn_add = ttk.Button(frame_add, text="Adicionar", style="success.Outline.TButton", command=on_add_data)
        btn_add.pack(side='left')

        # --- Lista de Datas ---
        listbox_folgas = Listbox(container, height=10, font=self.FONT_MAIN, width=30)
        listbox_folgas.grid(row=1, column=0, sticky='nsew', pady=5)

        # Scrollbar para a Listbox
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=listbox_folgas.yview)
        scrollbar.grid(row=1, column=1, sticky='ns', pady=5)
        listbox_folgas.config(yscrollcommand=scrollbar.set)

        # Preenche a lista com as datas salvas
        try:
            datas_ordenadas = sorted(lista_de_datas, key=lambda d: datetime.strptime(d.strip(), "%d/%m/%Y"))
        except ValueError:
            datas_ordenadas = lista_de_datas # Se houver erro de formatação, não ordena

        for data in datas_ordenadas:
            listbox_folgas.insert(END, data)

        # --- Botões de Ação ---
        frame_botoes = ttk.Frame(container)
        frame_botoes.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(10, 0))

        def on_remove_data():
            try:
                listbox_folgas.delete(ANCHOR) # Deleta o item selecionado
            except Exception as e:
                print(f"Erro ao remover: {e}")

        btn_remove = ttk.Button(frame_botoes, text="Remover Data Selecionada",
                                style="danger.Outline.TButton", command=on_remove_data)
        btn_remove.pack(side='left')

        def on_save_folgas():
            # Pega todas as datas da listbox
            nova_lista_de_datas = list(listbox_folgas.get(0, END))
            # Atualiza o dicionário principal
            self.dados_folgas[consultor_nome] = nova_lista_de_datas
            # Salva no arquivo JSON
            if salvar_folgas(self.dados_folgas):
                self.show_toast("Sucesso!", f"Folgas de {consultor_nome} salvas.")
                popup.destroy()
            else:
                messagebox.showerror("Erro", "Não foi possível salvar as folgas.", parent=popup)

        btn_save = ttk.Button(frame_botoes, text="Salvar e Fechar",
                                style="success.TButton", command=on_save_folgas)
        btn_save.pack(side='right')

    # --- TELA: LOCUTOR (TOTALMENTE MODIFICADA) ---
    def create_locutor_view(self):
        ttk.Label(self.main_frame, text="Locutor da Academia", font=self.FONT_TITLE).pack(pady=(0, 10), anchor='w')

        # Cria um painel dividido verticalmente
        pw_locutor = Panedwindow(self.main_frame, orient='vertical')
        pw_locutor.pack(fill='both', expand=True)

        # --- PAINEL DE CIMA: Mensagens Padrão ---
        frame_padrao = ttk.LabelFrame(pw_locutor, text=" Mensagens Padrão (Gerenciável) ", padding=15)
        pw_locutor.add(frame_padrao, weight=1) # Damos peso 1

        frame_padrao.grid_rowconfigure(0, weight=1)
        frame_padrao.grid_columnconfigure(0, weight=1)

        # Lista (Treeview) de mensagens
        cols = ('titulo')
        self.locutor_tree = ttk.Treeview(frame_padrao, columns=cols, show='headings', height=5, selectmode='browse')
        self.locutor_tree.heading('titulo', text='Título da Mensagem')
        self.locutor_tree.column('titulo', width=400)
        self.locutor_tree.grid(row=0, column=0, columnspan=4, sticky='nsew', pady=(0, 10))
        
        # Botões de Ação
        btn_falar_selecionado = ttk.Button(frame_padrao, text="Falar Selecionado",
                                          command=self.falar_mensagem_selecionada, 
                                          style='primary.TButton')
        btn_falar_selecionado.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
        
        btn_adicionar = ttk.Button(frame_padrao, text="Adicionar", 
                                   command=self.adicionar_mensagem, 
                                   style='success.Outline.TButton')
        btn_adicionar.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        btn_editar = ttk.Button(frame_padrao, text="Editar", 
                                command=self.editar_mensagem_selecionada, 
                                style='info.Outline.TButton')
        btn_editar.grid(row=1, column=2, padx=5, pady=5, sticky='ew')

        btn_excluir = ttk.Button(frame_padrao, text="Excluir", 
                                 command=self.excluir_mensagem_selecionada, 
                                 style='danger.Outline.TButton')
        btn_excluir.grid(row=1, column=3, padx=5, pady=5, sticky='ew')
        
        # Faz os botões expandirem igualmente
        frame_padrao.grid_columnconfigure(0, weight=2) # Botão de falar é maior
        frame_padrao.grid_columnconfigure(1, weight=1)
        frame_padrao.grid_columnconfigure(2, weight=1)
        frame_padrao.grid_columnconfigure(3, weight=1)


        # --- PAINEL DE BAIXO: Mensagem Personalizada ---
        frame_custom = ttk.LabelFrame(pw_locutor, text=" Mensagem Personalizada ", padding=15)
        pw_locutor.add(frame_custom, weight=1) # Damos peso 1
        
        frame_custom.grid_rowconfigure(0, weight=1)
        frame_custom.grid_columnconfigure(0, weight=1)

        # Usamos ScrolledText para mensagens longas
        self.entry_locutor = scrolledtext.ScrolledText(frame_custom, font=self.FONT_MAIN, height=3, width=80)
        self.entry_locutor.grid(row=0, column=0, sticky='nsew', pady=(5, 10))

        btn_falar = ttk.Button(frame_custom, text="FALAR MENSAGEM PERSONALIZADA", 
                               style="success.TButton", 
                               command=lambda: self.falar_no_microfone(self.entry_locutor.get("1.0", "end-1c")))
        btn_falar.grid(row=1, column=0, sticky='ew', ipady=10)

        # --- Preenche a lista de mensagens padrão ---
        self.populate_locutor_tree()


    # --- MÉTODOS DO LOCUTOR (NOVOS E MODIFICADOS) ---

    def populate_locutor_tree(self):
        """Limpa e preenche a Treeview com as mensagens do locutor."""
        if not hasattr(self, 'locutor_tree'):
            return # A tela do locutor ainda não foi criada
            
        for item in self.locutor_tree.get_children():
            self.locutor_tree.delete(item)
            
        for mensagem in self.lista_mensagens_locutor:
            # Insere o 'titulo' e usa o 'titulo' como iid (ID interno)
            self.locutor_tree.insert('', 'end', iid=mensagem['titulo'], values=(mensagem['titulo'],))

    def falar_mensagem_selecionada(self):
        """Pega o texto da mensagem selecionada e o fala."""
        selected_iid = self.locutor_tree.focus()
        if not selected_iid:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione uma mensagem na lista para falar.")
            return
        
        # Como o 'iid' é o 'titulo', podemos buscar na lista
        for mensagem in self.lista_mensagens_locutor:
            if mensagem['titulo'] == selected_iid:
                self.falar_no_microfone(mensagem['texto']) # Chama a função principal de falar
                return
        
        messagebox.showerror("Erro", "Não foi possível encontrar o texto da mensagem selecionada.")

    def adicionar_mensagem(self):
        """Chama o popup para adicionar uma nova mensagem."""
        self.mostrar_popup_mensagem() # Chama sem argumento

    def editar_mensagem_selecionada(self):
        """Chama o popup para editar a mensagem selecionada."""
        selected_iid = self.locutor_tree.focus()
        if not selected_iid:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione uma mensagem para editar.")
            return
        
        # Encontra os dados da mensagem para enviar ao popup
        for mensagem in self.lista_mensagens_locutor:
            if mensagem['titulo'] == selected_iid:
                self.mostrar_popup_mensagem(dados_mensagem=mensagem)
                return

    def excluir_mensagem_selecionada(self):
        """Exclui a mensagem selecionada do JSON."""
        selected_iid = self.locutor_tree.focus()
        if not selected_iid:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione uma mensagem para excluir.")
            return
            
        if not messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir a mensagem:\n\n'{selected_iid}'\n\nEsta ação não pode ser desfeita."):
            return
            
        # Encontra e remove da lista
        self.lista_mensagens_locutor = [msg for msg in self.lista_mensagens_locutor if msg['titulo'] != selected_iid]
        
        # Salva a nova lista no JSON
        if salvar_mensagens_locutor(self.lista_mensagens_locutor):
            self.show_toast("Sucesso", "Mensagem excluída.")
            self.populate_locutor_tree() # Atualiza a lista na tela
        else:
            self.show_toast("Erro", "Não foi possível salvar a exclusão.", bootstyle='danger')
            # Recarrega a lista original em caso de falha ao salvar
            self.lista_mensagens_locutor = carregar_mensagens_locutor()

    def mostrar_popup_mensagem(self, dados_mensagem=None):
        """Cria um popup para Adicionar ou Editar uma mensagem."""
        
        is_edit_mode = dados_mensagem is not None

        popup = Toplevel(self)
        popup.title("Editar Mensagem" if is_edit_mode else "Adicionar Nova Mensagem")
        self._center_popup(popup, 600, 400) # (popup, largura, altura)
        popup.grab_set()

        container = ttk.Frame(popup, padding=20)
        container.pack(fill='both', expand=True)

        ttk.Label(container, text="Título (Nome curto para o botão):", font=self.FONT_BOLD).pack(anchor='w')
        entry_titulo = ttk.Entry(container, font=self.FONT_MAIN, width=70)
        entry_titulo.pack(fill='x', pady=(5, 15))

        ttk.Label(container, text="Texto Completo (O que será falado):", font=self.FONT_BOLD).pack(anchor='w')
        entry_texto = scrolledtext.ScrolledText(container, font=self.FONT_MAIN, height=5, width=70)
        entry_texto.pack(fill='both', expand=True, pady=5)
        
        if is_edit_mode:
            entry_titulo.insert(0, dados_mensagem['titulo'])
            entry_texto.insert("1.0", dados_mensagem['texto'])
            # Não permite editar o título (que é o ID)
            entry_titulo.config(state='disabled') 

        def on_save():
            novo_titulo = entry_titulo.get().strip()
            novo_texto = entry_texto.get("1.0", "end-1c").strip()

            if not novo_titulo or not novo_texto:
                messagebox.showwarning("Campos Vazios", "Título e Texto são obrigatórios.", parent=popup)
                return

            if is_edit_mode:
                # Modo Edição: Apenas atualiza o texto
                for msg in self.lista_mensagens_locutor:
                    if msg['titulo'] == dados_mensagem['titulo']:
                        msg['texto'] = novo_texto
                        break
            else:
                # Modo Adicionar: Verifica se o título já existe
                for msg in self.lista_mensagens_locutor:
                    if msg['titulo'].lower() == novo_titulo.lower():
                        messagebox.showwarning("Título Duplicado", "Já existe uma mensagem com esse título.", parent=popup)
                        return
                # Adiciona o novo
                self.lista_mensagens_locutor.append({"titulo": novo_titulo, "texto": novo_texto})
            
            # Salva no JSON e atualiza a UI
            if salvar_mensagens_locutor(self.lista_mensagens_locutor):
                self.show_toast("Sucesso", "Mensagem salva.")
                self.populate_locutor_tree()
                popup.destroy()
            else:
                messagebox.showerror("Erro", "Não foi possível salvar a mensagem.", parent=popup)
                # Recarrega a lista original
                self.lista_mensagens_locutor = carregar_mensagens_locutor()


        btn_save = ttk.Button(container, text="Salvar Mensagem", style="success.TButton", command=on_save)
        btn_save.pack(side='right', pady=(15, 0))
        btn_cancel = ttk.Button(container, text="Cancelar", style="secondary.Outline.TButton", command=popup.destroy)
        btn_cancel.pack(side='right', padx=10, pady=(15, 0))


    # --- MÉTODO PARA O LOCUTOR (VERSÃO COM VOZ NATURAL Edge-TTS) ---
    def falar_no_microfone(self, texto):
        if not texto.strip():
            messagebox.showwarning("Atenção", "O campo de texto está vazio.")
            return

        self.config(cursor="watch")
        self.update_idletasks()

        # Define a voz que queremos usar (Feminina, Brasil)
        VOICE = "pt-BR-FranciscaNeural"
        
        # Define o nome do arquivo de fala temporário
        temp_file = os.path.join(SCRIPT_PATH, "temp_locutor_audio.mp3")
        
        # --- NOVO: Define o caminho do arquivo de alerta ---
        alerta_file = os.path.join(DATA_FOLDER_PATH, "alerta.mp3")

        # edge-tts é assíncrono, então precisamos de uma função async
        # para *apenas gerar o arquivo*
        async def _gerar_arquivo_fala():
            print("Locutor: Gerando áudio com Edge-TTS...")
            communicate = Communicate(texto, VOICE)
            await communicate.save(temp_file)

        try:
            # --- PASSO 1: Gerar o arquivo de fala ---
            # Roda a função assíncrona para criar o temp_file
            asyncio.run(_gerar_arquivo_fala())
            
            # --- PASSO 2: Tocar a sequência ---
            # Agora que o arquivo existe, podemos tocar tudo de forma síncrona
            
            # 2a. Tocar o alerta (se existir)
            if os.path.exists(alerta_file):
                print("Locutor: Tocando alerta...")
                playsound(alerta_file)
            else:
                print("Aviso: 'alerta.mp3' não encontrado na pasta 'data'. Pulando o toque.")
                # (Opcional: podemos dar um beep do sistema, mas por enquanto só pulamos)
            
            # 2b. Tocar a fala (2x)
            print("Locutor: Tocando fala (1/2)...")
            playsound(temp_file)
            print("Locutor: Tocando fala (2/2)...")
            playsound(temp_file)
            
        except Exception as e:
            # Captura erros do asyncio, edge-tts ou playsound
            print(f"Erro no processo de locução: {e}")
            messagebox.showerror("Erro de Locutor", f"Não foi possível gerar ou tocar a voz.\n\nVerifique sua conexão com a internet.\n\nErro: {e}\n\n{traceback.format_exc()}")
                
        finally:
            # --- PASSO 3: Limpar ---
            # Garante que o arquivo de fala temporário seja removido
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    print(f"Aviso: Não foi possível remover o arquivo temporário: {e}")
            
            # Volta o cursor ao normal
            self.config(cursor="") 

# --- Bloco Principal ---
if __name__ == "__main__":
    app = App(themename="flatly")
    app.mainloop()