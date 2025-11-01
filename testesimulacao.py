# -*- coding: utf-8 -*-
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.toast import ToastNotification
# CORREÇÃO: ScrolledFrame removido da tela principal para evitar RecursionError
# Importamos Panedwindow (com W maiúsculo) do ttkbootstrap, que é o correto
from ttkbootstrap.widgets import Panedwindow 
from tkinter import messagebox, Toplevel, Entry, Button, StringVar, scrolledtext, \
                    PhotoImage, Listbox, filedialog
from datetime import date
from dateutil.relativedelta import relativedelta
import os
import sys
import requests
import json
import webbrowser
import platform
try:
    from PIL import Image, ImageTk, ImageDraw, ImageOps
    import piexif 
except ImportError:
    messagebox.showerror("Erro de Dependência", "Pillow e Piexif são necessários. Rode 'pip install Pillow piexif'")
import shutil 

# --- Variáveis Globais e Constantes ---
APP_VERSION = "3.4.1-Crash-Fix" 
VERSION_URL = "https://raw.githubusercontent.com/gabriielgouvea/veritas/main/version.json" 

# CORREÇÃO: Define o caminho da pasta 'data'
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_FOLDER_PATH = os.path.join(SCRIPT_PATH, "data") # Pasta para todos os dados
CONSULTORES_JSON_PATH = os.path.join(DATA_FOLDER_PATH, "consultores.json") # Caminho completo do JSON

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
        # CORREÇÃO: Usa o caminho completo da constante
        with open(CONSULTORES_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        messagebox.showerror("Erro Crítico", f"{CONSULTORES_JSON_PATH} não encontrado!")
        # Tenta criar a pasta data se não existir
        if not os.path.exists(DATA_FOLDER_PATH):
            os.makedirs(DATA_FOLDER_PATH)
            messagebox.showinfo("Pasta Criada", f"Pasta 'data' não encontrada. Criei ela para você.\n\nPor favor, adicione o 'consultores.json' e os ícones lá.")
        return []
    except Exception as e:
        messagebox.showerror("Erro ao Ler JSON", f"Erro ao ler {CONSULTORES_JSON_PATH}: {e}")
        return []

def salvar_consultores(lista_consultores):
    try:
        # CORREÇÃO: Usa o caminho completo da constante
        with open(CONSULTORES_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(lista_consultores, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar {CONSULTORES_JSON_PATH}: {e}")
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
        self.title(f"Veritas | Sistema de Gestão v{APP_VERSION}") 
        self.state('zoomed') 
        self.resizable(True, True)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- Carregar Dados dos Consultores ---
        self.lista_completa_consultores = carregar_consultores()
        self.nomes_consultores = [c['nome'] for c in self.lista_completa_consultores]

        # --- Carregar Imagens ---
        self.load_images()
        
        # --- Criar Estilos Customizados ---
        self.create_custom_styles()

        # --- SIDEBAR (Menu) ---
        self.sidebar_frame = ttk.Frame(self, style='Sidebar.TFrame', width=300) 
        self.sidebar_frame.grid(row=0, column=0, sticky="ns")
        self.sidebar_frame.grid_propagate(False) 
        self.sidebar_frame.grid_rowconfigure(9, weight=1) 

        # --- ÁREA DE CONTEÚDO PRINCIPAL ---
        # CORREÇÃO: Removido ScrolledFrame da tela principal
        self.main_frame = ttk.Frame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # --- WIDGETS DA SIDEBAR ---
        self.create_sidebar_widgets()
        
        # --- FOOTER ---
        footer_frame = ttk.Frame(self)
        footer_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.footer_label = ttk.Label(footer_frame, text="   Desenvolvido por Gabriel Gouvêa com seus parceiros GPT & Gemini 🤖", style='secondary.TLabel')
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
            self.icon_mensagens = ImageTk.PhotoImage(Image.open(os.path.join(DATA_FOLDER_PATH, "messages.png")).resize(ICON_SIZE))
            self.icon_comissao = ImageTk.PhotoImage(Image.open(os.path.join(DATA_FOLDER_PATH, "commission.png")).resize(ICON_SIZE))
            self.icon_folgas = ImageTk.PhotoImage(Image.open(os.path.join(DATA_FOLDER_PATH, "days_off.png")).resize(ICON_SIZE))
            self.icon_entradas = ImageTk.PhotoImage(Image.open(os.path.join(DATA_FOLDER_PATH, "entries.png")).resize(ICON_SIZE))
            self.icon_updates = ImageTk.PhotoImage(Image.open(os.path.join(DATA_FOLDER_PATH, "updates.png")).resize(ICON_SIZE))
            self.icon_developer = ImageTk.PhotoImage(Image.open(os.path.join(DATA_FOLDER_PATH, "developer.png")).resize(ICON_SIZE))
        except Exception as e:
            messagebox.showerror("Erro ao Carregar Ícones", f"Não foi possível carregar alguns ícones da pasta 'data'.\n\nVerifique se 'calculator.png', 'messages.png', etc., estão na pasta 'data'.\n\nErro: {e}")
            self.icon_simulador = self.icon_mensagens = self.icon_comissao = self.default_icon
            self.icon_folgas = self.icon_entradas = self.icon_updates = self.icon_developer = self.default_icon

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
        
        create_nav_button(2, "Simulador", "simulador", self.icon_simulador)
        create_nav_button(3, "Mensagens Prontas", "mensagens", self.icon_mensagens)
        create_nav_button(4, "Calculadora Comissão", "comissao", self.icon_comissao)
        create_nav_button(5, "Folgas", "folgas", self.icon_folgas)
        create_nav_button(6, "Entradas Liberadas", "entradas", self.icon_entradas)
        create_nav_button(7, "Área do Desenvolvedor", "developer", self.icon_developer)
        create_nav_button(8, "Verificar Atualizações", "updates", self.icon_updates)
        
        self.sidebar_frame.grid_rowconfigure(10, weight=1) 
        ttk.Separator(self.sidebar_frame).grid(row=9, column=0, sticky='sew', padx=10, pady=10)


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
        
        view_creators = {
            "simulador": self.create_cancellation_view,
            "mensagens": self.create_messages_view,
            "comissao": self.create_comissao_view,
            "folgas": self.create_folgas_view,
            "entradas": self.create_entradas_view,
            "developer_area": self.create_developer_area_view
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
        
        ttk.Label(login_container, text="Sistema Veritas", font=self.FONT_TITLE_LOGIN).pack(pady=(0, 25))

        form_frame = ttk.Frame(login_container)
        form_frame.pack(pady=10)

        ttk.Label(form_frame, text="Selecione ou digite seu nome:", font=self.FONT_MAIN).pack(anchor='w')
        
        self.combo_consultor_login = ttk.Combobox(form_frame, values=self.nomes_consultores, width=35, font=self.FONT_MAIN, state="normal")
        self.combo_consultor_login.pack(pady=(5, 15))
        self.combo_consultor_login.bind('<KeyRelease>', self.filtrar_combobox)
        self.combo_consultor_login.bind('<Button-1>', self.on_login_combobox_click)
        
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

    def filtrar_combobox(self, event=None):
        """Filtra a lista do combobox de login em tempo real."""
        texto_digitado = self.combo_consultor_login.get().upper()
        
        if not texto_digitado:
            self.combo_consultor_login['values'] = self.nomes_consultores
        else:
            nomes_filtrados = [nome for nome in self.nomes_consultores if texto_digitado in nome.upper()]
            self.combo_consultor_login['values'] = nomes_filtrados
            
    def on_login_combobox_click(self, event=None):
        """Força o dropdown do combobox a aparecer ao clicar."""
        if 'popdown' in self.combo_consultor_login.state():
            return
        # CORREÇÃO: Gera um evento de "Seta para Baixo" em vez de um clique recursivo.
        self.combo_consultor_login.event_generate('<Down>')


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
        # CORREÇÃO 2: Popup de motivo maior
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
                    # Permite que o container da caixa de texto expanda
                    other_entry_container.pack(fill='both', expand=True, pady=5, anchor='w')
                    ttk.Label(other_entry_container, text="Descreva:").pack(side='top', anchor='w')
                    # CORREÇÃO 2: Substituído Entry por ScrolledText
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
                # CORREÇÃO 2: Lendo do ScrolledText
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
        matricula = self.entry_matricula.get(); nome_cliente = self.entry_nome_cliente.get()
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
        matricula = self.entry_matricula.get(); nome_cliente = self.entry_nome_cliente.get()
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
            mensagem_completa = (f"Olá {nome_cliente}!\n\n"
                                 "Para prosseguir com o cancelamento da sua matrícula, "
                                 "preciso que preencha as informações e assine "
                                 f"através deste link: {link}\n\n"
                                 "Por favor, me mande o PDF assim que finalizar, ok? 😉")
            self.clipboard_clear(); self.clipboard_append(mensagem_completa)
            self.show_toast("Mensagem Copiada!", "O link e a mensagem para o cliente foram copiados!")
            janela_link.destroy()
        ttk.Button(container, text="Copiar Mensagem e Link", command=copiar_link_e_mensagem, style='primary.TButton').pack(pady=10)
        self.wait_window(janela_link)

    def gerar_documento_popup(self):
        if 'total_a_pagar' not in calculo_resultado: messagebox.showerror("Erro", "Execute um cálculo válido primeiro."); return
        nome_cliente = self.entry_nome_cliente.get(); matricula = self.entry_matricula.get()
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
        
        # CORREÇÃO 1: Layout do formulário e botões
        frame_form = ttk.Frame(self.main_frame)
        frame_form.pack(padx=0, pady=5, fill="x", anchor='w') 

        ttk.Label(frame_form, text="Data de Início (dd/mm/aaaa):", width=25, anchor='w').grid(row=0, column=0, sticky="w", pady=5)
        self.entry_data_inicio = ttk.Entry(frame_form, width=30) # Restaurado
        self.entry_data_inicio.grid(row=0, column=1, sticky="w", pady=5)
        self.entry_data_inicio.bind("<KeyRelease>", lambda e: formatar_data(e, self.entry_data_inicio)) # Bind restaurado

        ttk.Label(frame_form, text="Tipo de Plano:", width=25, anchor='w').grid(row=1, column=0, sticky="w", pady=5)
        self.combo_plano = ttk.Combobox(frame_form, values=list(PLANOS.keys()), width=27, state="readonly")
        self.combo_plano.grid(row=1, column=1, sticky="w", pady=5); self.combo_plano.set('Anual (12 meses)')

        ttk.Label(frame_form, text="Mensalidades em Atraso:", width=25, anchor='w').grid(row=2, column=0, sticky="w", pady=5)
        self.entry_parcelas_atraso = ttk.Entry(frame_form, width=30)
        self.entry_parcelas_atraso.grid(row=2, column=1, sticky="w", pady=5)

        # Frame de botões agora dentro do frame_form
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
        self.entry_matricula = ttk.Entry(self.frame_whatsapp, width=35, validate="key", validatecommand=vcmd_matricula)
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
        
        # CORREÇÃO 1: Lendo a data do Entry simples
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
        # CORREÇÃO 1: Limpando o Entry simples
        self.entry_data_inicio.delete(0, 'end'); self.entry_parcelas_atraso.delete(0, 'end'); self.combo_plano.set('Anual (12 meses)')
        
        self.frame_whatsapp.pack_forget()
        for widget in self.frame_resultado.winfo_children():
            if widget != self.frame_whatsapp: widget.destroy()
        
        ttk.Label(self.frame_resultado, text="O resultado aparecerá aqui...", font=self.FONT_MAIN, style="secondary.TLabel").pack(expand=True)
        self.entry_data_inicio.focus_set()
        
        self.entry_matricula.delete(0, 'end'); self.entry_nome_cliente.delete(0, 'end')
        calculo_resultado = {}
        
    def create_messages_view(self):
        """Cria a tela de Mensagens Prontas."""
        ttk.Label(self.main_frame, text="Mensagens Prontas", font=self.FONT_TITLE).pack(pady=(0, 10), anchor='w')
        ttk.Separator(self.main_frame).pack(fill='x', pady=10)
        ttk.Label(self.main_frame, text="Esta área ainda está em desenvolvimento...", font=self.FONT_MAIN).pack(pady=5, anchor='w')

    def create_comissao_view(self):
        """Cria a tela da Calculadora de Comissão."""
        ttk.Label(self.main_frame, text="Calculadora de Comissão", font=self.FONT_TITLE).pack(pady=(0, 10), anchor='w')
        ttk.Separator(self.main_frame).pack(fill='x', pady=10)
        ttk.Label(self.main_frame, text="Esta área ainda está em desenvolvimento...", font=self.FONT_MAIN).pack(pady=5, anchor='w')

    def create_folgas_view(self):
        """Cria a tela de Folgas."""
        ttk.Label(self.main_frame, text="Controle de Folgas", font=self.FONT_TITLE).pack(pady=(0, 10), anchor='w')
        ttk.Separator(self.main_frame).pack(fill='x', pady=10)
        ttk.Label(self.main_frame, text="Esta área ainda está em desenvolvimento...", font=self.FONT_MAIN).pack(pady=5, anchor='w')

    def create_entradas_view(self):
        """Cria a tela de Entradas Liberadas."""
        ttk.Label(self.main_frame, text="Entradas Liberadas", font=self.FONT_TITLE).pack(pady=(0, 10), anchor='w')
        ttk.Separator(self.main_frame).pack(fill='x', pady=10)
        ttk.Label(self.main_frame, text="Esta área ainda está em desenvolvimento...", font=self.FONT_MAIN).pack(pady=5, anchor='w')

    # --- NOVA ÁREA DO DESENVOLVEDOR ---
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
        
        # CORREÇÃO 1: Usa ttk.Panedwindow (w minúsculo)
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

    # --- Funções da Área do Desenvolvedor ---
    
    def on_dev_tree_select(self, event=None):
        """Chamado quando um item é selecionado na Treeview."""
        selected_iid = self.dev_tree.focus()
        if not selected_iid:
            return
        
        values = self.dev_tree.item(selected_iid, 'values')
        nome, foto_path = values[0], values[1]
        
        self.dev_nome_var.set(nome)
        self.dev_foto_path_var.set(foto_path)
        self.load_profile_picture(foto_path, size=PROFILE_PIC_SIZE, is_dev_preview=True)
        
    def dev_fazer_upload(self):
        """Abre a janela de diálogo para o upload de uma nova foto."""
        filepath = filedialog.askopenfilename(
            title="Selecionar foto", 
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp"), ("Todos os arquivos", "*.*")]
        )
        if not filepath:
            return 
            
        filename = os.path.basename(filepath)
        # CORREÇÃO: Destino é a pasta 'data'
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

# --- Bloco Principal ---
if __name__ == "__main__":
    app = App(themename="flatly") 
    app.mainloop()