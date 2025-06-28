import streamlit as st
import requests
import re
import json
import webbrowser

# --- Configuração da Página do Streamlit ---
st.set_page_config(
    page_title="Diagnóstico de Anúncios Mercado Livre",
    page_icon="🩺",
    layout="wide"
)

# --- Estilos CSS Customizados ---
st.markdown("""
<style>
    .stApp {
        background-color: #f5f5f5;
    }
    h1, h2, h3 {
        color: #333;
    }
    .st-emotion-cache-1y4p8pa { /* Main container padding */
        padding-top: 2rem;
    }
    .st-emotion-cache-1v0mbdj.e115fcil1 { /* Card-like containers */
        padding: 1.5rem;
        background-color: #ffffff;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton>button {
        width: 100%;
        background-color: #3483fa;
        color: white;
        border-radius: 0.5rem;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #2968c8;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- Funções de Análise e Extração ---

def extract_item_id(input_str):
    """Extrai o ID do item de uma URL do Mercado Livre ou de um código direto."""
    match = re.search(r'(MLB-?\d+)', input_str, re.IGNORECASE)
    if match:
        return match.group(1).replace('-', '')
    return None

def gerar_diagnostico(item_data, seller_data):
    """Gera um diagnóstico completo e um painel de ações sugeridas."""
    diagnosticos = []
    acoes = []

    # PILAR 1: ANÁLISE DE EXPERIÊNCIA DE COMPRA (PREDITIVO)
    if seller_data and seller_data.get('seller_reputation'):
        reputation = seller_data['seller_reputation']
        if reputation.get('metrics'):
            metrics = reputation['metrics']
            claims_rate = metrics.get('claims', {}).get('rate', 0)
            if claims_rate > 0.02:
                rate_str = f"{claims_rate * 100:.2f}%"
                diagnosticos.append(f"**Infração Inferida: Experiência de Compra Ruim.** A taxa de reclamações do vendedor está em **{rate_str}**, acima do limite aceitável. Este é o motivo mais provável para a perda de visibilidade do anúncio.")
                acoes.append("Acesse a seção 'Vendas' e filtre por 'Reclamações' para entender o padrão e corrija a causa raiz (descrição, fotos, embalagem).")

    # PILAR 2: QUALIDADE DO ANÚNCIO
    health_score = item_data.get('health', 0) * 100
    if health_score < 100:
        diagnosticos.append(f"**Qualidade da Ficha Técnica Incompleta ({health_score:.0f}%):** Anúncios com 100% da ficha técnica têm prioridade nos resultados de busca.")
        acoes.append("Acesse a edição do anúncio e preencha todos os campos da ficha técnica que estiverem em branco.")
        
    return diagnosticos, acoes

def build_consolidated_json(item_data, seller_data, diagnosticos):
    """Constrói um JSON consolidado com os dados mais relevantes."""
    inferred_infractions = []
    if diagnosticos:
        for diag in diagnosticos:
            clean_diag = re.sub(r'\*\*|`', '', diag)
            inferred_infractions.append({
                "type": "INFERRED_VIOLATION",
                "reason": clean_diag,
                "remedy": "Verificar o plano de ação sugerido para a correção."
            })

    consolidated_data = {
        "id": item_data.get('id'),
        "title": item_data.get('title'),
        "link": item_data.get('permalink'),
        "price": item_data.get('price'),
        "status": item_data.get('status'),
        "health": item_data.get('health'),
        "sold_quantity": item_data.get('sold_quantity'),
        "tags": item_data.get('tags'),
        "seller_details": {
            "id": seller_data.get('id'),
            "nickname": seller_data.get('nickname'),
            "reputation": seller_data.get('seller_reputation')
        },
        "inferred_infractions": inferred_infractions if inferred_infractions else "Nenhuma infração crítica inferida."
    }
    return consolidated_data

# --- Gerenciamento de Estado da Sessão ---
if 'auth_required' not in st.session_state:
    st.session_state.auth_required = False
if 'config' not in st.session_state:
    st.session_state.config = {
        "CLIENT_ID": "", "CLIENT_SECRET": "", "REDIRECT_URI": "https://google.com",
        "ACCESS_TOKEN": "", "REFRESH_TOKEN": ""
    }

# --- Interface do Streamlit ---

st.title("🩺 Diagnóstico de Anúncios Mercado Livre")
st.write("Cole o link do anúncio para uma análise preditiva de qualidade e um plano de ação.")

# Mostra a sidebar de autenticação apenas se for necessário
if st.session_state.auth_required:
    with st.sidebar:
        st.header("⚙️ Autenticação Necessária")
        st.error("O acesso público foi bloqueado pela API. Por favor, autentique-se para continuar.")
        
        config = st.session_state.config
        config['CLIENT_ID'] = st.text_input("Client ID", value=config.get('CLIENT_ID', ''))
        config['CLIENT_SECRET'] = st.text_input("Client Secret", value=config.get('CLIENT_SECRET', ''), type="password")
        
        if st.button("Salvar Credenciais"):
            st.session_state.config = config
            st.success("Credenciais salvas na sessão atual!")

        st.header("🔑 Gerar Token")
        if st.button("1. Gerar Código de Autorização", help="Abre uma nova aba para você autorizar o aplicativo."):
            if config.get('CLIENT_ID'):
                url = f"https://auth.mercadolivre.com.br/authorization?response_type=code&client_id={config['CLIENT_ID']}&redirect_uri={config.get('REDIRECT_URI', 'https://google.com')}&scope=read%20write%20offline_access"
                js = f"window.open('{url}', '_blank');"
                html = f'<script>{js}</script>'
                st.components.v1.html(html)
            else:
                st.error("Por favor, insira e salve seu Client ID primeiro.")
        
        auth_code = st.text_input("Cole o Código de Autorização (TG-...)")

        if st.button("2. Gerar Access Token"):
            if auth_code:
                url = "https://api.mercadolibre.com/oauth/token"
                payload = {
                    'grant_type': 'authorization_code', 'client_id': config['CLIENT_ID'], 'client_secret': config['CLIENT_SECRET'],
                    'code': auth_code, 'redirect_uri': config.get('REDIRECT_URI', 'https://google.com')
                }
                response = requests.post(url, data=payload)
                if response.ok:
                    tokens = response.json()
                    config['ACCESS_TOKEN'] = tokens['access_token']
                    config['REFRESH_TOKEN'] = tokens['refresh_token']
                    st.session_state.config = config
                    st.success("Token gerado! Tente analisar novamente.")
                    st.rerun()
                else:
                    st.error(f"Erro ao gerar token: {response.json().get('message', 'Erro desconhecido')}")
            else:
                st.warning("Por favor, insira o Código de Autorização.")

input_text = st.text_input("Cole o Link do Anúncio ou o Código (ex: MLB1234567890)", key="url_input")

if st.button("Realizar Diagnóstico", type="primary"):
    item_id = extract_item_id(input_text)
    if not item_id:
        st.warning("URL ou código inválido.")
    else:
        with st.spinner("Realizando diagnóstico..."):
            headers = {}
            # Se a autenticação for necessária e tivermos um token, usamos
            if st.session_state.auth_required and st.session_state.config.get('ACCESS_TOKEN'):
                headers = {'Authorization': f'Bearer {st.session_state.config.get("ACCESS_TOKEN")}'}
            elif st.session_state.auth_required:
                st.error("A autenticação é necessária. Por favor, gere um token na barra lateral e tente novamente.")
                st.stop()

            base_url = "https://api.mercadolibre.com"
            try:
                # 1. Obter dados do anúncio
                item_url = f"{base_url}/items/{item_id}"
                item_response = requests.get(item_url, headers=headers)
                item_response.raise_for_status()
                item_data = item_response.json()

                # 2. Obter dados do vendedor
                seller_id = item_data.get('seller_id')
                seller_url = f"{base_url}/users/{seller_id}"
                seller_response = requests.get(seller_url, headers=headers) # Seller data também pode precisar de auth
                seller_data = seller_response.json() if seller_response.ok else {}
                
                # 3. Gerar diagnóstico e JSON consolidado
                diagnosticos, acoes = gerar_diagnostico(item_data, seller_data)
                consolidated_json = build_consolidated_json(item_data, seller_data, diagnosticos)

                st.markdown("---")
                
                # 4. Exibir o diagnóstico e plano de ação
                if diagnosticos:
                    st.error("🔥 Diagnóstico de Problemas e Infrações Potenciais")
                    for diag in diagnosticos:
                        st.markdown(f"- {diag}")
                    st.success("📋 Plano de Ação Sugerido")
                    for acao in acoes:
                        st.markdown(f"1. **{acao}**")
                else:
                    st.success("✅ Diagnóstico Positivo!")
                    st.balloons()
                    st.markdown("Nenhum problema crítico foi inferido a partir dos dados públicos disponíveis.")
                
                # 5. Exibir o JSON Consolidado
                st.markdown("---")
                st.subheader("📄 Visão Consolidada em JSON (Diagnóstico Completo)")
                st.json(consolidated_json)

            except requests.exceptions.HTTPError as err:
                if err.response.status_code in [401, 403]:
                    st.session_state.auth_required = True
                    st.error("O acesso público foi bloqueado pela API. A barra de autenticação foi ativada na lateral. Por favor, autentique-se e tente novamente.")
                    st.rerun()
                else:
                    st.error(f"Erro ao buscar dados do anúncio: {err.response.status_code} - Verifique o código do anúncio.")
            except Exception as e:
                st.error(f"Ocorreu um erro inesperado: {e}")
