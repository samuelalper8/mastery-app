import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from gtts import gTTS
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÕES E ESTILOS DINÂMICOS
# ==============================================================================
st.set_page_config(page_title="Samuel's Mastery RPG", page_icon="⚔️", layout="wide")

ARQUIVO_DADOS = "dados_concluidos.txt"
PROGRESS_FILE = "progresso_rpg.json"
INTERVALOS = [1, 3, 7, 15, 30, 60, 90, 180, 365, 540, 730, 1095]
XP_ACERTO, XP_ERRO, XP_MISSAO, XP_BASE_NIVEL = 15, 2, 50, 100

# Função para definir a cor do quadro conforme o nível
def get_card_style(nivel):
    cores = {
        "A1": "#dcfce7", "A2": "#f0fdf4", # Verdes
        "B1": "#fef9c3", "B2": "#ffedd5", # Amarelos/Laranjas
        "C1": "#fee2e2", "C2": "#fecaca"  # Vermelhos
    }
    bg_color = cores.get(nivel.upper(), "#ffffff")
    border_color = "#cbd5e1"
    return f"""
    <style>
    .flashcard {{
        background-color: {bg_color}; padding: 40px; border-radius: 25px;
        border: 3px solid {border_color}; text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        min-height: 400px; display: flex; flex-direction: column; 
        justify-content: center; align-items: center; margin-bottom: 20px;
        transition: background-color 0.5s ease;
    }}
    .listening-icon {{ font-size: 80px; color: #3b82f6; margin-bottom: 20px; }}
    .eng-word {{ color: #0f172a; font-size: 42px; font-weight: 800; margin-bottom: 15px; }}
    .pt-word {{ color: #1e40af; font-size: 26px; font-weight: 600; margin-top: 20px; }}
    .pron {{ color: #475569; font-size: 20px; font-style: italic; background: rgba(255,255,255,0.5); 
             padding: 5px 15px; border-radius: 8px; margin-top: 10px; border: 1px solid rgba(0,0,0,0.05); }}
    </style>
    """

# ==============================================================================
# 2. FUNÇÕES DE SUPORTE
# ==============================================================================

def carregar_progresso():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {"xp": 0, "itens": {}}
    return {"xp": 0, "itens": {}}

def salvar_progresso(xp, itens_status):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"xp": xp, "itens": itens_status}, f, indent=4)

