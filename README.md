# Consulta Zoneamento CNAE - Três Corações

Consulta preliminar de zoneamento e atividades econômicas permitidas por logradouro, CEP ou CNAE na cidade de Três Corações - MG.



## Funcionalidades

- **Busca por Rua**: Logradouros exatos ou aproximados (top 5 melhores matches)
- **Busca por CEP**: Parcial (ex: "37415" retorna todas ruas deste prefixo)
- **Busca por CNAE**: Código ou descrição da atividade (ex: "0111", "comércio")
- **Filtro secundário CNAE**: Refinamento das atividades após busca inicial
- **Filtro AR**: Atividades rurais específicas
- **Informações completas**: Endereço, bairro, CEP, nível de zoneamento

## Pré-requisitos

- Python 3.8+
- Bibliotecas: `streamlit`, `pandas`, `openpyxl`, `fuzzywuzzy`

## Instalação

1. Clone ou baixe este repositório
2. Coloque os arquivos Excel na pasta raiz:
   - `Estrutura-Detalhada-cnaes.xlsx`
   - `Cnaes-com-zoneamento.xlsx`
3. Instale dependências:

```bash
pip install streamlit pandas openpyxl fuzzywuzzy python-levenshtein
```

4. Execute o aplicativo:

```bash
streamlit run app.py
```

## Deploy Streamlit Cloud

1. Crie repositório GitHub público com:
   - `app.py`
   - Arquivos Excel
   - Este `README.md`
2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Conecte GitHub → Deploy automático
4. URL pública disponível em minutos

## Como Usar

### 1. Tipo de Consulta
| Tipo | Exemplo | Resultado |
|------|---------|-----------|
| **Rua** | "Renato Azeredo" | Todas ruas similares + atividades permitidas |
| **CEP** | "37415" | 200+ logradouros deste prefixo |
| **CNAE** | "0111" ou "arroz" | Ruas permitidas para esta atividade |

### 2. Opções
- **Exato ☑️**: Apenas logradouros contendo texto exato
- **Filtro CNAE**: "AR" (rurais) ou código/parcial após busca principal

### 3. Níveis de Zoneamento
| Nível | Tipo |
|-------|------|
| 1 | Residencial |
| 2-3 | Misto |
| 4-5 | Comercial/Industrial |

## Capturas de Tela





## Dados

- **1.332 CNAEs** detalhados com níveis de permissão
- **29.624 logradouros** com CEP, bairro e zoneamento
- **Zoneamento oficial** Três Corações - MG

## Aviso Legal

> **IMPORTANTE**: Esta é consulta preliminar. Formalize o pedido no setor Minas Fácil (UAI) para confirmar sua consulta.

## Contato

Prefeitura Municipal de Três Corações - MG  
Desenvolvido por LDR  
Março 2026

***

<div style="text-align: center; margin-top: 40px;">
    <small>Prefeitura Três Corações | LDR</small>
</div>
