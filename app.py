import streamlit as st

from streamlit_extras.stylable_container import stylable_container

import rastreador_aprovados as backend

if "df_resultado_conferencia" not in st.session_state:
    st.session_state.df_resultado_conferencia = None

if "df_resultado_conversao" not in st.session_state:
    st.session_state.df_resultado_conversao = None

def realiza_conferencia():
   st.session_state.df_resultado_conferencia = backend.processar_conferencia(
        arquivo_lista_alunos,
        arquivo_lista_vestibular,
        st.session_state.opcao == "Nome + CPF"
    )

def converte_para_tabela():
   st.session_state.df_resultado_conversao = backend.extrair_tabela_pdf(arquivo_tabela_pdf)

st.set_page_config(
    page_title="Rastreador de Aprovados",
    page_icon="🦉",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');

/* Aplicar fonte e tamanho base */
html, body, [data-testid="stAppViewContainer"], .stApp {
  font-family: 'Poppins', sans-serif !important;
  font-size: 18px !important;
  color: #ffffff;
}

/* Título principal */
.titulo {
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.1;
  font-size: 28px !important;
  color: #ffffff !important;
  margin: 0;
}

/* Rótulo do radio */
div[data-testid="stRadio"] > label {
  font-size: 18px !important;
  color: #ffffff !important;
  margin-bottom: 6px;
}

/* Opções do radio */
div[data-testid="stRadio"] div[role="radiogroup"] label p {
  font-size: 15px !important;
  color: #ffffff !important;
}

/* Estilo do uploader */
[data-testid='stFileUploaderDropzone'] {
  min-height: 100px !important;
  margin: 0 auto !important;
  width: 90% !important;
  background-color: rgba(239, 123, 23, 0.12) !important;
  border: 2px dashed rgba(239, 123, 23, 0.45) !important;
  border-radius: 8px !important;
  position: relative !important;
  transition: all 0.2s ease-in-out !important;
}

/* Hover no uploader */
[data-testid='stFileUploaderDropzone']:hover {
  background-color: rgba(239, 123, 23, 0.18) !important;
  border-color: #ef7b17 !important;
}

/* Mantém acessível, mas esconde a UI interna padrão */
[data-testid='stFileUploaderDropzone'] > div:first-child,
[data-testid='stFileUploaderDropzone'] span,
[data-testid='stFileUploaderDropzone'] small,
[data-testid='stFileUploaderDropzone'] svg {
  visibility: hidden !important;
}

/* Texto centralizado customizado no uploader */
[data-testid='stFileUploaderDropzone']::after {
  content: "Solte o arquivo aqui ou clique para selecionar";
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  font-weight: 600;
  font-size: 14px;
  color: #ffffff;
  width: 80%;
  pointer-events: none;
  white-space: pre-wrap;
  opacity: 0.95;
}

/* Botões */
div.stButton > button {
  background-color: #ef7b17 !important;
  color: white !important;
  border: 1px solid #ef7b17 !important;
  font-weight: 700 !important;
  border-radius: 8px !important;
  padding: 8px 16px !important;
}
div.stButton > button:hover {
  background-color: #d6690f !important;
  border-color: #d6690f !important;
}
div.stButton > button:focus {
  box-shadow: none !important;
}

/* Tabelas / DataFrames */
.stDataFrame, .stTable td, .stTable th {
  font-size: 15px !important;
  color: #ffffff !important;
}

/* Garante contraste do texto dentro dos cards */
[data-testid="stBlock"] * {
  color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

#-------------------------------------------------------------------------------


col_img, col_titulo = st.columns([1, 9], vertical_alignment="center")

with col_img:
   st.image("logo.png", width=120)
with col_titulo:   
 st.markdown(
    "<h2 class='titulo'> Rastreador de<br>Aprovados </h2>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Conferência", "Conversor PDF"])

with tab1:

    with stylable_container(
        key="meu_card",
        css_styles="""
            {
                background-color: #15355B; 
                border-radius: 15px;
                padding: 50px;
                box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
            }
        """
    ):
        
        
        st.markdown('<h2 style="color:white; padding:0; font-size: 25px; text-align: left;   margin-left: 20px !important;">Conferência de listas</h2>', unsafe_allow_html=True)

# ---------------
        st.markdown('<div style="margin-top: -30px;"></div>', unsafe_allow_html=True) 
# -----------------------

        st.radio(
    "Método:",
    ["Nome completo", "Nome + CPF"],
    horizontal=True,
    key="opcao",
)

        col1, col2 = st.columns(2)

        with col1:
    
         st.markdown('<h2 style="color:white; padding:5px; font-size: 15px; text-align: center;  ">🧑‍🏫 Lista de alunos</h2>', unsafe_allow_html=True)
         arquivo_lista_alunos = st.file_uploader("Arquivo 1", type=["csv", "xlsx"], key="a1", label_visibility="collapsed")

        with col2:
         st.markdown('<h2 style="color:white; padding:5px; font-size: 15px; text-align: center;  ">📑 Lista do vestibular</h2>', unsafe_allow_html=True)
         arquivo_lista_vestibular = st.file_uploader("Arquivo 2", type=["csv", "xlsx"], key="a2", label_visibility="collapsed")
    

         col_vazia, col_botao = st.columns([2, 1])
         with col_botao:
          st.button("Buscar", on_click=realiza_conferencia)

        df_bottom_conferencia = st.empty()
        if st.session_state.df_resultado_conferencia is not None:
            df_bottom_conferencia.dataframe(st.session_state.df_resultado_conferencia)



with tab2:
     with stylable_container(
        key="meu_card2",
        css_styles="""
            {
                background-color: #15355B;
                border-radius: 15px;
                padding: 50px;
                box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
            }
        """
    ):
        
        st.markdown('<h2 style="color:white; padding:0; font-size: 25px; text-align: left; ">Extrator de tabelas em arquivos PDF<br></h2>', unsafe_allow_html=True)
        st.markdown('<h7 style="color:white; padding:0; font-size: 15px; text-align: left; margin-top: 10px; ">Use isso para converter listas de aprovados que estão no formato PDF.<br> O sistema tentará criar um arquivo organizado no formato padrão do Excel.</h7>', unsafe_allow_html=True)

        st.markdown('<h2 style="color:white; padding:5px; font-size: 15px; text-align: center;  ">🗂️</h2>', unsafe_allow_html=True)
        arquivo_tabela_pdf = st.file_uploader("PDF", type=["pdf"],  label_visibility="collapsed", key="conv_pdf")

        col_vazia2, col_botao2 = st.columns([2, 1])
        with col_botao2:
         st.button("Converter para tabela", key= "btn_tb2", on_click=converte_para_tabela)
    
        df_bottom_conversao = st.empty()
        if st.session_state.df_resultado_conversao is not None:
            df_bottom_conversao.dataframe(st.session_state.df_resultado_conversao)