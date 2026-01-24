import pandas as pd
import re
import io
import pdfplumber
from rapidfuzz import process, fuzz
from unidecode import unidecode
from pypdf import PdfReader # Mantido para funções legadas se necessário

# ==========================================
# FUNÇÕES DE LIMPEZA E UTILITÁRIOS
# ==========================================

def normalizar_texto(texto):
    """Remove acentos, caixa alta e espaços extras."""
    if pd.isna(texto) or texto == "":
        return ""
    texto_limpo = unidecode(str(texto).upper())
    # Substitui quebras de linha por espaço
    texto_limpo = texto_limpo.replace('\n', ' ')
    return re.sub(r'\s+', ' ', texto_limpo).strip()

def limpar_numeros(valor):
    """Deixa apenas números (para CPF/RG)."""
    if pd.isna(valor):
        return ""
    return re.sub(r'\D', '', str(valor))

def extrair_miolo_cpf(cpf):
    """Pega os 6 dígitos centrais do CPF para validação contextual."""
    cpf_limpo = limpar_numeros(cpf)
    if len(cpf_limpo) < 9:
        return None
    # Geralmente listas escondem os 3 primeiros e 2 últimos (***.123.456-**)
    # Pegamos do índice 3 ao 9
    return cpf_limpo[3:9]

def carregar_dataframe(arquivo):
    """Lê CSV ou Excel e retorna DataFrame."""
    nome = arquivo.name.lower()
    if nome.endswith('.csv'):
        try:
            return pd.read_csv(arquivo, dtype=str)
        except:
            arquivo.seek(0)
            return pd.read_csv(arquivo, sep=';', dtype=str)
    else:
        return pd.read_excel(arquivo, dtype=str)

def identificar_colunas(df):
    """Tenta adivinhar colunas de Nome e CPF no DataFrame de alunos."""
    cols_lower = [c.lower() for c in df.columns]
    
    # Busca coluna de NOME
    keywords_nome = ['nome', 'candidato', 'aluno', 'estudante']
    col_nome = next((df.columns[i] for i, c in enumerate(cols_lower) if any(k in c for k in keywords_nome)), None)
    if not col_nome:
        # Pega a primeira coluna de texto se não achar
        cols_texto = df.select_dtypes(include=['object']).columns
        col_nome = cols_texto[0] if len(cols_texto) > 0 else df.columns[0]

    # Busca coluna de CPF/DOC
    keywords_doc = ['cpf', 'doc', 'inscrição', 'inscricao', 'rg']
    col_cpf = next((df.columns[i] for i, c in enumerate(cols_lower) if any(k in c for k in keywords_doc)), None)

    return col_nome, col_cpf

# ==========================================
# LÓGICA NOVA: PROCESSAMENTO DE PDF (TEXTO CORRIDO)
# ==========================================

def carregar_texto_pdf(arquivo_pdf):
    """Extrai todo o texto do PDF como uma única string gigante normalizada."""
    texto_completo = ""
    try:
        # pdfplumber lida bem com file-like objects do Streamlit
        with pdfplumber.open(arquivo_pdf) as pdf:
            for page in pdf.pages:
                texto_pagina = page.extract_text()
                if texto_pagina:
                    texto_completo += " " + texto_pagina
        return normalizar_texto(texto_completo)
    except Exception as e:
        return ""

def buscar_em_texto_corrido(df_alunos, texto_pdf_norm, col_nome, col_cpf, usar_validacao_cpf):
    resultados = []
    
    total_chars = len(texto_pdf_norm)

    for idx, row in df_alunos.iterrows():
        nome_original = row[col_nome]
        nome_busca = normalizar_texto(nome_original)
        
        if len(nome_busca) < 4: continue # Ignora nomes muito curtos

        # 1. Busca Exata (Substring)
        # O PDF é tratado como um textão. Procuramos se "SABRINA CRISTAN" está lá dentro.
        index_encontrado = texto_pdf_norm.find(nome_busca)
        
        match_encontrado = False
        status = ""
        obs = ""
        score = 0

        if index_encontrado != -1:
            match_encontrado = True
            score = 100
            
            # Validação Contextual
            if usar_validacao_cpf and col_cpf:
                cpf_aluno = row[col_cpf]
                miolo_cpf = extrair_miolo_cpf(cpf_aluno)
                
                if miolo_cpf:
                    # Cria uma "janela" de texto ao redor do nome (ex: 60 chars antes e depois)
                    inicio_ctx = max(0, index_encontrado - 60)
                    fim_ctx = min(total_chars, index_encontrado + len(nome_busca) + 60)
                    contexto = texto_pdf_norm[inicio_ctx:fim_ctx]
                    
                    # Limpa o contexto para sobrar só números e ver se o CPF está lá
                    contexto_numerico = re.sub(r'\D', '', contexto)
                    
                    if miolo_cpf in contexto_numerico:
                        status = "✅ Aprovado (Nome + CPF Confirmados)"
                        obs = "Documento encontrado próximo ao nome no PDF."
                    else:
                        status = "⚠️ Verificar (Nome encontrado, CPF não batendo)"
                        obs = f"Nome está na lista, mas o trecho '{miolo_cpf}' do CPF não foi achado perto."
                else:
                    status = "✅ Aprovado (Nome encontrado)"
                    obs = "Aluno sem CPF cadastrado para validação cruzada."
            else:
                status = "✅ Aprovado (Nome encontrado)"
                obs = "Validação feita apenas por nome."

        # Se não achou busca exata, e é só nome, poderíamos tentar fuzzy, 
        # mas em PDF gigante fuzzy é perigoso e lento. Melhor manter busca exata 
        # ou informar que não achou.
        
        if match_encontrado:
            resultados.append({
                "Aluno CPE": nome_original,
                "Nome na Lista (Detectado)": nome_busca, # No PDF não extraímos o nome exato da lista, assumimos o achado
                "Similaridade": f"{score}%",
                "Status": status,
                "Observação": obs
            })

    if not resultados:
        return pd.DataFrame({"Resultado": ["Nenhum aluno encontrado no PDF."]})
        
    return pd.DataFrame(resultados).sort_values(by="Status")

