# -*- coding: utf-8 -*-
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.toast import ToastNotification
from tkinter import messagebox, Toplevel, Entry, Button, StringVar
from datetime import date
from dateutil.relativedelta import relativedelta
import os
import sys
import requests
import json
import webbrowser
import platform

# --- Variáveis Globais e Constantes ---
APP_VERSION = "2.1.5" # Nova versão com popups padronizados e motivos pre-definidos
VERSION_URL = "https://raw.githubusercontent.com/gabriielgouvea/veritas/main/version.json" 

calculo_resultado = {}
consultor_selecionado = None
CONSULTORES = [
    "GABRIEL GOUVÊA", "GUILHERME VIEIRA", "NATALIA ROCHA",
    "RAPHAELA ALVES", "DAVI FERREIRA", "JANAINA SIBINELI", "LARISSA ROCHA",
    "ROBERTA FREIRIA", "JOÃO VITOR", "DANIELA MARTINS", "ROTIELY LOPES", "ROMULO ALVES", "GABRIEL FERNANDES", "LARISSA ROSSATO", "JAQUELINE"
]
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

# --- FUNÇÕES AUXILIARES (Lógica e Validação) ---
def check_for_updates():
    try:
        response = requests.get(VERSION_URL, timeout=10)
        response.raise_for_status()
        online_data = response.json()
        online_version = online_data["version"]
        download_url = online_data["download_url"]
        if online_version > APP_VERSION:
            msg = f"Uma nova versão ({online_version}) está disponível!\n\nA sua versão atual é {APP_VERSION}.\n\nDeseja ir para a página de download?"
            if messagebox.askyesno("Atualização Disponível", msg): webbrowser.open(download_url)
        else:
            messagebox.showinfo("Verificar Atualizações", "Você já está com a versão mais recente do programa.")
    except Exception as e:
        messagebox.showerror("Erro de Conexão", f"Não foi possível verificar as atualizações.\nVerifique sua conexão com a internet.\n\nErro: {e}")

def validar_matricula(P):
    if len(P) > 6: return False
    return str.isdigit(P) or P == ""

def validar_cpf_input(P):
    if len(P) > 11: return False
    return str.isdigit(P) or P == ""

def validar_cpf_algoritmo(cpf):
    cpf = ''.join(filter(str.isdigit, cpf));
    if len(cpf) != 11 or cpf == cpf[0] * 11: return False
    try:
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9)); digito1 = (soma * 10 % 11) % 10
        if digito1 != int(cpf[9]): return False
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10)); digito2 = (soma * 10 % 11) % 10
        if digito2 != int(cpf[10]): return False
    except ValueError: return False
    return True

