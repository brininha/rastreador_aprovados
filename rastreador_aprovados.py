import pandas as pd
import re
import io
import pdfplumber
from rapidfuzz import process, fuzz
from unidecode import unidecode
from pypdf import PdfReader 

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

def obter_fragmentos_cpf(cpf):
    """
    Gera uma lista com as 4 partes do CPF para tentar encontrar
    qualquer uma delas na lista oficial.
    Retorna: [Parte1, Parte2, Parte3, Digitos]
    """
    cpf_limpo = limpar_numeros(cpf)
    
    if len(cpf_limpo) < 11:
        return []
    
    fragmentos = [
        cpf_limpo[0:3],   # 123.***
        cpf_limpo[3:6],   # ***.456.***
        cpf_limpo[6:9],   # ***.***.789
        cpf_limpo[9:11]   # ***-00
    ]
    return fragmentos

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
    
    keywords_nome = ['nome', 'candidato', 'aluno', 'estudante']
    col_nome = next((df.columns[i] for i, c in enumerate(cols_lower) if any(k in c for k in keywords_nome)), None)
    if not col_nome:
        cols_texto = df.select_dtypes(include=['object']).columns
        col_nome = cols_texto[0] if len(cols_texto) > 0 else df.columns[0]

    keywords_doc = ['cpf', 'doc', 'inscrição', 'inscricao', 'rg']
    col_cpf = next((df.columns[i] for i, c in enumerate(cols_lower) if any(k in c for k in keywords_doc)), None)

    return col_nome, col_cpf

# ==========================================
# LÓGICA DE LEITURA DE TEXTO (PDF E TXT)
# ==========================================

def carregar_texto_pdf(arquivo_pdf):
    """Extrai texto do PDF via pdfplumber."""
    texto_completo = ""
    try:
        with pdfplumber.open(arquivo_pdf) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t: texto_completo += " " + t
        return normalizar_texto(texto_completo)
    except:
        return ""

def carregar_texto_txt(arquivo_txt):
    """Lê arquivo TXT tentando UTF-8 e depois Latin-1."""
    try:
        # Tenta UTF-8 (Padrão web/linux)
        conteudo = arquivo_txt.read().decode("utf-8")
    except UnicodeDecodeError:
        # Se falhar, tenta Latin-1 (Comum no Windows antigo/Excel)
        arquivo_txt.seek(0)
        conteudo = arquivo_txt.read().decode("latin-1")
    
    return normalizar_texto(conteudo)

def buscar_em_texto_corrido(df_alunos, texto_norm, col_nome, col_cpf, usar_validacao_cpf):
    """Lógica unificada para qualquer arquivo de texto (PDF ou TXT)"""
    resultados = []
    total_chars = len(texto_norm)

    for idx, row in df_alunos.iterrows():
        nome_original = row[col_nome]
        nome_busca = normalizar_texto(nome_original)
        
        if len(nome_busca) < 4: continue 

        # 1. Busca Exata do Nome
        index_encontrado = texto_norm.find(nome_busca)
        
        match_encontrado = False
        status = ""
        obs = ""
        score = 0

        if index_encontrado != -1:
            match_encontrado = True
            score = 100
            
            # 2. Validação Contextual por CPF
            if usar_validacao_cpf and col_cpf:
                cpf_aluno = row[col_cpf]
                fragmentos = obter_fragmentos_cpf(cpf_aluno)
                
                if fragmentos:
                    # Janela de contexto
                    inicio_ctx = max(0, index_encontrado - 50)
                    fim_ctx = min(total_chars, index_encontrado + len(nome_busca) + 50)
                    contexto = texto_norm[inicio_ctx:fim_ctx]
                    
                    contexto_numerico = re.sub(r'\D', '', contexto)
                    
                    match_cpf = False
                    frag_encontrado = ""
                    
                    for frag in fragmentos:
                        if frag in contexto_numerico:
                            match_cpf = True
                            frag_encontrado = frag
                            break
                    
                    if match_cpf:
                        status = "✅ Aprovado (Confirmado)"
                        obs = f"Nome encontrado e parte do CPF ({frag_encontrado}) identificada próxima."
                    else:
                        status = "⚠️ Verificar (CPF Divergente)"
                        obs = "Nome encontrado, mas nenhum trecho do CPF foi achado por perto."
                else:
                    status = "✅ Aprovado (Nome encontrado)"
                    obs = "CPF do aluno inválido/incompleto, validado apenas por nome."
            else:
                status = "✅ Aprovado (Nome encontrado)"
                obs = "Validação feita apenas por nome."

        if match_encontrado:
            resultados.append({
                "Aluno CPE": nome_original,
                "Nome Detectado": nome_busca,
                "Similaridade": f"{score}%",
                "Status": status,
                "Observação": obs
            })

    if not resultados:
        return pd.DataFrame({"Resultado": ["Nenhum aluno encontrado no arquivo enviado."]})
        
    return pd.DataFrame(resultados).sort_values(by="Status")

