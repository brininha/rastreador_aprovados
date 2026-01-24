import streamlit as st
from streamlit_extras.stylable_container import stylable_container
import rastreador_aprovados as backend

# Inicialização de sessão
if "df_resultado_conferencia" not in st.session_state:
    st.session_state.df_resultado_conferencia = None

if "df_resultado_conversao" not in st.session_state:
    st.session_state.df_resultado_conversao = None

# Funções de Callback
def realiza_conferencia():
    if arquivo_lista_alunos and arquivo_lista_vestibular:
        with st.spinner('Lendo arquivos e cruzando dados... Isso pode levar alguns segundos.'):
            st.session_state.df_resultado_conferencia = backend.processar_conferencia(
                arquivo_lista_alunos,
                arquivo_lista_vestibular,
                st.session_state.opcao == "Nome + CPF"
            )
    else:
        st.error("Por favor, faça o upload dos dois arquivos.")

def converte_para_tabela():
    if arquivo_tabela_pdf:
        st.session_state.df_resultado_conversao = backend.extrair_tabela_pdf(arquivo_tabela_pdf)

# Configuração da Página
st.set_page_config(
    page_title="Rastreador de Aprovados",
    page_icon="🦉",
    layout="centered"
)

# Estilização CSS (Mantida igual ao original para consistência)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
html, body, [data-testid="stAppViewContainer"], .stApp {
  font-family: 'Poppins', sans-serif !important;
  color: #ffffff;
}
.titulo {
  font-weight: 800; font-size: 28px !important; color: #ffffff !important; margin: 0;
}
div.stButton > button {
  background-color: #ef7b17 !important; color: white !important; border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# Cabeçalho
col_img, col_titulo = st.columns([1, 9], vertical_alignment="center")
with col_img:
   st.image("logo.png", width=120)
with col_titulo:   
 st.markdown("<h2 class='titulo'> Rastreador de<br>Aprovados Universal</h2>", unsafe_allow_html=True)

# Abas
tab1, tab2 = st.tabs(["🕵️ Conferência Automática", "🛠️ Ferramentas Extras"])

# --- ABA 1: CONFERÊNCIA ---
with tab1:
    with stylable_container(
        key="meu_card",
        css_styles="{background-color: #15355B; border-radius: 15px; padding: 30px;}"
    ):
        st.markdown('<h3 style="color:white;">Conferência de Listas</h3>', unsafe_allow_html=True)
        st.info("Agora aceita arquivos PDF diretamente! O sistema buscará o nome dos alunos dentro do arquivo PDF da lista oficial.")

        # Opções de Método
        st.radio(
            "Método de Validação:",
            ["Nome completo", "Nome + CPF"],
            horizontal=True,
            key="opcao",
            help="Se escolher Nome + CPF, o sistema procurará o nome do aluno e verificará se o CPF dele está próximo no texto."
        )

        col1, col2 = st.columns(2)

        with col1:
            st.markdown('**1. Alunos do Cursinho**')
            arquivo_lista_alunos = st.file_uploader(
                "Upload Alunos", 
                type=["csv", "xlsx"], 
                key="a1", 
                label_visibility="collapsed"
            )

        with col2:
            st.markdown('**2. Lista Oficial (PDF/Excel)**')
            # ATENÇÃO: Aqui adicionamos "pdf" na lista de tipos aceitos
            arquivo_lista_vestibular = st.file_uploader(
                "Upload Lista Oficial", 
                type=["csv", "xlsx", "pdf", 'txt'], 
                key="a2", 
                label_visibility="collapsed"
            )

        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🔍 Rastrear Aprovados", on_click=realiza_conferencia, use_container_width=True):
            pass

        # Exibição dos Resultados
        if st.session_state.df_resultado_conferencia is not None:
            st.write("### Resultado da Análise:")
            st.dataframe(st.session_state.df_resultado_conferencia, use_container_width=True)

# --- ABA 2: CONVERSOR (Legado/Extra) ---
with tab2:
     with stylable_container(
        key="meu_card2",
        css_styles="{background-color: #15355B; border-radius: 15px; padding: 30px;}"
    ):
        st.markdown('<h3 style="color:white;">Visualizador de Conteúdo PDF</h3>', unsafe_allow_html=True)
        arquivo_tabela_pdf = st.file_uploader("Selecione um PDF para espiar o conteúdo bruto", type=["pdf"], key="conv_pdf")

        if st.button("Extrair Texto", key="btn_tb2", on_click=converte_para_tabela):
            pass
    
        if st.session_state.df_resultado_conversao is not None:
            st.dataframe(st.session_state.df_resultado_conversao)