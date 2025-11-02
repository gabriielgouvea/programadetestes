# Ficheiro: calculadora_core.py
# Contém toda a lógica para ler o PDF, extrair dados e fazer os cálculos.

import pdfplumber
import re

def formatar_valor(valor_str):
    if isinstance(valor_str, str):
        valor_limpo = valor_str.replace("R$", "").strip().replace(".", "").replace(",", ".")
        try:
            return float(valor_limpo)
        except ValueError:
            try:
                valor_limpo_sem_espacos = re.sub(r'\s+', '', valor_limpo)
                return float(valor_limpo_sem_espacos)
            except ValueError:
                return 0.0
    return 0.0

def processar_pdf(caminho_do_arquivo):
    texto_completo = ""
    with pdfplumber.open(caminho_do_arquivo) as pdf:
        for page in pdf.pages:
            texto_da_pagina = page.extract_text(x_tolerance=2, y_tolerance=2)
            if not texto_da_pagina or len(texto_da_pagina) < 50:
                texto_da_pagina = page.extract_text(x_tolerance=2, y_tolerance=2, layout=True)
            if texto_da_pagina:
                texto_completo += texto_da_pagina + "\n"

    if not texto_completo:
        raise ValueError("Não foi possível extrair texto do PDF.")

    valor_total_bruto = 0.0
    info_cabecalho = {"operador": "Não identificado", "periodo": "Não identificado"}
    detalhes_deducoes = {"Adesão de Plano": 0.0, "Taxa de Cancelamento": 0.0, "Taxa de Personal": 0.0, "Recorrência": 0.0, "Aula Avulsa": 0.0, "Crédito em Conta (CCC)": 0.0}
    resumo_vendas = {"DINHEIRO": {'qtd': 0, 'valor': 0.0}, "PIX": {'qtd': 0, 'valor': 0.0}, "CARTÃO DE CRÉDITO": {'qtd': 0, 'valor': 0.0}, "CARTÃO DE DÉBITO": {'qtd': 0, 'valor': 0.0}, "PIX QR CODE": {'qtd': 0, 'valor': 0.0}, "CRÉDITO CONTA CORRENTE(CCC)": {'qtd': 0, 'valor': 0.0}, "total_atendimentos": 0}
    linhas = texto_completo.split('\n')

    # Extrair Cabeçalho
    with pdfplumber.open(caminho_do_arquivo) as pdf:
        if pdf.pages:
            primeira_pagina_texto = pdf.pages[0].extract_text(x_tolerance=2, y_tolerance=2, layout=True)
            if primeira_pagina_texto:
                for linha in primeira_pagina_texto.split('\n'):
                    if "Responsável Recebimento:" in linha:
                        try:
                            nome = linha.split("Responsável Recebimento:")[1].strip()
                            nome = re.sub(r'\s*Consultor Responsável:.*', '', nome).strip()
                            if nome: info_cabecalho["operador"] = nome
                        except IndexError: pass
                    match_periodo = re.search(r'(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})', linha)
                    if match_periodo:
                        info_cabecalho["periodo"] = f"{match_periodo.group(1)} a {match_periodo.group(2)}"

    # Extrair Valor Total
    texto_busca_total = ""
    with pdfplumber.open(caminho_do_arquivo) as pdf:
        paginas_analisar = pdf.pages[max(0, len(pdf.pages)-2):] 
        for page in paginas_analisar:
            texto_pagina = page.extract_text(x_tolerance=2, y_tolerance=2, layout=True)
            if texto_pagina: texto_busca_total += texto_pagina + "\n"
    if texto_busca_total:
        for linha in reversed(texto_busca_total.split('\n')):
            if "Total" in linha and "R$" in linha:
                match = re.findall(r'R\$\s?([\d\.,\s]+)', linha)
                if match:
                    valor_encontrado = formatar_valor(match[-1])
                    if valor_encontrado > 0:
                        valor_total_bruto = valor_encontrado
                        break

    # Extrair Deduções
    for i, linha in enumerate(linhas):
        linha_lower = linha.lower()
        match_valor_final = re.findall(r'([\d\.,]+)', linha)
        valor_linha = formatar_valor(match_valor_final[-1]) if match_valor_final else 0.0
        if "adesão plano recorrente" in linha_lower and valor_linha > 0: detalhes_deducoes["Adesão de Plano"] += valor_linha
        elif "canc. plano" in linha_lower and valor_linha > 0: detalhes_deducoes["Taxa de Cancelamento"] += valor_linha
        elif "taxa personal" in linha_lower and valor_linha > 0: detalhes_deducoes["Taxa de Personal"] += valor_linha
        elif "recorrência" in linha_lower and not any(x in linha_lower for x in ["adesão", "anuidade", "canc."]) and valor_linha > 0: detalhes_deducoes["Recorrência"] += valor_linha
        elif "aula avulsa" in linha_lower:
                for j in range(max(0, i-1), min(i + 3, len(linhas))):
                    if re.search(r'(R\$\s?)?100,00', linhas[j]):
                        detalhes_deducoes["Aula Avulsa"] += 100.0
                        break
        elif "crédito conta corrente(ccc)" in linha_lower and valor_linha > 0 and detalhes_deducoes["Crédito em Conta (CCC)"] == 0:
            detalhes_deducoes["Crédito em Conta (CCC)"] += valor_linha

    # Extrair Resumo de Vendas
    if texto_busca_total:
        mapa_metodos = {r'DINHEIRO':"DINHEIRO", r'PIX\s*$':"PIX", r'CART[AÃ]O DE CR[ÉE]DITO':"CARTÃO DE CRÉDITO", r'CART[AÃ]O DE D[ÉE]BITO':"CARTÃO DE DÉBITO", r'PIX QR CODE':"PIX QR CODE", r'CR[ÉE]DITO CONTA CORRENTE\(CCC\)':"CRÉDITO CONTA CORRENTE(CCC)"}
        padrao_resumo = re.compile(r'^(.*?)\s+Qtd:\s*(\d+)\s+Valor:\s*(R\$\s?)?([\d\.,\s]+)$', re.IGNORECASE | re.MULTILINE)
        matches_resumo = padrao_resumo.findall(texto_busca_total)
        for nome_pdf, qtd_str, _, valor_str in matches_resumo:
            nome_pdf_norm = nome_pdf.strip().upper().replace('É', 'E').replace('Ç', 'C')
            for regex, chave in mapa_metodos.items():
                if re.search(regex, nome_pdf_norm, re.IGNORECASE) and resumo_vendas[chave]['qtd'] == 0:
                    try:
                        resumo_vendas[chave]['qtd'] = int(qtd_str)
                        resumo_vendas[chave]['valor'] = formatar_valor(valor_str)
                    except ValueError: pass
                    break
    resumo_vendas["total_atendimentos"] = sum(d.get('qtd', 0) for k, d in resumo_vendas.items() if k != "total_atendimentos")

    # Cálculo Final
    total_deducoes = sum(detalhes_deducoes.values())
    base_comissionavel = max(0, valor_total_bruto - total_deducoes)
    comissao_final = base_comissionavel * 0.03
    
    return {"valor_total_bruto": valor_total_bruto, "total_deducoes": total_deducoes, "base_comissionavel": base_comissionavel, "comissao_final": comissao_final, "detalhes": detalhes_deducoes, "resumo_vendas": resumo_vendas, "info_cabecalho": info_cabecalho}