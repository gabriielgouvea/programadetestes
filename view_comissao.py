# -*- coding: utf-8 -*-

"""
Arquivo: view_comissao.py
Descrição: Contém a classe ComissaoView.
(v5.16.0 - COMPLETO: PDF + Extrato Seguro + Cálculos)
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
from ttkbootstrap.widgets.scrolled import ScrolledFrame
from tkinter import filedialog, messagebox, Toplevel, StringVar, IntVar, END, DoubleVar
from tkinter import ttk as standard_ttk
import os
import traceback
from datetime import date, datetime
import calendar
import random

# --- Importa para PDF ---
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor, black, gray, white
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as PDFImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
except ImportError:
    print("AVISO: ReportLab não instalado. O PDF não funcionará. Rode 'pip install reportlab'")

# --- Importa as funções de utilidade ---
from app_utils import formatar_reais

# --- Importa o processador de PDF ---
try:
    from calculadora_core import processar_pdf
except ImportError:
    processar_pdf = None

# --- Importa o gerenciador do Firebase ---
import firebase_manager as fm

class ComissaoView:
    
    def __init__(self, app, main_frame):
        self.app = app
        self.main_frame = main_frame
        
        # Dados
        self.dados_pins = fm.carregar_pins_consultores()
        self.dados_caixa_comissao = fm.carregar_caixa_comissao()
        self.nome_consultor_logado = self.app.consultor_logado_data.get('nome', 'N/A')
        
        # Recupera dados cadastrais completos (para o PDF)
        self.dados_completos_consultor = self.app.consultor_logado_data 
        
        self.pin_verificado_nesta_sessao = False 
        self.saldo_acumulado_mes = 0.00
        self.saldo_esta_visivel = False
        self.resultado_atual_pdf = None 
        self.itens_extrato_atual = [] # Guarda os dados filtrados para o PDF

        if processar_pdf is None:
            ttk.Label(self.main_frame, text="Erro Crítico: Core não encontrado", style="danger.TLabel").pack()
            return

        # Título
        ttk.Label(self.main_frame, text="Calculadora de Comissão", font=self.app.FONT_TITLE).pack(pady=(0, 10), anchor='w')

        # Abas
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill='both', expand=True)

        tab_calcular = ttk.Frame(notebook, padding=10)
        tab_consultar = ttk.Frame(notebook, padding=10)
        
        notebook.add(tab_calcular, text=' Calcular e Registrar ')
        notebook.add(tab_consultar, text=' Consultar Meu Saldo ')

        self.criar_aba_calcular(tab_calcular)
        self.criar_aba_consultar(tab_consultar)

    # --- ABA 1: CALCULAR ---

    def criar_aba_calcular(self, parent_frame):
        # Topo: Upload
        frame_upload = ttk.Frame(parent_frame)
        frame_upload.pack(side='top', fill='x', pady=(0, 10))

        btn_upload = ttk.Button(frame_upload, text="Fazer Upload do PDF de Fechamento",
                                command=self.processar_pdf_comissao,
                                style='primary.TButton',
                                width=40)
        btn_upload.pack(side='left', ipady=5, pady=5)

        self.lbl_pdf_selecionado = ttk.Label(frame_upload, text="Nenhum arquivo selecionado.", style='secondary.TLabel')
        self.lbl_pdf_selecionado.pack(side='left', padx=10)

        # Área de Resultados
        self.scrolled_frame = ScrolledFrame(parent_frame, autohide=False)
        self.app.tracked_scrolled_frames.append(self.scrolled_frame)
        self.scrolled_frame.pack(side='top', fill='both', expand=True)
        self.frame_resultado_comissao = self.scrolled_frame.container 

        self.lbl_inicial = ttk.Label(self.frame_resultado_comissao,
                    text="Selecione um PDF para visualizar os gráficos e calcular.",
                    style='secondary.TLabel')
        self.lbl_inicial.pack(pady=50)

    def processar_pdf_comissao(self):
        filepath = filedialog.askopenfilename(title="Selecione o PDF", filetypes=[("Arquivos PDF", "*.pdf")])
        if not filepath: return

        self.lbl_pdf_selecionado.config(text=os.path.basename(filepath))
        for widget in self.frame_resultado_comissao.winfo_children(): widget.destroy()

        self.app.config(cursor="watch")
        self.app.update_idletasks()

        try:
            resultados = processar_pdf(filepath)
            self.app.config(cursor="")
            
            # --- VALIDAÇÃO 1: NOME DO CONSULTOR ---
            operador_pdf = resultados.get("info_cabecalho", {}).get("operador", "").upper()
            consultor_logado = self.nome_consultor_logado.upper()
            
            # Lógica de comparação flexível (primeiro nome ou contains)
            nome_match = False
            if operador_pdf in consultor_logado or consultor_logado in operador_pdf:
                nome_match = True
            else:
                p_nome_pdf = operador_pdf.split()[0] if operador_pdf else ""
                p_nome_logado = consultor_logado.split()[0] if consultor_logado else ""
                if p_nome_pdf == p_nome_logado:
                    nome_match = True
            
            if not nome_match and operador_pdf != "NÃO IDENTIFICADO":
                msg = (f"VOCÊ está fazendo consulta da comissão do consultor(a) {operador_pdf}.\n\n"
                       f"Selecione o PDF correto ou faça login com outro usuário para continuar.")
                
                messagebox.showwarning("Atenção - Consultor Diferente", msg)
                self.lbl_pdf_selecionado.config(text="Arquivo rejeitado (Usuário incorreto).")
                
                # Mostra aviso na tela também
                ttk.Label(self.frame_resultado_comissao, 
                          text=f"⚠️ Acesso Bloqueado: Este PDF pertence a {operador_pdf}.", 
                          style="danger.TLabel", font=("Segoe UI", 12, "bold")).pack(pady=20)
                return 

            self.resultado_atual_pdf = resultados
            self.exibir_dashboard_classico(resultados)

        except Exception as e:
            self.app.config(cursor="")
            messagebox.showerror("Erro", f"Erro ao ler PDF: {e}")

    def _create_metric_widget(self, parent, label_text, value_text, bootstyle):
        frame = ttk.Frame(parent, bootstyle=bootstyle, padding=10, borderwidth=1, relief="raised")
        ttk.Label(frame, text=label_text, font=(self.app.FONT_MAIN[0], 9, 'bold'), bootstyle=f'inverse-{bootstyle}').pack(side='top', anchor='nw')
        ttk.Label(frame, text=value_text, font=(self.app.FONT_MAIN[0], 16, 'bold'), bootstyle=f'inverse-{bootstyle}').pack(side='bottom', anchor='se', pady=(5,0))
        return frame

    def exibir_dashboard_classico(self, resultados):
        container = self.frame_resultado_comissao
        
        # 1. Botão Fechamento
        frame_acao = ttk.Frame(container)
        frame_acao.pack(fill='x', pady=(0, 15))
        ttk.Label(frame_acao, text="Verifique os valores abaixo. Se estiver tudo certo:", font=("Segoe UI", 10), style="secondary.TLabel").pack(side='left')
        ttk.Button(frame_acao, text="Realizar Fechamento do Dia ➔", style="success.TButton", command=self.abrir_popup_fechamento).pack(side='right')

        # 2. Cabeçalho
        info = resultados.get("info_cabecalho", {})
        frame_info = ttk.Frame(container, bootstyle='info', padding=10)
        frame_info.pack(fill='x', pady=5)
        ttk.Label(frame_info, text=f"Fechamento: {info.get('operador')}    |    Período: {info.get('periodo')}", font=self.app.FONT_BOLD, bootstyle='inverse-info').pack()

        # 3. Cards
        frame_resumo = standard_ttk.LabelFrame(container, text=" Resumo do Cálculo ", padding=15)
        frame_resumo.pack(fill='x', pady=10)
        frame_metrics = ttk.Frame(frame_resumo)
        frame_metrics.pack(fill='x')
        frame_metrics.grid_columnconfigure((0,1,2,3), weight=1)

        self._create_metric_widget(frame_metrics, "Valor Total", formatar_reais(resultados.get('valor_total_bruto', 0)), 'secondary').grid(row=0, column=0, padx=5, sticky='ew')
        self._create_metric_widget(frame_metrics, "Descontos", formatar_reais(resultados.get('total_deducoes', 0)), 'warning').grid(row=0, column=1, padx=5, sticky='ew')
        self._create_metric_widget(frame_metrics, "Valor Comissionável", formatar_reais(resultados.get('base_comissionavel', 0)), 'primary').grid(row=0, column=2, padx=5, sticky='ew')
        self._create_metric_widget(frame_metrics, "SUA COMISSÃO (PDF)", formatar_reais(resultados.get('comissao_final', 0)), 'success').grid(row=0, column=3, padx=5, sticky='ew')

        # 4. Vendas
        frame_vendas = standard_ttk.LabelFrame(container, text=" Vendas e Atendimentos ", padding=15)
        frame_vendas.pack(fill='x', expand=True, pady=10)
        resumo = resultados.get("resumo_vendas", {})
        ttk.Label(frame_vendas, text=f"Total de Atendimentos: {resumo.get('total_atendimentos', 0)} transações").pack(anchor='w')
        
        tree_vendas = ttk.Treeview(frame_vendas, columns=('metodo', 'qtd', 'valor'), show='headings', height=6, bootstyle='info')
        tree_vendas.heading('metodo', text='Forma'); tree_vendas.heading('qtd', text='Qtd.'); tree_vendas.heading('valor', text='Total')
        tree_vendas.column('metodo', width=250); tree_vendas.column('qtd', anchor='center', width=50); tree_vendas.column('valor', anchor='e', width=120)
        
        for m, d in resumo.items():
            if isinstance(d, dict) and d.get('qtd', 0) > 0:
                tree_vendas.insert('', 'end', values=(m.replace("_", " ").title(), d.get('qtd'), formatar_reais(d.get('valor'))))
        tree_vendas.pack(fill='x', expand=True, pady=5)

        # 5. Deduções
        detalhes = resultados.get('detalhes', {})
        deducoes = {k: v for k, v in detalhes.items() if v > 0}
        if deducoes:
            frame_ded = standard_ttk.LabelFrame(container, text=" Deduções Detalhadas ", padding=15)
            frame_ded.pack(fill='x', expand=True, pady=10)
            tree_d = ttk.Treeview(frame_ded, columns=('m', 'v'), show='headings', height=len(deducoes), bootstyle='danger')
            tree_d.heading('m', text='Motivo'); tree_d.heading('v', text='Valor')
            tree_d.column('m', width=300); tree_d.column('v', anchor='e', width=120)
            for k, v in deducoes.items(): tree_d.insert('', 'end', values=(k, formatar_reais(v)))
            tree_d.pack(fill='x')

    # --- FLUXO DE FECHAMENTO E VALIDAÇÕES ---

    def abrir_popup_fechamento(self):
        if not self.resultado_atual_pdf: return

        # --- VALIDAÇÃO 2: DATA ---
        periodo_texto = self.resultado_atual_pdf.get("info_cabecalho", {}).get("periodo", "")
        data_pdf = None
        try:
            data_str = periodo_texto.split(' ')[0] 
            data_pdf = datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
        except: pass

        hoje = date.today()
        data_divergente = (data_pdf and data_pdf != hoje)

        # POPUP
        popup = Toplevel(self.app)
        popup.title("Registrar Fechamento")
        altura = 380 if data_divergente else 280
        self.app._center_popup(popup, 400, altura)
        container = ttk.Frame(popup, padding=20)
        container.pack(fill='both', expand=True)

        # 1. Planos
        ttk.Label(container, text="1. Planos Vendidos", font=self.app.FONT_BOLD).pack(anchor='w')
        ttk.Label(container, text="Quantidade de planos hoje:").pack(anchor='w')
        var_planos = StringVar(value="0")
        entry_planos = ttk.Entry(container, textvariable=var_planos, font=("Helvetica", 12))
        entry_planos.pack(fill='x', pady=(0, 15))
        entry_planos.select_range(0, END)
        entry_planos.focus_set()

        # 2. Data Divergente
        var_data_registro = StringVar(value=hoje.strftime("%d/%m/%Y")) 
        entry_data = None

        if data_divergente:
            frame_aviso = ttk.Frame(container, bootstyle='warning', padding=10)
            frame_aviso.pack(fill='x', pady=(0, 15))
            
            msg = f"O PDF é do dia {data_pdf.strftime('%d/%m')} e hoje é {hoje.strftime('%d/%m')}. Deseja registrar mesmo assim?"
            ttk.Label(frame_aviso, text=msg, bootstyle='inverse-warning', wraplength=350).pack(anchor='w', pady=(0,5))
            ttk.Label(frame_aviso, text="Selecione a data correta:", bootstyle='inverse-warning').pack(anchor='w')
            
            entry_data = DateEntry(frame_aviso, dateformat="%d/%m/%Y", bootstyle='warning')
            entry_data.entry.delete(0, END)
            entry_data.entry.insert(0, data_pdf.strftime("%d/%m/%Y")) 
            entry_data.pack(fill='x', pady=5)
        
        def ir_para_confirmacao():
            try: qtd = int(var_planos.get())
            except ValueError: messagebox.showerror("Erro", "Número inválido.", parent=popup); return
            
            data_final = entry_data.entry.get() if (data_divergente and entry_data) else var_data_registro.get()
            popup.destroy()
            self.abrir_popup_confirmacao_final(qtd, data_final)

        ttk.Button(container, text="Próximo ➔", style="primary.TButton", command=ir_para_confirmacao).pack(side='bottom', fill='x')
        popup.bind("<Return>", lambda e: ir_para_confirmacao())

    def abrir_popup_confirmacao_final(self, qtd_planos, data_registro_str):
        """Última checagem antes de salvar - CORRIGIDO UX"""
        popup = Toplevel(self.app)
        popup.title("Aguardando Confirmação") # Título menos 'final'
        self.app._center_popup(popup, 400, 380) 
        
        container = ttk.Frame(popup, padding=20)
        container.pack(fill='both', expand=True)

        # Pergunta clara
        ttk.Label(container, text="Deseja confirmar este registro?", font=("Segoe UI", 14, "bold"), wraplength=380, justify="center").pack(pady=(0, 15))

        val_comissao = self.resultado_atual_pdf.get('comissao_final', 0)
        val_planos = qtd_planos * 40.00
        val_total = val_comissao + val_planos

        def add_line(lbl, val, style='default', big=False):
            fr = ttk.Frame(container); fr.pack(fill='x', pady=4)
            font_lbl = ("Segoe UI", 11)
            font_val = ("Segoe UI", 11, "bold") if not big else ("Segoe UI", 14, "bold")
            ttk.Label(fr, text=lbl, font=font_lbl, bootstyle='secondary').pack(side='left')
            ttk.Label(fr, text=val, font=font_val, bootstyle=style).pack(side='right')

        add_line("Consultor:", self.nome_consultor_logado)
        add_line("Data de Registro:", data_registro_str)
        ttk.Separator(container).pack(fill='x', pady=10)
        add_line("Valor Comissão:", formatar_reais(val_comissao))
        add_line(f"Valor Planos ({qtd_planos}):", formatar_reais(val_planos))
        ttk.Separator(container).pack(fill='x', pady=10)
        add_line("TOTAL A RECEBER:", formatar_reais(val_total), "success", big=True)

        def confirmar():
            popup.destroy()
            self.registrar_no_caixa(val_comissao, val_planos, qtd_planos, data_registro_str)
            
        def cancelar():
            popup.destroy()

        # Botões Lado a Lado
        frame_btns = ttk.Frame(container)
        frame_btns.pack(side='bottom', fill='x', pady=10)
        
        ttk.Button(frame_btns, text="Cancelar", style="danger.Outline.TButton", command=cancelar, width=12).pack(side='left', padx=(0, 5))
        ttk.Button(frame_btns, text="✅ Confirmar", style="success.TButton", command=confirmar).pack(side='right', fill='x', expand=True, padx=(5, 0))

    def registrar_no_caixa(self, valor_pdf, valor_planos, qtd_planos, data_registro_str):
        # 1. PIN
        if not self.pin_verificado_nesta_sessao:
            if not self._verificar_pin_consultor():
                self.app.show_toast("Cancelado", "PIN incorreto.", bootstyle='warning'); return
            self.pin_verificado_nesta_sessao = True
        
        # 2. Salvar
        agora = datetime.now()
        id_unico = agora.strftime("%Y-%m-%d_%H%M%S")
        dt_obj = datetime.strptime(data_registro_str, "%d/%m/%Y")
        mes_ano = dt_obj.strftime("%Y-%m")

        novo = {
            "data": data_registro_str,
            "comissao_produtos": valor_pdf,
            "comissao_planos": valor_planos,
            "qtd_planos": qtd_planos,
            "total_dia": valor_pdf + valor_planos,
            "timestamp": str(agora)
        }
        
        if self.nome_consultor_logado not in self.dados_caixa_comissao: self.dados_caixa_comissao[self.nome_consultor_logado] = {}
        if mes_ano not in self.dados_caixa_comissao[self.nome_consultor_logado]: self.dados_caixa_comissao[self.nome_consultor_logado][mes_ano] = {}
            
        self.dados_caixa_comissao[self.nome_consultor_logado][mes_ano][id_unico] = novo
        
        if fm.salvar_caixa_comissao(self.dados_caixa_comissao):
            self.mostrar_popup_sucesso_bonito(valor_pdf, valor_planos, qtd_planos)
            # Limpa o saldo visualizado ao registrar novo, para forçar re-autenticação se quiser ver atualizado, ou atualiza direto
            # Aqui vamos apenas atualizar internamente, mas manter o estado visual
            if self.saldo_esta_visivel:
                self.consultar_saldo()
        else:
            messagebox.showerror("Erro", "Falha ao salvar.")

    def mostrar_popup_sucesso_bonito(self, v_pdf, v_planos, qtd_planos):
        """Popup de sucesso com tamanho corrigido"""
        popup = Toplevel(self.app)
        popup.title("Sucesso")
        # AUMENTADO A ALTURA PARA 320
        self.app._center_popup(popup, 350, 320) 
        
        ttk.Label(popup, text="✔", font=("Segoe UI", 35), bootstyle="success").pack(pady=(5,0))
        ttk.Label(popup, text="Registrado com Sucesso!", font=("Segoe UI", 12, "bold")).pack(pady=(0,10))

        fr = ttk.Frame(popup, padding=15, bootstyle='light')
        fr.pack(fill='x', padx=20)
        
        def row(l, v):
            f = ttk.Frame(fr, bootstyle='light'); f.pack(fill='x', pady=2)
            ttk.Label(f, text=l, bootstyle='secondary', background='#f8f9fa').pack(side='left')
            ttk.Label(f, text=v, font=("Segoe UI", 9, "bold"), background='#f8f9fa').pack(side='right')

        row("Comissão:", formatar_reais(v_pdf))
        row(f"Planos ({qtd_planos}):", formatar_reais(v_planos))
        ttk.Separator(fr).pack(fill='x', pady=5)
        row("TOTAL:", formatar_reais(v_pdf + v_planos))

        ttk.Button(popup, text="OK", command=popup.destroy, style="success.Outline.TButton").pack(pady=15)

    # --- ABA 2: CONSULTAR SALDO (COM PRIVACIDADE E PDF) ---

    def criar_aba_consultar(self, parent_frame):
        parent_frame.grid_columnconfigure(0, weight=1); parent_frame.grid_rowconfigure(2, weight=1)
        
        # Topo
        frame_saldo = standard_ttk.LabelFrame(parent_frame, text=" Saldo Acumulado ", padding=15)
        frame_saldo.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        self.saldo_label = ttk.Label(frame_saldo, text="R$ ****,**", font=("Segoe UI", 24, "bold"), bootstyle='success')
        self.saldo_label.pack(side='left')
        
        # BOTÃO DE TEXTO NO LUGAR DO ÍCONE
        self.btn_revelar = ttk.Button(frame_saldo, text="👁️ Visualizar Saldo e Extrato", style='light.TButton', command=self.revelar_saldo)
        self.btn_revelar.pack(side='left', padx=15)
        
        # Botão PDF (Novo) - Fica desabilitado até ver o saldo
        self.btn_pdf = ttk.Button(frame_saldo, text="📄 Baixar Holerite (PDF)", style='danger.TButton', command=self.gerar_pdf_holerite, state='disabled')
        self.btn_pdf.pack(side='right', padx=5)

        # Filtros
        frame_filtros = standard_ttk.LabelFrame(parent_frame, text=" Filtros ", padding=10)
        frame_filtros.grid(row=1, column=0, sticky='ew', pady=5)
        
        hoje = date.today()
        primeiro_dia = hoje.replace(day=1)

        ttk.Label(frame_filtros, text="De:").pack(side='left')
        self.filtro_de = DateEntry(frame_filtros, dateformat="%d/%m/%Y", startdate=primeiro_dia)
        self.filtro_de.pack(side='left', padx=5)
        
        ttk.Label(frame_filtros, text="Até:").pack(side='left')
        self.filtro_ate = DateEntry(frame_filtros, dateformat="%d/%m/%Y", startdate=hoje)
        self.filtro_ate.pack(side='left', padx=5)

        ttk.Label(frame_filtros, text="Tipo:").pack(side='left', padx=(10, 5))
        self.filtro_tipo = ttk.Combobox(frame_filtros, values=["Tudo", "Apenas Comissões", "Apenas Planos"], state="readonly", width=18)
        self.filtro_tipo.set("Tudo")
        self.filtro_tipo.pack(side='left')

        ttk.Button(frame_filtros, text="Filtrar", style="primary.Outline.TButton", command=self.consultar_saldo).pack(side='left', padx=15)

        # Tabela
        frame_res = ttk.Frame(parent_frame)
        frame_res.grid(row=2, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(frame_res, orient="vertical"); scroll.pack(side='right', fill='y')
        
        cols = ('data', 'prod', 'plan', 'total')
        self.tree_saldo = ttk.Treeview(frame_res, columns=cols, show='headings', yscrollcommand=scroll.set)
        scroll.config(command=self.tree_saldo.yview)
        
        self.tree_saldo.heading('data', text='Data')
        self.tree_saldo.heading('prod', text='Comissão')
        self.tree_saldo.heading('plan', text='Planos')
        self.tree_saldo.heading('total', text='Total')
        self.tree_saldo.column('data', width=100, anchor='center')
        self.tree_saldo.column('prod', width=100, anchor='e')
        self.tree_saldo.column('plan', width=100, anchor='e')
        self.tree_saldo.column('total', width=100, anchor='e')
        
        self.tree_saldo.pack(side='left', fill='both', expand=True)
        
        # Inicia vazio para privacidade

    def consultar_saldo(self, primeira=False):
        """Preenche a tabela apenas se o saldo estiver visível."""
        
        # Limpa tabela sempre
        for i in self.tree_saldo.get_children(): self.tree_saldo.delete(i)
        
        # SE NÃO TIVER PERMISSÃO VISUAL, SAI DA FUNÇÃO (Proteção do Extrato)
        if not self.saldo_esta_visivel:
            return

        self.saldo_acumulado_mes = 0.00
        self.itens_extrato_atual = [] # Reseta lista para PDF
        
        if not primeira: self.dados_caixa_comissao = fm.carregar_caixa_comissao()
        recs = self.dados_caixa_comissao.get(self.nome_consultor_logado, {})
        
        try:
            d_ini = self.filtro_de.entry.get_date()
            d_fim = self.filtro_ate.entry.get_date()
        except:
            d_ini = date.today().replace(day=1); d_fim = date.today()
        
        tipo = self.filtro_tipo.get()
        total_geral = 0.0
        items = []

        for mes, dados_mes in recs.items():
            for uid, d in dados_mes.items():
                try:
                    dt = datetime.strptime(d['data'], "%d/%m/%Y").date()
                    if d_ini <= dt <= d_fim:
                        items.append((dt, d))
                except: pass
        
        items.sort(key=lambda x: x[0]) # Ordena por data

        for dt, d in items:
            vp = d.get('comissao_produtos', 0)
            vl = d.get('comissao_planos', 0)
            vt = d.get('total_dia', 0)
            qtd_p = d.get('qtd_planos', 0)

            if tipo == "Apenas Comissões": vt = vp; vl = 0
            elif tipo == "Apenas Planos": vt = vl; vp = 0
            
            # Guarda para PDF
            self.itens_extrato_atual.append({
                'data': d['data'], 
                'comissao': vp, 
                'planos_val': vl, 
                'planos_qtd': qtd_p, 
                'total': vt
            })
            
            total_geral += vt
            self.tree_saldo.insert('', 'end', values=(d['data'], formatar_reais(vp), formatar_reais(vl), formatar_reais(vt)))

        self.saldo_acumulado_mes = total_geral
        
        # Atualiza Label e Botão PDF
        if self.saldo_esta_visivel: 
            self.saldo_label.config(text=formatar_reais(total_geral))
            self.btn_pdf.config(state='normal')
        else: 
            self.saldo_label.config(text="R$ ****,**")
            self.btn_pdf.config(state='disabled')

    def revelar_saldo(self):
        if self.saldo_esta_visivel:
            # OCULTAR TUDO
            self.saldo_label.config(text="R$ ****,**")
            self.btn_revelar.config(text="👁️ Visualizar Saldo e Extrato")
            self.btn_pdf.config(state='disabled') # Desabilita PDF
            self.saldo_esta_visivel = False
            # Limpa a tabela imediatamente
            for i in self.tree_saldo.get_children(): self.tree_saldo.delete(i)
        else:
            # MOSTRAR TUDO (Pede senha)
            if not self.pin_verificado_nesta_sessao:
                if not self._verificar_pin_consultor(): return
                self.pin_verificado_nesta_sessao = True
            
            self.saldo_esta_visivel = True
            self.btn_revelar.config(text="🙈 Ocultar Saldo")
            # Carrega os dados
            self.consultar_saldo()
            
    # --- GERADOR DE PDF (HOLERITE) ---
    def gerar_pdf_holerite(self):
        if not self.itens_extrato_atual:
            messagebox.showwarning("Vazio", "Não há dados no período selecionado para gerar o extrato.")
            return

        # Nome do arquivo
        filename_default = f"Extrato_Veritas_{self.nome_consultor_logado}_{date.today().strftime('%d-%m')}.pdf"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Arquivo PDF", "*.pdf")],
            initialfile=filename_default,
            title="Salvar Holerite"
        )
        if not filepath: return

        # Dados do Consultor (Do novo cadastro completo)
        dados_user = self.dados_completos_consultor
        # Tenta pegar o nome completo, se não tiver, usa o login
        nome_completo = dados_user.get('nome_completo', self.nome_consultor_logado).upper()
        cpf = dados_user.get('cpf', 'NÃO INFORMADO')
        
        # Datas
        d_ini = self.filtro_de.entry.get()
        d_fim = self.filtro_ate.entry.get()
        
        try:
            # Configuração da Página
            doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=1*cm, bottomMargin=2*cm)
            elements = []
            styles = getSampleStyleSheet()
            
            # Estilos Personalizados
            style_title = ParagraphStyle('TitleCustom', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER, textColor=HexColor("#2c3e50"), spaceAfter=10)
            style_normal = styles['Normal']
            style_bold = ParagraphStyle('BoldCustom', parent=styles['Normal'], fontName="Helvetica-Bold")
            style_disclaimer = ParagraphStyle('Disc', parent=styles['Normal'], fontSize=8, textColor=HexColor("#c0392b"), alignment=TA_CENTER, spaceBefore=5)
            
            # 1. Logo e Cabeçalho
            logo_path = os.path.join(self.app.DATA_FOLDER_PATH, "logo_completa.png")
            if os.path.exists(logo_path):
                im = PDFImage(logo_path, width=4*cm, height=1.5*cm) 
                im.hAlign = 'LEFT'
                elements.append(im)
            else:
                elements.append(Paragraph("SISTEMA VERITAS", style_title))

            elements.append(Spacer(1, 0.5*cm))
            elements.append(Paragraph("DEMONSTRATIVO DE COMISSÕES E VENDAS (NÃO OFICIAL)", style_title))
            
            # 2. Dados do Colaborador (Tabela para alinhar)
            data_colab = [
                [Paragraph(f"<b>COLABORADOR:</b> {nome_completo}", style_normal), Paragraph(f"<b>CPF:</b> {cpf}", style_normal)],
                [Paragraph(f"<b>PERÍODO:</b> {d_ini} a {d_fim}", style_normal), Paragraph(f"<b>EMISSÃO:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", style_normal)]
            ]
            t_colab = Table(data_colab, colWidths=[10*cm, 8*cm])
            t_colab.setStyle(TableStyle([('LINEBELOW', (0,1), (-1,1), 1, HexColor("#bdc3c7")), ('BOTTOMPADDING', (0,1), (-1,1), 10)]))
            elements.append(t_colab)
            elements.append(Spacer(1, 1*cm))

            # 3. Tabela de Extrato
            data_extrato = [['DATA', 'DESCRIÇÃO / ORIGEM', 'QTD. PLANOS', 'V. PLANOS', 'COMISSÃO', 'TOTAL DO DIA']]
            
            total_comissao = 0
            total_planos_val = 0
            total_planos_qtd = 0
            
            for it in self.itens_extrato_atual:
                row = [
                    it['data'],
                    "Fechamento Diário",
                    str(it['planos_qtd']),
                    formatar_reais(it['planos_val']),
                    formatar_reais(it['comissao']),
                    formatar_reais(it['total'])
                ]
                data_extrato.append(row)
                total_comissao += it['comissao']
                total_planos_val += it['planos_val']
                total_planos_qtd += it['planos_qtd']

            t = Table(data_extrato, colWidths=[2.5*cm, 4*cm, 2.5*cm, 3*cm, 3*cm, 3.5*cm])
            
            # Estilo da Tabela (Zebra)
            style_table = [
                ('BACKGROUND', (0,0), (-1,0), HexColor("#34495e")),
                ('TEXTCOLOR', (0,0), (-1,0), white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('GRID', (0,0), (-1,-1), 0.5, HexColor("#ecf0f1")),
            ]
            for i in range(1, len(data_extrato)):
                bg = white if i % 2 == 0 else HexColor("#f7f9f9")
                style_table.append(('BACKGROUND', (0,i), (-1,i), bg))
            
            t.setStyle(TableStyle(style_table))
            elements.append(t)
            elements.append(Spacer(1, 1*cm))

            # 4. Resumo (Box Final)
            elements.append(Paragraph("RESUMO DO PERÍODO", style_bold))
            
            data_resumo = [
                ["Total Planos Vendidos:", str(total_planos_qtd)],
                ["Valor Total Planos:", formatar_reais(total_planos_val)],
                ["Valor Total Comissões:", formatar_reais(total_comissao)],
                ["TOTAL GERAL (SALDO):", formatar_reais(self.saldo_acumulado_mes)]
            ]
            
            t_res = Table(data_resumo, colWidths=[6*cm, 6*cm], hAlign='RIGHT')
            t_res.setStyle(TableStyle([
                ('LINEABOVE', (0,-1), (-1,-1), 1, black),
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (1,-1), (1,-1), HexColor("#27ae60")), # Verde no total
                ('FONTSIZE', (1,-1), (1,-1), 14)
            ]))
            elements.append(t_res)
            
            elements.append(Spacer(1, 2*cm))

            # 5. Disclaimer Jurídico (Importante!)
            disclaimer_text = """
            <b>AVISO LEGAL IMPORTANTE:</b><br/>
            1. Este documento é gerado pelo sistema "Veritas" para simples conferência e controle pessoal do usuário.<br/>
            2. O Sistema Veritas e seus desenvolvedores <b>NÃO POSSUEM VÍNCULO</b> com a academia Ironberg ou sua administração.<br/>
            3. Este documento <b>NÃO POSSUI VALIDADE JURÍDICA</b> como comprovante de renda, holerite oficial ou extrato bancário.<br/>
            4. Os valores aqui apresentados dependem exclusivamente dos dados inseridos manualmente pelo usuário, podendo conter erros de cálculo ou digitação.<br/>
            """
            
            t_disc = Table([[Paragraph(disclaimer_text, style_disclaimer)]], colWidths=[18*cm])
            t_disc.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 1, HexColor("#e74c3c")),
                ('BACKGROUND', (0,0), (-1,-1), HexColor("#fdedec"))
            ]))
            elements.append(t_disc)

            # Gera
            doc.build(elements)
            self.app.show_toast("Sucesso", f"PDF salvo em:\n{os.path.basename(filepath)}")
            os.startfile(filepath) # Abre o PDF automaticamente

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erro PDF", f"Falha ao gerar PDF: {e}")

    # --- PIN ---
    def _verificar_pin_consultor(self):
        self.dados_pins = fm.carregar_pins_consultores()
        pin_atual = self.dados_pins.get(self.nome_consultor_logado, "0000")
        if pin_atual == "0000": return self._popup_criar_pin()
        pin = self._popup_pedir_pin()
        return pin == pin_atual

    def _popup_criar_pin(self):
        pop = Toplevel(self.app); self.app._center_popup(pop,350,280)
        ttk.Label(pop, text="Crie seu PIN", font=self.app.FONT_BOLD).pack(pady=10)
        p1=StringVar(); p2=StringVar()
        ttk.Entry(pop, textvariable=p1, show="*").pack(); ttk.Entry(pop, textvariable=p2, show="*").pack()
        suc = False
        def sv():
            nonlocal suc
            if len(p1.get())==4 and p1.get()==p2.get():
                self.dados_pins[self.nome_consultor_logado]=p1.get(); fm.salvar_pins_consultores(self.dados_pins); suc=True; pop.destroy()
        ttk.Button(pop, text="Salvar", command=sv).pack()
        self.app.wait_window(pop); return suc

    def _popup_pedir_pin(self):
        pop = Toplevel(self.app); pop.title("PIN"); self.app._center_popup(pop,300,180)
        ttk.Label(pop, text="Digite seu PIN:").pack(pady=10)
        v = StringVar(); e = ttk.Entry(pop, textvariable=v, show="*", font=("Arial",14), width=10); e.pack(pady=5); e.focus()
        r = None
        def ok(): nonlocal r; r=v.get(); pop.destroy()
        ttk.Button(pop, text="OK", command=ok).pack(pady=10); pop.bind("<Return>", lambda e: ok())
        self.app.wait_window(pop); return r