# ==========================================
# CONTROLADOR PRINCIPAL
# ==========================================

def processar_conferencia(arquivo_alunos, arquivo_lista, usar_cpf=False):
    """
    Função inteligente que detecta se a lista oficial é Excel/CSV ou PDF
    e direciona para a lógica correta.
    """
    
    # 1. Carregar Alunos
    df_alunos = carregar_dataframe(arquivo_alunos)
    col_nome_aluno, col_cpf_aluno = identificar_colunas(df_alunos)
    
    if not col_nome_aluno:
        return pd.DataFrame({"Erro": ["Não consegui identificar a coluna de nomes no arquivo de alunos."]})

    # 2. Verificar tipo da Lista Oficial
    nome_arquivo_lista = arquivo_lista.name.lower()
    
    # --- ROTA A: O usuário subiu um PDF (Usa a lógica nova "Bag of Words") ---
    if nome_arquivo_lista.endswith('.pdf'):
        texto_pdf = carregar_texto_pdf(arquivo_lista)
        if not texto_pdf:
            return pd.DataFrame({"Erro": ["Não foi possível ler o texto desse PDF. Ele pode ser uma imagem escaneada."]})
            
        return buscar_em_texto_corrido(df_alunos, texto_pdf, col_nome_aluno, col_cpf_aluno, usar_cpf)

    # --- ROTA B: O usuário subiu Excel/CSV (Usa a lógica antiga de comparação linha a linha) ---
    else:
        df_oficial = carregar_dataframe(arquivo_lista)
        col_nome_lista, col_cpf_lista = identificar_colunas(df_oficial)
        
        # Preparação para fuzzy matching
        lista_nomes_oficial_norm = [normalizar_texto(x) for x in df_oficial[col_nome_lista].dropna()]
        lista_nomes_oficial_orig = df_oficial[col_nome_lista].dropna().tolist()
        
        resultados = []
        
        for idx, row in df_alunos.iterrows():
            nome_aluno_real = str(row[col_nome_aluno])
            nome_aluno_busca = normalizar_texto(nome_aluno_real)
            
            if len(nome_aluno_busca) < 4: continue

            # Busca Fuzzy
            match = process.extractOne(
                nome_aluno_busca, 
                lista_nomes_oficial_norm, 
                scorer=fuzz.token_sort_ratio, 
                score_cutoff=85
            )

            if match:
                nome_encontrado_norm, score, index_match = match
                nome_encontrado_real = lista_nomes_oficial_orig[index_match]
                
                status = "Em análise"
                adicionar = False
                obs = ""
                
                if usar_cpf and col_cpf_aluno and col_cpf_lista:
                    doc_aluno = limpar_numeros(row[col_cpf_aluno])
                    doc_lista = limpar_numeros(df_oficial.iloc[index_match][col_cpf_lista])
                    
                    if doc_aluno and doc_lista and (doc_aluno in doc_lista or doc_lista in doc_aluno):
                        status = "✅ Aprovado"
                        obs = "Nome e Documento conferem."
                        adicionar = True
                    else:
                        status = "⚠️ Verificar Homônimo"
                        obs = "Nome bate, mas documento diverge."
                        # Se similaridade for muito alta, mostra mesmo assim para humano decidir
                        if score >= 98: adicionar = True
                else:
                    # Sem CPF
                    if score >= 95:
                        status = "✅ Aprovado"
                        adicionar = True
                    elif score >= 88:
                        status = "🔍 Verificar grafia"
                        adicionar = True
                
                if adicionar:
                    resultados.append({
                        "Aluno CPE": nome_aluno_real,
                        "Nome na Lista": nome_encontrado_real,
                        "Similaridade": f"{score:.1f}%",
                        "Status": status,
                        "Observação": obs
                    })

        if not resultados:
            return pd.DataFrame({"Resultado": ["Nenhum match encontrado."]})
            
        return pd.DataFrame(resultados).sort_values(by="Status")

# Mantemos a função antiga de extração de tabela apenas para a aba secundária do app, se quiser usar
def extrair_tabela_pdf(arquivo_pdf):
    reader = PdfReader(arquivo_pdf)
    dados = []
    for page in reader.pages:
        if page.extract_text():
            dados.append({"Conteúdo Bruto": page.extract_text()[:500] + "..."})
    return pd.DataFrame(dados)