def formatar_data(event, entry):
    texto_atual = entry.get()
    numeros = "".join(filter(str.isdigit, texto_atual))
    data_formatada = ""
    if len(numeros) > 0: data_formatada = numeros[:2]
    if len(numeros) > 2: data_formatada += "/" + numeros[2:4]
    if len(numeros) > 4: data_formatada += "/" + numeros[4:8]
    entry.delete(0, 'end')
    entry.insert(0, data_formatada)
    entry.icursor('end')

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

        self.title(f"Veritas | Simulador de Cancelamento v{APP_VERSION}")
        self.geometry("1100x700")
        self.resizable(True, True)
        self.place_window_center()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ttk.Frame(self, style='light.TFrame')
        self.sidebar_frame.grid(row=0, column=0, sticky="ns")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.main_frame = ttk.Frame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.logo_label = ttk.Label(self.sidebar_frame, text="VERITAS", font=("Helvetica", 20, "bold"), style='primary.TLabel')
        self.logo_label.grid(row=0, column=0, padx=20, pady=20)

        cancel_button = ttk.Button(self.sidebar_frame, text="  Simulador", command=lambda: self.show_view(self.create_cancellation_view), style='Link.TButton')
        cancel_button.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        messages_button = ttk.Button(self.sidebar_frame, text="  Mensagens Prontas", command=lambda: self.show_view(self.create_messages_view), style='Link.TButton')
        messages_button.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        updates_button = ttk.Button(self.sidebar_frame, text="  Verificar Atualizações", command=check_for_updates, style='Link.TButton')
        updates_button.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        self.theme_button = ttk.Button(self.sidebar_frame, text="🌙 Mudar Tema", style="Link.TButton", command=self.toggle_theme)
        self.theme_button.grid(row=4, column=0, padx=10, pady=20)
        
        self.user_info_frame = ttk.Frame(self.sidebar_frame, style='light.TFrame')
        self.user_info_frame.grid(row=7, column=0, sticky="sew", pady=10)
        self.consultant_label = ttk.Label(self.user_info_frame, text="Nenhum consultor selecionado", style='dark.TLabel')
        self.consultant_label.pack(pady=(0,5), padx=10)
        trocar_consultor_button = ttk.Button(self.user_info_frame, text="Trocar Consultor", command=self.show_login_view, style='Link.TButton')
        trocar_consultor_button.pack(pady=(0,10))
        
        footer_frame = ttk.Frame(self)
        footer_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.footer_label = ttk.Label(footer_frame, text="   Desenvolvido por Gabriel Gouvêa com seus parceiros GPT & Gemini 🤖", style='secondary.TLabel')
        self.footer_label.pack(fill='x')

        self.show_login_view()

    def show_toast(self, title, message, bootstyle='success'):
        toast = ToastNotification(title=title, message=message, duration=3000, bootstyle=bootstyle, position=(20, 20, 'se'))
        toast.show_toast()

    def toggle_theme(self):
        if self.style.theme.name == 'flatly':
            self.style.theme_use('darkly'); self.theme_button.config(text="☀️ Mudar Tema")
            self.sidebar_frame.config(style='secondary.TFrame'); self.user_info_frame.config(style='secondary.TFrame')
            self.consultant_label.config(style='inverse-secondary.TLabel'); self.logo_label.config(style='inverse-secondary.TLabel')
            self.footer_label.config(style='inverse.TLabel')
        else:
            self.style.theme_use('flatly'); self.theme_button.config(text="🌙 Mudar Tema")
            self.sidebar_frame.config(style='light.TFrame'); self.user_info_frame.config(style='light.TFrame')
            self.consultant_label.config(style='dark.TLabel'); self.logo_label.config(style='primary.TLabel')
            self.footer_label.config(style='secondary.TLabel')

    def show_view(self, view_creator):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        view_creator()

    def show_login_view(self):
        self.sidebar_frame.grid_remove()
        for widget in self.main_frame.winfo_children(): widget.destroy()
        
        login_container = ttk.Frame(self.main_frame); login_container.pack(expand=True)
        
        ttk.Label(login_container, text="Selecione o Consultor", font=("Helvetica", 16, "bold")).pack(pady=10)
        self.combo_consultor_login = ttk.Combobox(login_container, values=CONSULTORES, width=30, font=("Helvetica", 12), state="readonly")
        self.combo_consultor_login.pack(pady=10)
        
        def on_login():
            global consultor_selecionado
            consultor_selecionado = self.combo_consultor_login.get()
            if not consultor_selecionado:
                messagebox.showwarning("Atenção", "Por favor, selecione um consultor para continuar."); return
            
            self.consultant_label.config(text=f"👤 {consultor_selecionado}")
            self.sidebar_frame.grid()
            self.show_view(self.create_cancellation_view)

        ttk.Button(login_container, text="Entrar", command=on_login, style='success.TButton', width=20).pack(pady=20)
        
    def create_messages_view(self):
        ttk.Label(self.main_frame, text="Mensagens Prontas", font=("Helvetica", 18, "bold")).pack(pady=10, anchor='w')
        ttk.Separator(self.main_frame).pack(fill='x', pady=10)
        ttk.Label(self.main_frame, text="Esta área ainda está em desenvolvimento...", font=("Helvetica", 12)).pack(pady=5, anchor='w')
    
    # --- NOVO MÉTODO PARA CENTRALIZAR POPUPS ---
    def _center_popup(self, popup, width, height):
        self.update_idletasks() # Atualiza para garantir que as dimensões da janela principal estejam corretas
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width()
        main_height = self.winfo_height()
        
        pos_x = main_x + (main_width // 2) - (width // 2)
        pos_y = main_y + (main_height // 2) - (height // 2)
        
        popup.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        popup.resizable(False, False)
        popup.transient(self) # Faz o popup ser dependente da janela principal
        popup.grab_set()      # Bloqueia interações com a janela principal

    # --- MÉTODO ATUALIZADO PARA O POPUP DE MOTIVO COM OPÇÕES ---
    def _ask_for_reason_popup(self):
        self.popup_motivo = None # Variável para guardar o resultado

        popup = Toplevel(self)
        popup.title("Motivo do Cancelamento")
        
        # Define o tamanho para o popup de motivo (ajustado para as opções)
        popup_width = 500
        popup_height = 350
        self._center_popup(popup, popup_width, popup_height)

        container = ttk.Frame(popup, padding=20)
        container.pack(fill='both', expand=True)
        
        ttk.Label(container, text="Selecione o motivo do cancelamento:", font=("-weight bold")).pack(pady=(0, 10), anchor='w')
        
        # Variável para os Radiobuttons
        selected_reason = StringVar(value="") 
        entry_other_reason = None # Variável para a Entry de "Outros"

        def update_other_entry_state():
            nonlocal entry_other_reason
            if selected_reason.get() == "OUTROS":
                if entry_other_reason is None: # Cria a entry se ainda não existe
                    entry_other_reason = ttk.Entry(container, width=50)
                    entry_other_reason.pack(pady=5, anchor='w')
                    entry_other_reason.focus_set()
            else:
                if entry_other_reason is not None: # Destrói a entry se existe
                    entry_other_reason.destroy()
                    entry_other_reason = None
        
        # Cria os Radiobuttons para os motivos
        for motivo in MOTIVOS_CANCELAMENTO:
            rb = ttk.Radiobutton(container, text=motivo, variable=selected_reason, value=motivo, command=update_other_entry_state, style='Toolbutton')
            rb.pack(anchor='w', pady=2)
        
        def on_confirm():
            motivo_selecionado = selected_reason.get()
            final_motivo = ""

            if not motivo_selecionado:
                messagebox.showwarning("Campo Vazio", "Por favor, selecione ou descreva um motivo.", parent=popup)
                return
            
            if motivo_selecionado == "OUTROS":
                if entry_other_reason is None or not entry_other_reason.get():
                    messagebox.showwarning("Campo Vazio", "Por favor, descreva o motivo em 'Outros'.", parent=popup)
                    return
                final_motivo = f"OUTROS: {entry_other_reason.get()}"
            else:
                final_motivo = motivo_selecionado

            self.popup_motivo = final_motivo
            popup.destroy()

        ttk.Button(container, text="Confirmar e Copiar", style="success.TButton", command=on_confirm).pack(pady=15)
        
        self.wait_window(popup)

    def copiar_texto_gerencia(self):
        global consultor_selecionado
        if 'total_a_pagar' not in calculo_resultado: messagebox.showerror("Erro", "Execute um cálculo válido primeiro."); return
        
        matricula = self.entry_matricula.get(); nome_cliente = self.entry_nome_cliente.get()
        if not matricula or not nome_cliente: messagebox.showerror("Erro", "Preencha a Matrícula e o Nome do Cliente."); return
        
        self._ask_for_reason_popup() # Chama o popup de motivo
        
        motivo = self.popup_motivo
        
        if not motivo: # Se o usuário fechou o popup sem confirmar ou não escolheu motivo
            return
            
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

    # --- MÉTODO ATUALIZADO PARA O POPUP DE LINK ---
    def mostrar_janela_com_link(self, link):
        janela_link = Toplevel(self); janela_link.title("Link Gerado com Sucesso!")
        
        popup_width = 450 # Mesma largura do popup de CPF
        popup_height = 180 # Altura ajustada
        self._center_popup(janela_link, popup_width, popup_height)
        
        container = ttk.Frame(janela_link, padding=20); container.pack(fill='both', expand=True)
        ttk.Label(container, text="Envie este link para o cliente:", font=("-weight bold")).pack(pady=(0, 10))
        entry_link = ttk.Entry(container, width=60)
        entry_link.insert(0, link)
        entry_link.pack(padx=10, pady=5); entry_link.config(state="readonly")
        
        def copiar_link():
            self.clipboard_clear(); self.clipboard_append(link)
            self.show_toast("Link Copiado!", "O link foi copiado para a área de transferência.")
            # Não mudamos o texto do botão para que o popup possa ser fechado e reaberto sem confusão.
            # Se a cópia já foi avisada pelo toast, mudar o texto do botão é redundante.
        
        ttk.Button(container, text="Copiar Link", command=copiar_link, style='primary.TButton').pack(pady=10)
        
        self.wait_window(janela_link)

    # --- MÉTODO ATUALIZADO PARA O POPUP DE CPF ---
    def gerar_documento_popup(self):
        if 'total_a_pagar' not in calculo_resultado: messagebox.showerror("Erro", "Execute um cálculo válido primeiro."); return
        nome_cliente = self.entry_nome_cliente.get(); matricula = self.entry_matricula.get()
        if not nome_cliente or not matricula: messagebox.showerror("Erro", "Preencha Nome e Matrícula para gerar o documento."); return
        
        popup = Toplevel(self); popup.title("Informação Adicional")
        
        popup_width = 450
        popup_height = 200
        self._center_popup(popup, popup_width, popup_height)

        container = ttk.Frame(popup, padding=20)
        container.pack(fill='both', expand=True)
        
        ttk.Label(container, text="Digite o CPF do Cliente:", font=("-weight bold")).pack(pady=(0, 10))
        vcmd_cpf = (container.register(validar_cpf_input), '%P')
        entry_cpf_popup = ttk.Entry(container, width=30, validate="key", validatecommand=vcmd_cpf); entry_cpf_popup.pack(pady=5); entry_cpf_popup.focus_set()
        
        def finalizar_geracao():
            cpf_cliente = entry_cpf_popup.get()
            if not validar_cpf_algoritmo(cpf_cliente): 
                messagebox.showerror("CPF Inválido", "O CPF digitado não é válido.", parent=popup); return
            dados_para_enviar = {"nome": nome_cliente.upper(), "cpf": cpf_cliente, "matricula": matricula, "valor_multa": f"{calculo_resultado['total_a_pagar']:.2f}", "data_inicio_contrato": calculo_resultado['data_inicio_contrato'].strftime('%d/%m/%Y'),"consultor": consultor_selecionado.upper()}
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

    def create_cancellation_view(self):
        frame_entrada = ttk.Frame(self.main_frame); frame_entrada.pack(padx=10, pady=5, fill="x", anchor='n')

        ttk.Label(frame_entrada, text="Data de Início (dd/mm/aaaa):").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_data_inicio = ttk.Entry(frame_entrada, width=30)
        self.entry_data_inicio.grid(row=0, column=1, sticky="w", pady=5)
        self.entry_data_inicio.bind("<KeyRelease>", lambda e: formatar_data(e, self.entry_data_inicio))

        ttk.Label(frame_entrada, text="Tipo de Plano:").grid(row=1, column=0, sticky="w", pady=5)
        self.combo_plano = ttk.Combobox(frame_entrada, values=list(PLANOS.keys()), width=27, state="readonly")
        self.combo_plano.grid(row=1, column=1, sticky="w", pady=5); self.combo_plano.set('Anual (12 meses)')

        ttk.Label(frame_entrada, text="Mensalidades em Atraso:").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_parcelas_atraso = ttk.Entry(frame_entrada, width=30)
        self.entry_parcelas_atraso.grid(row=2, column=1, sticky="w", pady=5)

        frame_botoes = ttk.Frame(self.main_frame); frame_botoes.pack(pady=10, padx=10, fill="x", anchor='n')
        
        self.frame_resultado = ttk.Frame(self.main_frame, padding=(20, 15), relief="solid", borderwidth=1)
        self.frame_resultado.pack(pady=5, padx=10, fill="both", expand=True) 
        
        self.placeholder_label = ttk.Label(self.frame_resultado, text="O resultado aparecerá aqui...", font=("Helvetica", 11), style="secondary.TLabel")
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
        frame_botoes_copiar.grid(row=2, column=1, columnspan=2, pady=15) # Ajustado para row 2
        
        ttk.Button(frame_botoes_copiar, text="Copiar (Pendências)", style='success.Outline.TButton', command=self.copiar_texto_gerencia).pack(side="left", padx=5)
        ttk.Button(frame_botoes_copiar, text="Copiar Detalhes", style='info.Outline.TButton', command=self.copiar_texto_cliente).pack(side="right", padx=5)
        
        ttk.Button(self.frame_whatsapp, text="Gerar Link de Assinatura", style='danger.TButton', command=self.gerar_documento_popup).grid(row=3, column=1, columnspan=2, pady=(5,0), sticky='ew') # Ajustado para row 3
        
        self.frame_whatsapp.columnconfigure(0, weight=1); self.frame_whatsapp.columnconfigure(3, weight=1)

        def do_calculation():
            data_inicio_str = self.entry_data_inicio.get()
            tipo_plano = self.combo_plano.get()
            parcelas_atrasadas_str = self.entry_parcelas_atraso.get() or "0"
            if not data_inicio_str or not tipo_plano: messagebox.showerror("Erro", "Preencha a Data de Início e o Tipo de Plano."); return
            try:
                dia, mes, ano = map(int, data_inicio_str.split('/')); data_inicio = date(ano, mes, dia)
            except Exception:
                messagebox.showerror("Erro", "Formato de data inválido."); return
            data_simulacao_hoje = date.today()
            if data_inicio > data_simulacao_hoje: messagebox.showerror("Data Inválida", "A Data de Início do contrato não pode ser uma data no futuro."); return

            def processar_calculo(pagamento_hoje_status=None):
                global calculo_resultado
                calculo_resultado = logica_de_calculo(data_inicio, tipo_plano, parcelas_atrasadas_str, pagamento_hoje_status)
                
                for widget in self.frame_resultado.winfo_children():
                    if widget != self.frame_whatsapp: widget.destroy()
                
                if 'erro_data' in calculo_resultado: 
                    messagebox.showerror("Data Inválida", calculo_resultado['erro_data'])
                    ttk.Label(self.frame_resultado, text="O resultado aparecerá aqui...").pack(expand=True); self.frame_whatsapp.pack_forget(); return
                elif 'erro_geral' in calculo_resultado: 
                    messagebox.showerror("Erro", calculo_resultado['erro_geral'])
                    ttk.Label(self.frame_resultado, text="O resultado aparecerá aqui...").pack(expand=True); self.frame_whatsapp.pack_forget(); return
                
                ttk.Label(self.frame_resultado, text=f"Data da Simulação: {calculo_resultado['data_simulacao'].strftime('%d/%m/%Y')}").pack(fill='x', anchor='w')
                ttk.Label(self.frame_resultado, text=f"Plano: {calculo_resultado['plano']} (R$ {calculo_resultado['valor_plano']:.2f})").pack(fill='x', anchor='w')
                ttk.Label(self.frame_resultado, text=f"Início do Contrato: {calculo_resultado['data_inicio_contrato'].strftime('%d/%m/%Y')}").pack(fill='x', anchor='w')
                ttk.Separator(self.frame_resultado).pack(fill='x', pady=5)
                ttk.Label(self.frame_resultado, text=f"Valor por parcelas em atraso ({calculo_resultado['parcelas_atrasadas_qtd']}x): R$ {calculo_resultado['valor_atrasado']:.2f}", font=("-weight bold")).pack(fill='x', anchor='w')
                ttk.Label(self.frame_resultado, text=f"Mensalidade a vencer: {calculo_resultado['linha_mensalidade_a_vencer']}", font=("-weight bold")).pack(fill='x', anchor='w')
                ttk.Label(self.frame_resultado, text=f"Multa contratual (10% sobre {calculo_resultado['meses_para_multa']} meses): R$ {calculo_resultado['valor_multa']:.2f}", font=("-weight bold")).pack(fill='x', anchor='w')
                ttk.Separator(self.frame_resultado).pack(fill='x', pady=5)
                ttk.Label(self.frame_resultado, text=f"TOTAL A SER PAGO: R$ {calculo_resultado['total_a_pagar']:.2f}", font=("-weight bold")).pack(fill='x', anchor='w')
                ttk.Separator(self.frame_resultado).pack(fill='x', pady=5)
                ttk.Label(self.frame_resultado, text=f"O acesso à academia será encerrado em: {calculo_resultado['data_acesso_final'].strftime('%d/%m/%Y')}").pack(fill='x', anchor='w')
                
                self.frame_whatsapp.pack(pady=20, padx=10, fill="x", side='bottom')

            if data_simulacao_hoje.day == data_inicio.day and data_simulacao_hoje >= data_inicio:
                resposta = messagebox.askyesno("Verificação de Pagamento", "A parcela de hoje já foi debitada do cartão do cliente?")
                processar_calculo(resposta)
            else:
                processar_calculo()

        def clear_fields():
            global calculo_resultado
            self.entry_data_inicio.delete(0, 'end'); self.entry_parcelas_atraso.delete(0, 'end'); self.combo_plano.set('Anual (12 meses)')
            
            self.frame_whatsapp.pack_forget()
            for widget in self.frame_resultado.winfo_children():
                if widget != self.frame_whatsapp: widget.destroy()
            
            ttk.Label(self.frame_resultado, text="O resultado aparecerá aqui...", font=("Helvetica", 11), style="secondary.TLabel").pack(expand=True)
            self.entry_data_inicio.focus_set()
            
            self.entry_matricula.delete(0, 'end'); self.entry_nome_cliente.delete(0, 'end')
            calculo_resultado = {}

        ttk.Button(frame_botoes, text="Calcular", command=do_calculation, style='success.TButton').pack(side="left", expand=True, padx=5)
        ttk.Button(frame_botoes, text="Nova Simulação", command=clear_fields, style='danger.TButton').pack(side="right", expand=True, padx=5)

# --- Bloco Principal ---
if __name__ == "__main__":
    app = App(themename="flatly")
    app.mainloop()