import streamlit as st
import pandas as pd
import unicodedata
import os
import base64
from datetime import datetime as _dt

try:
    import geopandas as gpd
    import folium
    from streamlit_folium import st_folium
    GEO_OK = True
except ImportError:
    GEO_OK = False

try:
    from rapidfuzz import process as fuzz_process
    FUZZ_OK = True
except ImportError:
    try:
        from fuzzywuzzy import process as fuzz_process
        FUZZ_OK = True
    except ImportError:
        import difflib
        FUZZ_OK = False

st.set_page_config(
    page_title="Zoneamento e CNAE - Três Corações",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ====================== CSS ======================
CSS = """
<style>
@import url('https://api.fontshare.com/v2/css?f[]=satoshi@400,500,600,700&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
.main .block-container { padding-top: 0rem !important; padding-left: 0rem !important; padding-right: 0rem !important; max-width: 100% !important; }
.custom-header { background: linear-gradient(135deg, #1a3a5c 0%, #2c5aa0 100%); padding: 22px 40px; display: flex; align-items: center; gap: 18px; box-shadow: 0 4px 24px rgba(26,58,92,0.18); }
.custom-header img { height: 56px; border-radius: 6px; }
.custom-header-text h1 { font-family: Satoshi, Inter, sans-serif; font-size: 1.4rem; font-weight: 700; color: #fff; margin: 0; line-height: 1.2; }
.custom-header-text p { font-family: Satoshi, Inter, sans-serif; font-size: 0.82rem; color: #c2d4e8; margin: 3px 0 0 0; }
.aviso-box { background: #fffbf0; border-left: 5px solid #f0a500; padding: 14px 20px; margin: 16px 40px 0 40px; border-radius: 0 8px 8px 0; font-family: Satoshi, Inter, sans-serif; font-size: 0.9rem; color: #5c4a1a; }
.metric-card { flex: 1; background: linear-gradient(135deg, #f0f7ff 0%, #e8f3ff 100%); border: 1.5px solid #c8dff5; border-radius: 12px; padding: 20px 24px; text-align: center; box-shadow: 0 2px 8px rgba(26,58,92,0.06); }
.metric-number { font-size: 2.4rem; font-weight: 700; color: #1a3a5c; display: block; }
.metric-label { font-size: 0.72rem; font-weight: 600; color: #5c6b7a; text-transform: uppercase; letter-spacing: 1px; }
.custom-footer { margin-top: 40px; padding: 20px 40px; border-top: 1px solid #eaeef2; font-size: 0.78rem; color: #8a9ab0; text-align: center; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ====================== CONSTANTES ======================
PREFIXOS = {'AVENIDA','AV','RUA','R','PRACA','PCA','TRAVESSA','TV','ALAMEDA','AL','RODOVIA','ROD','ESTRADA','EST','VIELA','BECO','LARGO','LGO','VIA','VIADUTO'}

CORES_ZONA = {
    'zona_central': '#4db6c4',
    'zona_urbana_industrial': '#566573',
    'zona_adensamento_2': '#e8a090',
    'zona_baixa_densidade': '#a0785a',
    'zona_expansao_urbana': '#e67e22',
    'zeis': '#5e2a7a',
    'mini_distrito': '#f1c40f',           # Distrito Industrial - amarelo
    'areas_especiais_de_conservacao_ambiental': '#27ae60',
    'zona_especial_interesse_institucional': '#c8b4d8',
    'zona_de_especial_interesse_institucional_2': '#d7a3c8',
    'zona_adensamento1': '#f1948a',
    'perimetro_proposto_ibam': '#d35400',
    'tres_coracoes': '#f8f4eb',           # fundo claro da cidade
    'default': '#bdc3c7',
}

LEGENDA_ZONAS = {
    'zona_central': ('#4db6c4', 'Zona Central'),
    'zona_urbana_industrial': ('#566573', 'Mini Distrito'),
    'zona_adensamento1': ('#f1948a', 'Zona de Adensamento 1'),
    'zona_adensamento_2': ('#e8a090', 'Zona de Adensamento 2'),
    'zona_baixa_densidade': ('#a0785a', 'Zona de Baixa Densidade'),
    'zona_expansao_urbana': ('#e67e22', 'Zona de Expansão Urbana'),
    'zona_especial_interesse_institucional': ('#c8b4d8', 'Zona Esp. Interesse Institucional 1'),
    'zona_de_especial_interesse_institucional_2': ('#d7a3c8', 'Zona Esp. Interesse Institucional 2'),
    'zeis': ('#5e2a7a', 'ZEIS - Especial Interesse Social'),
    'mini_distrito': ('#f1c40f', 'Distrito Industrial'),
    'areas_especiais_de_conservacao_ambiental': ('#27ae60', 'Áreas Especiais de Conservação Ambiental'),
    'perimetro_proposto_ibam': ('#d35400', 'Zona de Expansão Urbana'),
    'tres_coracoes': ('#f8f4eb', 'Três Corações'),
}

URL_ABERTURA = "https://docs.google.com/forms/d/e/1FAIpQLScw50OCPy57Lgz0jX_CP-M8G2SaDKXWE5WF9pw1716SFuU-sw/viewform"

# ====================== HELPERS ======================
def normalizar(texto):
    if pd.isna(texto): return ""
    texto = str(texto).upper()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto

def remover_prefixo(texto):
    partes = texto.strip().split()
    if partes and partes[0] in PREFIXOS:
        return " ".join(partes[1:])
    return texto

def busca_fuzzy(query, universe, threshold=75, limit=8):
    if FUZZ_OK:
        resultados = fuzz_process.extract(query, universe, limit=limit)
        return [r[0] for r in resultados if r[1] >= threshold]
    else:
        return difflib.get_close_matches(query, universe, n=limit, cutoff=threshold / 100)

# ====================== CARREGAMENTO ======================
@st.cache_data(show_spinner="Carregando dados...")
def carregar_dados():
    erros = []
    df_cnaes_raw, df_ruas_raw = None, None
    for nome in ("Cnaes-com-zoneamento.xlsx", "base_dados.xlsx"):
        if os.path.exists(nome):
            try:
                raw = pd.read_excel(nome, sheet_name=0, dtype=str)
                if "CNAEs" in raw.columns or "CNAE" in raw.columns.str.upper().tolist():
                    df_cnaes_raw = raw
                else:
                    df_ruas_raw = raw
            except Exception as e:
                erros.append(f"Erro ao ler {nome}: {e}")
    for nome in ("Estrutura-Detalhada-cnaes.xlsx",):
        if os.path.exists(nome):
            try:
                raw = pd.read_excel(nome, sheet_name=0, dtype=str)
                if df_ruas_raw is None:
                    df_ruas_raw = raw
                if df_cnaes_raw is None:
                    df_cnaes_raw = raw
            except Exception as e:
                erros.append(f"Erro ao ler {nome}: {e}")

    df_cnaes = pd.DataFrame()
    df_ruas = pd.DataFrame()

    if df_cnaes_raw is not None:
        try:
            df_cnaes = df_cnaes_raw.iloc[:, [0, 1, 3]].copy()
            df_cnaes.columns = ["CNAEs", "Denominacao", "Nivel"]
            df_cnaes["Nivel"] = pd.to_numeric(df_cnaes["Nivel"], errors="coerce").fillna(5)
            df_cnaes["Rural"] = df_cnaes_raw.iloc[:, 2].astype(str).str.contains("AR", case=False, na=False)
            df_cnaes = df_cnaes.dropna(subset=["CNAEs"]).reset_index(drop=True)
            df_cnaes["CNAE_norm"] = df_cnaes["CNAEs"].apply(normalizar)
            df_cnaes["Denom_norm"] = df_cnaes["Denominacao"].apply(normalizar)
        except Exception as e:
            erros.append(f"Falha ao processar CNAEs: {e}")
    else:
        erros.append("Arquivo de CNAEs nao encontrado (Cnaes-com-zoneamento.xlsx).")

    if df_ruas_raw is not None:
        try:
            df_ruas = df_ruas_raw.copy()
            col_nivel = None
            for _c in df_ruas.columns:
                if normalizar(_c) in ("NIVEL", "NIVEL_RUA", "NIVEL RUA"):
                    col_nivel = _c
                    break
            if col_nivel:
                df_ruas["Nivel_Rua"] = pd.to_numeric(df_ruas[col_nivel], errors="coerce")
            else:
                df_ruas["Nivel_Rua"] = float("nan")
            df_ruas["Endereco_Full"] = df_ruas.iloc[:, 0].astype(str) + " " + df_ruas.iloc[:, 3].astype(str)
            df_ruas["CEP"] = df_ruas.iloc[:, 5].astype(str)
            df_ruas["Bairro"] = df_ruas.iloc[:, 6].astype(str)
            df_ruas["Endereco_norm"] = df_ruas["Endereco_Full"].apply(normalizar)
            df_ruas["Endereco_sem_prefixo"] = df_ruas["Endereco_norm"].apply(remover_prefixo)
            df_ruas["CEP_norm"] = df_ruas["CEP"].apply(normalizar)
            df_ruas["Bairro_norm"] = df_ruas["Bairro"].apply(normalizar)
            df_ruas = df_ruas.dropna(subset=["Endereco_Full"]).reset_index(drop=True)
        except Exception as e:
            erros.append(f"Falha ao processar Ruas: {e}")
    else:
        erros.append("Arquivo de logradouros nao encontrado.")

    return df_cnaes, df_ruas, erros

@st.cache_data(show_spinner="Carregando geometrias...")
def carregar_geo():
    if not GEO_OK:
        return None, None, ["Bibliotecas geoespaciais nao instaladas."]
    erros = []
    gdf_ruas, gdf_zonas = None, None

    if os.path.exists("ruas_trescoracoes.geojson"):
        try:
            gdf_ruas = gpd.read_file("ruas_trescoracoes.geojson")
            gdf_ruas["name_norm"] = gdf_ruas["name"].apply(normalizar)
            gdf_ruas["name_sem_prefixo"] = gdf_ruas["name_norm"].apply(remover_prefixo)
            colunas_bairro = [c for c in gdf_ruas.columns if any(k in c.lower() for k in ["bairro", "suburb", "neighbourhood", "district", "quarter"])]
            gdf_ruas["bairro_geo"] = gdf_ruas[colunas_bairro[0]].apply(normalizar) if colunas_bairro else ""
            cols_dt = gdf_ruas.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns
            gdf_ruas = gdf_ruas.drop(columns=cols_dt)
        except Exception as e:
            erros.append(f"Erro ao ler GeoJSON: {e}")
    else:
        erros.append("Arquivo ruas_trescoracoes.geojson nao encontrado.")

    if os.path.exists("zoneamento.gpkg"):
        try:
            gdf_zonas = gpd.read_file("zoneamento.gpkg", layer="hatches")
            if gdf_zonas.crs and gdf_zonas.crs.to_epsg() != 4326:
                gdf_zonas = gdf_zonas.to_crs(epsg=4326)
        except Exception as e:
            erros.append(f"Erro ao ler GPKG: {e}")
    else:
        erros.append("Arquivo zoneamento.gpkg nao encontrado.")

    return gdf_ruas, gdf_zonas, erros

# ====================== LÓGICA DE BUSCA ======================
def buscar_por_rua(consulta, df_ruas, exato):
    consulta_norm = normalizar(consulta)
    consulta_sp = remover_prefixo(consulta_norm)
    if exato:
        mask = df_ruas["Endereco_norm"].str.contains(consulta_norm, na=False)
    else:
        universe = df_ruas["Endereco_sem_prefixo"].unique().tolist()
        escolhidos = busca_fuzzy(consulta_sp, universe, threshold=75)
        mask = df_ruas["Endereco_sem_prefixo"].isin(escolhidos)
    return df_ruas[mask], consulta_sp

def buscar_por_cep(consulta, df_ruas):
    consulta_norm = normalizar(consulta).replace("-", "").replace(".", "").replace(" ", "")
    cep_limpo = df_ruas["CEP_norm"].str.replace("-", "").str.replace(".", "")
    mask = cep_limpo.str.startswith(consulta_norm, na=False)
    if not mask.any():
        mask = cep_limpo.str.contains(consulta_norm, na=False)
    return df_ruas[mask]

def buscar_por_cnae(consulta, df_cnaes, df_ruas):
    consulta_norm = normalizar(consulta)
    mask = (
        df_cnaes["CNAE_norm"].str.contains(consulta_norm, na=False) |
        df_cnaes["Denom_norm"].str.contains(consulta_norm, na=False)
    )
    cnaes_match = df_cnaes[mask]
    if cnaes_match.empty:
        return df_ruas.iloc[0:0], cnaes_match
    nivel_cnae = int(cnaes_match["Nivel"].min())
    tem_nivel_rua = df_ruas["Nivel_Rua"].notna().any()
    if not tem_nivel_rua:
        filtradas = df_ruas.copy()
    else:
        filtradas = df_ruas[df_ruas["Nivel_Rua"] >= nivel_cnae]
    return filtradas, cnaes_match

def filtrar_cnaes(cnaes_base, filtro):
    if not filtro:
        return cnaes_base
    filtro_norm = normalizar(filtro)
    if filtro_norm == "AR":
        return cnaes_base[cnaes_base["Rural"] == True]
    return cnaes_base[
        cnaes_base["CNAE_norm"].str.contains(filtro_norm, na=False) |
        cnaes_base["Denom_norm"].str.contains(filtro_norm, na=False)
    ]

def cnaes_permitidos_por_ruas(filtradas, df_cnaes):
    if filtradas.empty:
        return df_cnaes.iloc[0:0]
    nivel_max_raw = filtradas["Nivel_Rua"].dropna()
    if nivel_max_raw.empty:
        return df_cnaes
    nivel_max = int(nivel_max_raw.max())
    return df_cnaes[df_cnaes["Nivel"] <= nivel_max]

def filtrar_geo_por_cep(gdf_ruas_geo, filtradas):
    colunas_cep = [c for c in gdf_ruas_geo.columns if "cep" in c.lower() or "postal" in c.lower()]
    if colunas_cep:
        ceps_planilha = set(filtradas["CEP"].str.replace(r"[-.]", "", regex=True).str.strip())
        col_cep = colunas_cep[0]
        gdf_ruas_geo = gdf_ruas_geo.copy()
        gdf_ruas_geo["cep_norm"] = gdf_ruas_geo[col_cep].astype(str).str.replace(r"[-.]", "", regex=True).str.strip()
        mask = gdf_ruas_geo["cep_norm"].isin(ceps_planilha)
        if mask.any():
            return mask
    pares = set(zip(filtradas["Endereco_sem_prefixo"], filtradas["Bairro_norm"]))
    nomes = {n for n, _ in pares}
    return gdf_ruas_geo["name_sem_prefixo"].isin(nomes)

_CENTRO_TC = [-21.6950, -45.2550]

def exibir_mapa(gdf_sel, gdf_zonas):
    # Define centro do mapa
    if gdf_sel is not None and not gdf_sel.empty:
        centro_geom = gdf_sel.geometry.unary_union.centroid
        centro = [centro_geom.y, centro_geom.x]
        zoom = 16
    else:
        centro = _CENTRO_TC
        zoom = 14

    m = folium.Map(location=centro, zoom_start=zoom, tiles="CartoDB positron")

    # ==================== APENAS A RUA DESTACADA ====================
    if gdf_sel is not None and not gdf_sel.empty:
        rua_grupo = folium.FeatureGroup(name="Rua pesquisada", show=True)
        folium.GeoJson(
            gdf_sel.to_json(),
            style_function=lambda f: {
                "color": "#e74c3c",      # vermelho forte
                "weight": 8,
                "opacity": 0.95,
                "dashArray": "8, 4"      # linha tracejada
            },
            tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Rua:"])
        ).add_to(rua_grupo)
        rua_grupo.add_to(m)
    else:
        st.caption("ℹ️ Rua não localizada no arquivo geoespacial.")

    folium.LayerControl(collapsed=False).add_to(m)
    st_folium(m, width=None, height=500, returned_objects=[])# ====================== CABEÇALHO ======================
logo_html = ""
if os.path.exists("brasao.png"):
    with open("brasao.png", "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" />'
elif os.path.exists("brasão.png"):
    with open("brasão.png", "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" />'

st.markdown(
    f'<div class="custom-header">{logo_html}'
    f'<div class="custom-header-text">'
    f'<h1> Consulta de Zoneamento e CNAE</h1>'
    f'<p>Prefeitura Municipal de Três Corações - MG | Ferramenta pública para verificar viabilidade de atividades comerciais</p>'
    f'</div></div>',
    unsafe_allow_html=True
)

st.markdown(
    f'<div class="aviso-box">&#9888;&#65039; <strong>IMPORTANTE:</strong> Esta é uma consulta preliminar. '
    f'Formalize o pedido na Sala Mineira (UAI) para confirmar a viabilidade. '
    f'<a href="{URL_ABERTURA}" target="_blank">Abertura de empresas online.</a></div>',
    unsafe_allow_html=True
)

# ====================== CARREGAMENTO ======================
df_cnaes, df_ruas, erros_dados = carregar_dados()
for e in erros_dados:
    st.error(e)

gdf_ruas_geo, gdf_zonas, erros_geo = carregar_geo()

# ====================== ÁREA DE BUSCA ======================
st.markdown('<div class="content-area">', unsafe_allow_html=True)

col_tipo, col_input, col_btn = st.columns([1.5, 4, 1])
with col_tipo:
    opcao = st.selectbox("Tipo de busca", ["Rua", "CEP", "CNAE"], label_visibility="collapsed")
with col_input:
    placeholder_map = {"Rua": "Ex.: Renato Azeredo...", "CEP": "Ex.: 37415...", "CNAE": "Ex.: 4711 ou lanchonete"}
    consulta = st.text_input("Consulta", placeholder=placeholder_map[opcao], label_visibility="collapsed")
with col_btn:
    buscar = st.button("Consultar", type="primary", use_container_width=True)

exato = st.checkbox("Busca exata (sem aproximação)", value=False, disabled=(opcao != "Rua"))

st.markdown("---")

# ====================== EXECUÇÃO DA BUSCA ======================
if buscar and consulta.strip():
    filtradas = None
    cnaes_base = None
    consulta_sp = ""

    with st.spinner("Consultando..."):
        if opcao == "Rua":
            filtradas, consulta_sp = buscar_por_rua(consulta, df_ruas, exato)
            if not filtradas.empty:
                cnaes_base = cnaes_permitidos_por_ruas(filtradas, df_cnaes)
        elif opcao == "CEP":
            filtradas = buscar_por_cep(consulta, df_ruas)
            if not filtradas.empty:
                cnaes_base = cnaes_permitidos_por_ruas(filtradas, df_cnaes)
        else:
            filtradas, cnaes_base = buscar_por_cnae(consulta, df_cnaes, df_ruas)

    st.session_state["resultados"] = {
        "filtradas": filtradas,
        "cnaes_base": cnaes_base,
        "opcao": opcao,
        "consulta": consulta,
        "consulta_sp": consulta_sp,
        "exato": exato
    }

# ====================== EXIBIÇÃO DOS RESULTADOS ======================
if "resultados" in st.session_state:
    res = st.session_state["resultados"]
    filtradas = res["filtradas"]
    cnaes_base = res["cnaes_base"]
    opcao = res["opcao"]
    consulta = res["consulta"]
    consulta_sp = res["consulta_sp"]
    exato = res["exato"]

    if filtradas is not None and not filtradas.empty:
        # Filtro de atividade
        filtro_cnae = st.text_input(
            "🔎 Filtrar atividade nos resultados:",
            placeholder="Ex.: lanchonete, comercio, 4711, AR...",
            key="filtro_atividade"
        )

        cnaes_filtrados = filtrar_cnaes(cnaes_base, filtro_cnae) if filtro_cnae.strip() else cnaes_base

        ceps_unicos = len(filtradas["CEP"].dropna().unique())
        total_cnaes = len(cnaes_filtrados)

        # ==================== CARDS LADO A LADO ====================
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="CEPs encontrados", value=ceps_unicos)
        with col2:
            st.metric(label="CNAEs permitidos", value=total_cnaes)

        # Mapa
        if GEO_OK and gdf_ruas_geo is not None:
            st.subheader(" Mapa de Zoneamento")
            if opcao == "Rua":
                mask_geo = gdf_ruas_geo["name_sem_prefixo"].str.contains(consulta_sp, na=False) if consulta_sp else pd.Series([False]*len(gdf_ruas_geo))
                exibir_mapa(gdf_ruas_geo[mask_geo], gdf_zonas)
            elif opcao == "CEP":
                mask_geo = filtrar_geo_por_cep(gdf_ruas_geo, filtradas)
                exibir_mapa(gdf_ruas_geo[mask_geo], gdf_zonas)
            else:
                exibir_mapa(gdf_ruas_geo.iloc[0:0], gdf_zonas)

        # Resultados
        st.markdown("### Resultados")
        col_log, col_cnae = st.columns(2)

        with col_log:
            st.markdown("**📍 Logradouros**")
            df_log = (
                filtradas[["Endereco_Full", "Bairro", "CEP"]]
                .drop_duplicates()
                .rename(columns={"Endereco_Full": "Endereco"})
                .reset_index(drop=True)
            )
            st.dataframe(df_log, use_container_width=True, height=320)

        with col_cnae:
            if filtro_cnae.strip() and cnaes_filtrados.empty:
                st.markdown("**❌ Atividade NÃO permitida neste endereço**")
                df_cnae_out = pd.DataFrame(columns=["CNAEs", "Denominacao"])
                st.dataframe(df_cnae_out, use_container_width=True, height=100)
            else:
                st.markdown("**✅ CNAEs Permitidos**" if not filtro_cnae.strip() else "**✅ Atividade PERMITIDA**")
                df_cnae_out = (
                    cnaes_filtrados[["CNAEs", "Denominacao"]]
                    .drop_duplicates()
                    .reset_index(drop=True)
                )
                st.dataframe(df_cnae_out, use_container_width=True, height=320)

        # ====================== PDF ======================
        st.markdown("---")
        st.markdown("#### 📄 Exportar Resultado")

        import base64 as _b64

        logo_pdf = ""
        if os.path.exists("brasao.png"):
            with open("brasao.png", "rb") as _f:
                _logo_b64 = _b64.b64encode(_f.read()).decode()
            logo_pdf = f'<img src="data:image/png;base64,{_logo_b64}" style="height:70px;" />'
        elif os.path.exists("brasão.png"):
            with open("brasão.png", "rb") as _f:
                _logo_b64 = _b64.b64encode(_f.read()).decode()
            logo_pdf = f'<img src="data:image/png;base64,{_logo_b64}" style="height:70px;" />'

        linhas_logradouros = "".join(
            f"<tr><td>{r['Endereco']}</td><td>{r['Bairro']}</td><td>{r['CEP']}</td></tr>"
            for _, r in df_log.iterrows()
        )
        linhas_cnaes = "".join(
            f"<tr><td style='font-family:monospace'>{r['CNAEs']}</td><td>{r['Denominacao']}</td></tr>"
            for _, r in df_cnae_out.iterrows()
        )

        html_parts = [
            "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'>",
            "<style>",
            "body{font-family:Arial,sans-serif;font-size:11px;color:#222;margin:40px}",
            ".header{display:flex;align-items:center;gap:18px;border-bottom:3px solid #1a3a5c;padding-bottom:14px;margin-bottom:20px}",
            ".header-text h1{font-size:16px;color:#1a3a5c;margin:0}",
            ".header-text p{font-size:10px;color:#555;margin:3px 0 0 0}",
            ".aviso{background:#fff8e6;border-left:5px solid #f0a500;padding:10px 14px;margin-bottom:20px;font-size:10.5px;color:#5c4a1a;border-radius:0 6px 6px 0}",
            ".aviso strong{color:#1a3a5c}",
            "h2{font-size:12px;color:#1a3a5c;margin:18px 0 6px 0;border-bottom:1px solid #c8dff5;padding-bottom:4px}",
            "table{width:100%;border-collapse:collapse;margin-bottom:20px}",
            "th{background:#1a3a5c;color:white;padding:6px 10px;text-align:left;font-size:10px}",
            "td{padding:5px 10px;border-bottom:1px solid #eee;font-size:10px}",
            "tr:nth-child(even) td{background:#f5f9ff}",
            ".footer{margin-top:30px;border-top:1px solid #ddd;padding-top:10px;font-size:9px;color:#999;text-align:center}",
            ".info{font-size:10px;color:#555;margin-bottom:16px}",
            "</style></head><body>",
            f'<div class="header">{logo_pdf}<div class="header-text"><h1>Consulta de Zoneamento e CNAE</h1>',
            "<p>Prefeitura Municipal de Três Corações - MG | Secretaria de Tributação</p></div></div>",
            '<div class="aviso"><strong>ATENÇÃO - DOCUMENTO INFORMATIVO:</strong> Este relatório é resultado de uma ',
            "<strong>consulta preliminar</strong> e <strong>não possui validade jurídica</strong>. ",
            "Para formalizar o pedido de viabilidade, compareça à <strong>Sala Mineira (UAI)</strong> ",
            "ou acesse o portal <strong>Minas Fácil</strong>. A aprovação final está sujeita a análise técnica da Prefeitura.</div>",
            f'<div class="info"><strong>Consulta realizada em:</strong> {_dt.now().strftime("%d/%m/%Y às %H:%M")}',
            f" &nbsp;|&nbsp; <strong>Tipo:</strong> {opcao} &nbsp;|&nbsp; <strong>Termo:</strong> {consulta}</div>",
            "<h2>Logradouros Encontrados</h2>",
            f"<table><tr><th>Endereço</th><th>Bairro</th><th>CEP</th></tr>{linhas_logradouros}</table>",
            f"<h2>CNAEs Permitidos ({len(df_cnae_out)} atividades)</h2>",
            f"<table><tr><th>CNAE</th><th>Denominação</th></tr>{linhas_cnaes}</table>",
            f'<div class="footer">Prefeitura Municipal de Três Corações | LDR - {_dt.now().year} | Documento informativo - confirmar junto à Sala Mineira (UAI).</div>',
            "</body></html>"
        ]

        html_pdf = "".join(html_parts)
        html_b64 = _b64.b64encode(html_pdf.encode("utf-8")).decode()
        nome_arquivo = f"consulta_zoneamento_{consulta.replace(' ','_')}_{_dt.now().strftime('%Y%m%d_%H%M')}.html"

        st.markdown(
            f'<a href="data:text/html;base64,{html_b64}" download="{nome_arquivo}" '
            f'style="display:inline-block;background:#1a3a5c;color:white;padding:10px 22px;'
            f'border-radius:8px;text-decoration:none;font-weight:600;font-size:0.9rem;">'
            f'⬇️ Baixar Relatório'
            f'</a>'
            f'<p style="font-size:0.78rem;color:#888;margin-top:6px;">'
            f'Após baixar: abra o arquivo no navegador, Ctrl+P e salve como PDF</p>',
            unsafe_allow_html=True,
        )

    else:
        st.warning("Nenhum resultado encontrado. Ajuste o texto ou o tipo de busca.")

st.markdown('</div>', unsafe_allow_html=True)
# Sidebar e rodapé (mantidos)
with st.sidebar:
    st.markdown("### Legenda de Zonas")
    for chave, (cor, label) in LEGENDA_ZONAS.items():
        st.markdown(f'<span style="display:inline-block;width:14px;height:14px;background:{cor};border-radius:3px;margin-right:8px;vertical-align:middle;"></span>{label}', unsafe_allow_html=True)

st.markdown('<div class="custom-footer">Prefeitura Municipal de Três Corações | LDR - 2026</div>', unsafe_allow_html=True)