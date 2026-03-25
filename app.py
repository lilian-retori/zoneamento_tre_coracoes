import streamlit as st
import pandas as pd
from fuzzywuzzy import process

st.set_page_config(page_title="CNAE Três Corações", page_icon="🏛️", layout="wide")

st.markdown("# Consulta Zoneamento")
st.markdown("### Prefeitura Municipal de Três Corações - MG")

st.warning("""
IMPORTANTE: Esta é consulta preliminar. 
Formalize o pedido no setor Minas Fácil (UAI) para confirmar sua consulta.
""")

# SIDEBAR LIMPO
with st.sidebar:
    st.header("Como usar")
    st.markdown("""
    - Rua: 'Renato Azeredo'  
    - CEP: '37415' (parcial)
    - CNAE: '0111' ou 'arroz'
    
    AR = Rural
    """)

@st.cache_data
def carregar_dados():
    df1_raw = pd.read_excel('Estrutura-Detalhada-cnaes.xlsx', sheet_name=0)
    df2_raw = pd.read_excel('Cnaes-com-zoneamento.xlsx', sheet_name=0)
    
    if 'CNAEs' in df2_raw.columns:
        df_cnaes_raw, df_ruas_raw = df2_raw, df1_raw
    else:
        df_cnaes_raw, df_ruas_raw = df1_raw, df2_raw

    df_cnaes = df_cnaes_raw.iloc[:, [0,1,3]].copy()
    df_cnaes.columns = ['CNAEs', 'Denominação', 'Nivel']
    df_cnaes['Nivel'] = pd.to_numeric(df_cnaes['Nivel'], errors='coerce').fillna(5)
    df_cnaes['Rural'] = df_cnaes_raw.iloc[:, 2].astype(str).str.contains('AR', case=False, na=False)
    df_cnaes = df_cnaes.dropna(subset=['CNAEs'])

    df_ruas = df_ruas_raw.copy()
    df_ruas['Nivel_Rua'] = pd.to_numeric(df_ruas.get('Nível', 1), errors='coerce').fillna(1)
    df_ruas['Endereço_Full'] = df_ruas.iloc[:, 0].astype(str) + ' ' + df_ruas.iloc[:, 3].astype(str)
    df_ruas['CEP'] = df_ruas.iloc[:, 5].astype(str)
    df_ruas['Bairro'] = df_ruas.iloc[:, 6].astype(str)
    df_ruas = df_ruas.dropna(subset=['Endereço_Full'])

    return df_cnaes, df_ruas

df_cnaes, df_ruas = carregar_dados()

# INPUTS
col1, col2, col3, col4 = st.columns(4)
with col1:
    opcao = st.selectbox("Tipo:", ["Rua", "CEP", "CNAE"])
with col2:
    consulta = st.text_input("Consulta:", placeholder="Renato Azeredo...")
with col3:
    exato = st.checkbox("Exato")
with col4:
    filtro_cnae = st.text_input("Filtro CNAE:", placeholder="AR/0111")

if consulta:
    if opcao == "Rua":
        if exato:
            filtradas = df_ruas[df_ruas['Endereço_Full'].str.contains(consulta, case=False, na=False)]
        else:
            matches = process.extract(consulta, df_ruas['Endereço_Full'].unique(), limit=5)
            filtradas = df_ruas[df_ruas['Endereço_Full'].isin([m[0] for m in matches if m[1] >= 80])]
        cnaes_base = df_cnaes[df_cnaes['Nivel'] <= int(filtradas['Nivel_Rua'].max())]
        
    elif opcao == "CEP":
        filtradas = df_ruas[df_ruas['CEP'].str.startswith(consulta, na=False)]
        cnaes_base = df_cnaes[df_cnaes['Nivel'] <= int(filtradas['Nivel_Rua'].max())]
        
    else:  # CNAE
        mask_cnae = (df_cnaes['CNAEs'].str.contains(consulta, na=False) | 
                    df_cnaes['Denominação'].str.contains(consulta, case=False, na=False))
        cnaes_base = df_cnaes[mask_cnae]
        nivel_cnae = int(cnaes_base['Nivel'].max())
        filtradas = df_ruas[df_ruas['Nivel_Rua'] >= nivel_cnae]

    # Filtro CNAE
    if filtro_cnae:
        if filtro_cnae == 'AR':
            cnaes_filtrados = cnaes_base[cnaes_base['Rural'] == True]
        else:
            cnaes_filtrados = cnaes_base[
                (cnaes_base['CNAEs'].str.contains(filtro_cnae, na=False) | 
                 cnaes_base['Denominação'].str.contains(filtro_cnae, case=False, na=False))
            ]
    else:
        cnaes_filtrados = cnaes_base

    if 'filtradas' in locals() and not filtradas.empty:
        st.success(f"{len(filtradas)} resultados | Nível {filtradas['Nivel_Rua'].min():.0f}-{filtradas['Nivel_Rua'].max():.0f}")
        
        st.subheader("Logradouros")
        st.dataframe(filtradas[['Endereço_Full', 'Bairro', 'CEP', 'Nivel_Rua']], use_container_width=True, height=300)
        
        st.subheader("CNAEs Permitidos")
        st.dataframe(cnaes_filtrados[['CNAEs', 'Denominação', 'Nivel']], use_container_width=True, height=500)
    else:
        st.warning("Nada encontrado.")

st.markdown("---")
st.caption("Prefeitura Três Corações | LDR")