def gerar_audio(texto):
    try:
        tts = gTTS(text=texto, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

@st.cache_data
def load_game_data():
    if not os.path.exists(ARQUIVO_DADOS): return pd.DataFrame()
    itens = []
    with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"): continue
            p = [x.strip() for x in line.split('|')]
            if len(p) >= 3:
                itens.append({
                    "Inglês": p[0], "Pronúncia": p[1], "Tradução": p[2], 
                    "Categoria": p[3] if len(p)>3 else "Geral", 
                    "Nível": p[4].upper() if len(p)>4 else "A1"
                })
    return pd.DataFrame(itens).drop_duplicates(subset=['Inglês'])

# Inicialização de Estado
if 'data' not in st.session_state: st.session_state.data = carregar_progresso()
if 'idx' not in st.session_state: st.session_state.idx = 0
if 'revelado' not in st.session_state: st.session_state.revelado = False

df = load_game_data()
xp_atual = st.session_state.data.get("xp", 0)
progresso_itens = st.session_state.data.get("itens", {})

# ==============================================================================
# 3. SIDEBAR (DASHBOARD)
# ==============================================================================

with st.sidebar:
    st.title("⚔️ Samuel's RPG")
    nivel_rpg = (xp_atual // XP_BASE_NIVEL) + 1
    st.metric("Nível de Herói", nivel_rpg)
    st.progress(min((xp_atual % XP_BASE_NIVEL) / XP_BASE_NIVEL, 1.0))
    st.caption(f"XP Total: {xp_atual}")
    
    st.divider()
    menu = st.radio("Menu", ["📖 Treinamento", "📊 Estatísticas", "📖 Glossário"])
    
    if menu == "📖 Treinamento":
        st.subheader("🎯 Filtros de Missão")
        modo_estudo = st.selectbox("Modo de Foco:", ["Leitura (Tradicional)", "🎧 Escuta (Listening First)"])
        tipo_filtro = st.selectbox("Filtrar por:", ["Tudo (SRS)", "Módulo", "Nível"])
        
        filtro_val = None
        if tipo_filtro == "Módulo":
            filtro_val = st.selectbox("Qual Módulo?", sorted(df['Categoria'].unique()))
        elif tipo_filtro == "Nível":
            filtro_val = st.selectbox("Qual Nível?", ["A1", "A2", "B1", "B2", "C1", "C2"])

# ==============================================================================
# 4. LÓGICA DO DECK E INTERFACE
# ==============================================================================

hoje = datetime.now().strftime("%Y-%m-%d")
df['Proxima'] = df['Inglês'].apply(lambda x: progresso_itens.get(x, {}).get('prox', '2000-01-01'))

if menu == "📖 Treinamento":
    if tipo_filtro == "Tudo (SRS)":
        deck = df[df['Proxima'] <= hoje].copy()
    elif tipo_filtro == "Módulo":
        deck = df[df['Categoria'] == filtro_val].copy()
    else:
        deck = df[df['Nível'] == filtro_val].copy()

    if deck.empty:
        st.success("✨ Área limpa! Tenta outro módulo ou nível.")
    else:
        st.session_state.idx %= len(deck)
        row = deck.iloc[st.session_state.idx]
        
        # APLICA O ESTILO DO QUADRO DINAMICAMENTE
        st.markdown(get_card_style(row['Nível']), unsafe_allow_html=True)
        
        st.markdown('<div class="flashcard">', unsafe_allow_html=True)
        
        audio_data = gerar_audio(row['Inglês'])
        
        if modo_estudo == "🎧 Escuta (Listening First)" and not st.session_state.revelado:
            st.markdown('<div class="listening-icon">🔊</div>', unsafe_allow_html=True)
            st.write("### Identifica o som...")
            if audio_data: st.audio(audio_data, format='audio/mp3', autoplay=True)
            if st.button("👂 Ouvir de novo"): st.rerun()
        else:
            st.markdown(f'<span style="color:#64748b; font-weight:bold;">{row["Categoria"].upper()} • {row["Nível"]}</span>', unsafe_allow_html=True)
            st.markdown(f'<div class="eng-word">{row["Inglês"]}</div>', unsafe_allow_html=True)
            
            if st.session_state.revelado:
                st.markdown(f'<hr style="width:30%; opacity:0.2"><div class="pt-word">{row["Tradução"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="pron">🗣️ {row["Pronúncia"]}</div>', unsafe_allow_html=True)
                if modo_estudo == "Leitura (Tradicional)" and audio_data:
                    st.audio(audio_data, format='audio/mp3', autoplay=True)

        st.markdown('</div>', unsafe_allow_html=True)
        
        # Botões de Controle
        if not st.session_state.revelado:
            if st.button("👁️ REVELAR (Espaço)", use_container_width=True, type="primary"):
                st.session_state.revelado = True
                st.rerun()
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("❌ Errei", use_container_width=True):
                    progresso_itens[row['Inglês']] = {"srs": 0, "prox": hoje}
                    salvar_progresso(xp_atual + XP_ERRO, progresso_itens)
                    st.session_state.revelado = False; st.session_state.idx += 1; st.rerun()
            with c2:
                if st.button("⏭️ Pular", use_container_width=True):
                    st.session_state.revelado = False; st.session_state.idx += 1; st.rerun()
            with c3:
                if st.button("✅ Acertei", use_container_width=True, type="primary"):
                    srs = progresso_itens.get(row['Inglês'], {}).get('srs', 0)
                    novo_srs = min(srs + 1, len(INTERVALOS) - 1)
                    prox_data = (datetime.now() + timedelta(days=INTERVALOS[novo_srs])).strftime("%Y-%m-%d")
                    progresso_itens[row['Inglês']] = {"srs": novo_srs, "prox": prox_data}
                    salvar_progresso(xp_atual + XP_ACERTO, progresso_itens)
                    st.session_state.revelado = False; st.session_state.idx += 1; st.rerun()

elif menu == "📊 Estatísticas":
    st.title("📊 Painel de Controle")
    st.write(f"Vocabulário total dominado: **{len(progresso_itens)} palavras**")
    st.bar_chart(df['Nível'].value_counts())
    st.caption("Distribuição de palavras por nível de dificuldade no teu deck.")

elif menu == "📖 Glossário":
    st.title("📖 Biblioteca")
    busca = st.text_input("Procurar palavra...")
    st.dataframe(df[df['Inglês'].str.contains(busca, case=False)], use_container_width=True)
