import streamlit as st
import pandas as pd
from fuzzywuzzy import process
import unicodedata

st.set_page_config(page_title="CNAE Três Corações", page_icon="🏛️", layout="wide")

# ----------------- Header com brasão -----------------
col_logo, col_titulo = st.columns([1,6])
with col_logo:
    # Certifique-se de que o arquivo 'brasão.png' está na mesma pasta do app
    st.image('brasão.png', width=120)
with col_titulo:
    st.markdown("# Consulta Zoneamento")
    st.markdown("### Prefeitura Municipal de Três Corações - MG")

# ----------------- Aviso UAI com link -----------------
st.warning("""
IMPORTANTE: Esta é consulta preliminar. 
Formalize o pedido na Sala Mineira (UAI) para confirmar a viabilidade.

Se preferir fazer **online**, clique no link para abertura de empresas:

**Online:** [Abertura de Empresas](https://docs.google.com/forms/d/e/1FAIpQLScw50OCPy57Lgz0jX_CP-M8G2SaDKXWE5WF9pw1716SFuU-sw/viewform?pli=1)
""")

# ----------------- Funções auxiliares -----------------
def normalizar(texto: str) -> str:
    """Remove acentos, ç, e coloca em maiúsculo (para busca sem case/acento)."""
    if pd.isna(texto):
        return ""
    texto = str(texto).upper()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    return texto.replace("Ç", "C")

# ----------------- Carregamento de dados -----------------
@st.cache_data
def carregar_dados():
    df1_raw = pd.read_excel('Estrutura-Detalhada-cnaes.xlsx', sheet_name=0)
    df2_raw = pd.read_excel('Cnaes-com-zoneamento.xlsx', sheet_name=0)
    
    if 'CNAEs' in df2_raw.columns:
        df_cnaes_raw, df_ruas_raw = df2_raw, df1_raw
    else:
        df_cnaes_raw, df_ruas_raw = df1_raw, df2_raw

    # CNAEs
    df_cnaes = df_cnaes_raw.iloc[:, [0,1,3]].copy()
    df_cnaes.columns = ['CNAEs', 'Denominação', 'Nivel']
    df_cnaes['Nivel'] = pd.to_numeric(df_cnaes['Nivel'], errors='coerce').fillna(5)
    df_cnaes['Rural'] = df_cnaes_raw.iloc[:, 2].astype(str).str.contains('AR', case=False, na=False)
    df_cnaes = df_cnaes.dropna(subset=['CNAEs'])

    # Ruas
    df_ruas = df_ruas_raw.copy()
    df_ruas['Nivel_Rua'] = pd.to_numeric(df_ruas.get('Nível', 1), errors='coerce').fillna(1)
    df_ruas['Endereço_Full'] = df_ruas.iloc[:, 0].astype(str) + ' ' + df_ruas.iloc[:, 3].astype(str)
    df_ruas['CEP'] = df_ruas.iloc[:, 5].astype(str)
    df_ruas['Bairro'] = df_ruas.iloc[:, 6].astype(str)

    # NORMALIZADOS
    df_ruas['Endereco_norm'] = df_ruas['Endereço_Full'].apply(normalizar)
    df_ruas['CEP_norm'] = df_ruas['CEP'].apply(normalizar)
    df_cnaes['CNAE_norm'] = df_cnaes['CNAEs'].apply(normalizar)
    df_cnaes['Denom_norm'] = df_cnaes['Denominação'].apply(normalizar)

    df_ruas = df_ruas.dropna(subset=['Endereço_Full'])

    return df_cnaes, df_ruas

df_cnaes, df_ruas = carregar_dados()

# ----------------- Layout dos inputs -----------------
col_tipo, col_exato, col_vazio = st.columns([2,1,3])
with col_tipo:
    opcao = st.selectbox("Tipo:", ["Rua", "CEP", "CNAE"])
with col_exato:
    exato = st.checkbox("Exato")

