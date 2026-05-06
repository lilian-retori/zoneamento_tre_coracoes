# Zoneamento e CNAE – Três Corações (MG)

Aplicação web construída em **Python + Streamlit** para consulta de **viabilidade comercial e de serviços** com base no **zoneamento urbano de Três Corações – MG**.  
O sistema cruza **CNAEs**, **endereços (ruas/CEPs)** e **camadas geográficas** para indicar se uma atividade é potencialmente permitida em determinado local, exibindo o resultado em tabela e em um **mapa interativo**.  

> ⚠️ **Aviso importante:** a ferramenta é uma **consulta preliminar**, sem validade jurídica. A confirmação da viabilidade deve ser feita via Sala Mineira (UAI), conforme avisos já presentes na interface.

---

## Funcionalidades principais

- **Busca por Rua, CEP ou CNAE**  
  - Entrada via texto: rua (com busca aproximada/fuzzy), CEP ou código/descrição de CNAE.  
  - Opção de **busca exata** para ruas.  

- **Cruzamento com nível de atividade**  
  - Cada CNAE possui um **nível**.  
  - Cada logradouro possui um **nível de rua**.  
  - Apenas CNAEs compatíveis com o nível daquela via são considerados “permitidos”.

- **Mapa interativo de zoneamento**  
  - Exibição da rua pesquisada com destaque em vermelho.  
  - Integração com arquivos geográficos (`ruas_trescoracoes.geojson` e `zoneamento.gpkg`).  
  - Uso de **Folium** e **streamlit-folium** para renderização no navegador.  

- **Relatório em HTML/PDF**  
  - Geração de um relatório com:
    - Endereços/CEPs encontrados.  
    - Lista de CNAEs permitidos/compatíveis.  
    

---

## Arquitetura e tecnologias

- **Linguagem:** Python  
- **Framework web:** [Streamlit](https://streamlit.io/)  
- **Geoprocessamento:**
  - [GeoPandas](https://geopandas.org/)  
  - [Folium](https://python-visualization.github.io/folium/)  
  - [streamlit-folium](https://github.com/randyzwitch/streamlit-folium)  

- **Dados tabulares:**
  - [Pandas](https://pandas.pydata.org/)

- **Busca aproximada (fuzzy):**
  - [rapidfuzz](https://github.com/maxbachmann/RapidFuzz) (preferencial)  
  - Fallback para `fuzzywuzzy` ou `difflib` se não instalados.