# ==========================================
# CONTROLADOR PRINCIPAL
# ==========================================

def processar_conferencia(arquivo_alunos, arquivo_lista, usar_cpf=False):
    # 1. Carregar Alunos
    df_alunos = carregar_dataframe(arquivo_alunos)
    col_nome_aluno, col_cpf_aluno = identificar_colunas(df_alunos)
    
    if not col_nome_aluno:
        return pd.DataFrame({"Erro": ["Não identifiquei a coluna de nomes no arquivo de alunos."]})

    # 2. Verificar tipo da Lista Oficial
    nome_arquivo_lista = arquivo_lista.name.lower()
    
    texto_extraido = None
    
    # ROTA A: Arquivos de Texto (PDF ou TXT)
    if nome_arquivo_lista.endswith('.pdf'):
        texto_extraido = carregar_texto_pdf(arquivo_lista)
    elif nome_arquivo_lista.endswith('.txt'):
        texto_extraido = carregar_texto_txt(arquivo_lista)

    if texto_extraido is not None:
        if not texto_extraido:
            return pd.DataFrame({"Erro": ["Arquivo vazio ou ilegível."]})
        return buscar_em_texto_corrido(df_alunos, texto_extraido, col_nome_aluno, col_cpf_aluno, usar_cpf)

    # ROTA B: Excel/CSV (Tabelas estruturadas)
    else:
        df_oficial = carregar_dataframe(arquivo_lista)
        col_nome_lista, col_cpf_lista = identificar_colunas(df_oficial)
        
        lista_nomes_oficial_norm = [normalizar_texto(x) for x in df_oficial[col_nome_lista].dropna()]
        lista_nomes_oficial_orig = df_oficial[col_nome_lista].dropna().tolist()
        
        resultados = []
        
        for idx, row in df_alunos.iterrows():
            nome_aluno_real = str(row[col_nome_aluno])
            nome_aluno_busca = normalizar_texto(nome_aluno_real)
            if len(nome_aluno_busca) < 4: continue

            match = process.extractOne(nome_aluno_busca, lista_nomes_oficial_norm, scorer=fuzz.token_sort_ratio, score_cutoff=85)

            if match:
                nome_encontrado_norm, score, index_match = match
                nome_encontrado_real = lista_nomes_oficial_orig[index_match]
                
                status = "Em análise"
                adicionar = False
                obs = ""
                
                if usar_cpf and col_cpf_aluno and col_cpf_lista:
                    doc_aluno = limpar_numeros(row[col_cpf_aluno])
                    doc_lista = limpar_numeros(df_oficial.iloc[index_match][col_cpf_lista])
                    
                    fragmentos = obter_fragmentos_cpf(doc_aluno)
                    match_doc = False
                    if fragmentos:
                        for frag in fragmentos:
                            if frag in doc_lista:
                                match_doc = True
                                break
                    
                    if match_doc:
                        status = "✅ Aprovado"
                        obs = "Nome e Documento conferem."
                        adicionar = True
                    else:
                        status = "⚠️ Verificar Homônimo"
                        obs = "Nome bate, mas documento diverge."
                        if score >= 98: adicionar = True
                else:
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

def extrair_tabela_pdf(arquivo_pdf):
    reader = PdfReader(arquivo_pdf)
    dados = []
    for page in reader.pages:
        if page.extract_text():
            dados.append({"Conteúdo Bruto": page.extract_text()[:500] + "..."})
    return pd.DataFrame(dados)