col_consulta, col_filtro = st.columns([3,2])
with col_consulta:
    consulta = st.text_input("Nome/número:", placeholder="Renato Azeredo, 37415, 0111...")
with col_filtro:
    filtro_cnae = st.text_input(
        "Filtro CNAE (dentro dos resultados da rua/CEP):",
        placeholder="AR, 0111, comércio...",
    )

# ----------------- Lógica principal -----------------
filtradas = None
cnaes_base = None

if consulta:
    consulta_norm = normalizar(consulta)

    if opcao == "Rua":
        if exato:
            mask = df_ruas['Endereco_norm'].str.contains(consulta_norm, na=False)
            filtradas = df_ruas[mask]
        else:
            universe = df_ruas['Endereco_norm'].unique()
            matches = process.extract(consulta_norm, universe, limit=5)
            escolhidos = [m[0] for m in matches if m[1] >= 80]
            filtradas = df_ruas[df_ruas['Endereco_norm'].isin(escolhidos)]

        if not filtradas.empty:
            nivel_max = int(filtradas['Nivel_Rua'].max())
            cnaes_base = df_cnaes[df_cnaes['Nivel'] <= nivel_max]

    elif opcao == "CEP":
        mask = df_ruas['CEP_norm'].str.startswith(consulta_norm, na=False)
        filtradas = df_ruas[mask]
        if not filtradas.empty:
            nivel_max = int(filtradas['Nivel_Rua'].max())
            cnaes_base = df_cnaes[df_cnaes['Nivel'] <= nivel_max]

    else:  # CNAE
        mask_cnae = (
            df_cnaes['CNAE_norm'].str.contains(consulta_norm, na=False) |
            df_cnaes['Denom_norm'].str.contains(consulta_norm, na=False)
        )
        cnaes_base = df_cnaes[mask_cnae]
        if not cnaes_base.empty:
            nivel_cnae = int(cnaes_base['Nivel'].max())
            filtradas = df_ruas[df_ruas['Nivel_Rua'] >= nivel_cnae]

# ----------------- Filtro CNAE dentro do resultado da rua/CEP -----------------
cnaes_filtrados = None
if cnaes_base is not None:
    if filtro_cnae:
        filtro_norm = normalizar(filtro_cnae)
        if filtro_norm == "AR":
            cnaes_filtrados = cnaes_base[cnaes_base['Rural'] == True]
        else:
            cnaes_filtrados = cnaes_base[
                cnaes_base['CNAE_norm'].str.contains(filtro_norm, na=False) |
                cnaes_base['Denom_norm'].str.contains(filtro_norm, na=False)
            ]
    else:
        cnaes_filtrados = cnaes_base

# ----------------- Saída: limitar para todos os CNAEs -----------------
if consulta and filtradas is not None and not filtradas.empty and cnaes_filtrados is not None:
    # contar CEPs únicos
    ceps_unicos = filtradas['CEP'].dropna().drop_duplicates()
    len_ceps = len(ceps_unicos)

    st.success(
        f"{len_ceps} CEPs encontrados "
        f"e {len(cnaes_filtrados)} CNAEs permitidos."
    )

    st.subheader("Logradouros")
    df_log = filtradas[['Endereço_Full', 'Bairro', 'CEP']].drop_duplicates().reset_index(drop=True)
    st.dataframe(df_log, use_container_width=True, height=300)

    st.subheader("CNAEs Permitidos")
    # agora mostra TODOS os CNAEs permitidos
    df_cnae_out = cnaes_filtrados[['CNAEs', 'Denominação']].drop_duplicates().reset_index(drop=True)
    st.dataframe(df_cnae_out, use_container_width=True, height=500)

elif consulta and (filtradas is None or filtradas.empty):
    st.info("Nenhum resultado encontrado para este tipo de pesquisa. Ajuste o texto ou o tipo e tente novamente.")
else:
    pass

st.markdown("---")
st.caption("Prefeitura Três Corações | LDR")