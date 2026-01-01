import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from gtts import gTTS
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÕES E ESTILOS (VISUAL LIMPO E LETRAS CLARAS)
# ==============================================================================
st.set_page_config(page_title="Samuel's Mastery RPG", page_icon="⚔️", layout="wide")

ARQUIVO_DADOS = "dados_concluidos.txt"
PROGRESS_FILE = "progresso_rpg.json"
INTERVALOS = [1, 3, 7, 15, 30, 60, 90, 180, 365, 540, 730, 1095]
XP_ACERTO, XP_ERRO, XP_BASE_NIVEL = 15, 2, 100

def get_text_styles():
    return """
    <style>
    /* Remove containers e foca no texto */
    .main { background-color: transparent; }
    
    .display-area {
        text-align: center;
        padding: 60px 20px;
        max-width: 900px;
        margin: 0 auto;
    }
    
    .meta-text { 
        color: #94a3b8; 
        font-size: 16px; 
        font-weight: 600; 
        letter-spacing: 2px;
        margin-bottom: 10px;
    }
    
    .eng-text { 
        color: #f8fafc; /* Branco Suave */
        font-size: 56px; 
        font-weight: 800; 
        line-height: 1.1;
        margin-bottom: 20px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .pt-text { 
        color: #60a5fa; /* Azul Claro Brilhante */
        font-size: 34px; 
        font-weight: 700;
        margin-top: 20px;
    }
    
    .pron-text { 
        color: #cbd5e1; /* Cinza muito claro */
        font-size: 24px; 
        font-style: italic;
        margin-top: 15px;
        opacity: 0.9;
    }

    .listening-icon { 
        font-size: 120px; 
        color: #60a5fa;
        margin-bottom: 30px;
    }
    </style>
    """

# ==============================================================================
# 2. LÓGICA DE DADOS
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

if 'data' not in st.session_state: st.session_state.data = carregar_progresso()
if 'idx' not in st.session_state: st.session_state.idx = 0
if 'revelado' not in st.session_state: st.session_state.revelado = False

df = load_game_data()
xp_atual = st.session_state.data.get("xp", 0)
progresso_itens = st.session_state.data.get("itens", {})

# ==============================================================================
# 3. SIDEBAR
# ==============================================================================

with st.sidebar:
    st.title("⚔️ Samuel RPG")
    nivel_rpg = (xp_atual // XP_BASE_NIVEL) + 1
    st.metric("Level", nivel_rpg)
    st.progress(min((xp_atual % XP_BASE_NIVEL) / XP_BASE_NIVEL, 1.0))
    
    menu = st.radio("Menu", ["📖 Treino", "📊 Stats", "📖 Glossário"])
    if menu == "📖 Treino":
        modo_estudo = st.selectbox("Modo:", ["Leitura", "🎧 Escuta"])
        tipo_filtro = st.selectbox("Filtro:", ["Tudo (SRS)", "Módulo", "Nível"])
        filtro_val = None
        if tipo_filtro == "Módulo":
            filtro_val = st.selectbox("Selecione:", sorted(df['Categoria'].unique()))
        elif tipo_filtro == "Nível":
            filtro_val = st.selectbox("Selecione:", ["A1", "A2", "B1", "B2", "C1", "C2"])

# ==============================================================================
# 4. ÁREA DE EXPOSIÇÃO (SEM CARTÃO)
# ==============================================================================

st.markdown(get_text_styles(), unsafe_allow_html=True)
hoje = datetime.now().strftime("%Y-%m-%d")
df['Proxima'] = df['Inglês'].apply(lambda x: progresso_itens.get(x, {}).get('prox', '2000-01-01'))

if menu == "📖 Treino":
    if tipo_filtro == "Tudo (SRS)":
        deck = df[df['Proxima'] <= hoje].copy()
    elif tipo_filtro == "Módulo":
        deck = df[df['Categoria'] == filtro_val].copy()
    else:
        deck = df[df['Nível'] == filtro_val].copy()

    if deck.empty:
        st.info("Nenhuma palavra pendente aqui. Tente outro filtro!")
    else:
        st.session_state.idx %= len(deck)
        row = deck.iloc[st.session_state.idx]
        
        # Início da Área de Texto
        st.markdown('<div class="display-area">', unsafe_allow_html=True)
        
        if modo_estudo == "🎧 Escuta" and not st.session_state.revelado:
            st.markdown('<div class="listening-icon">🔊</div>', unsafe_allow_html=True)
            audio_data = gerar_audio(row['Inglês'])
            if audio_data: st.audio(audio_data, format='audio/mp3', autoplay=True)
        else:
            # Informações flutuando
            st.markdown(f'<div class="meta-text">{row["Categoria"]} • Nível {row["Nível"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="eng-text">{row["Inglês"]}</div>', unsafe_allow_html=True)
            
            if st.session_state.revelado:
                st.markdown(f'<div class="pt-text">{row["Tradução"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="pron-text">🗣️ {row["Pronúncia"]}</div>', unsafe_allow_html=True)
                
                if modo_estudo == "Leitura":
                    audio_data = gerar_audio(row['Inglês'])
                    if audio_data: st.audio(audio_data, format='audio/mp3', autoplay=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Botões de Ação Centralizados
        bc1, bc2, bc3 = st.columns([1,2,1])
        with bc2:
            if not st.session_state.revelado:
                if st.button("REVELAR", use_container_width=True, type="primary"):
                    st.session_state.revelado = True
                    st.rerun()
            else:
                c1, c2, c3 = st.columns(3)
                if c1.button("❌", help="Errei"):
                    progresso_itens[row['Inglês']] = {"srs": 0, "prox": hoje}
                    salvar_progresso(xp_atual + XP_ERRO, progresso_itens)
                    st.session_state.revelado = False; st.session_state.idx += 1; st.rerun()
                if c2.button("⏭️", help="Pular"):
                    st.session_state.revelado = False; st.session_state.idx += 1; st.rerun()
                if c3.button("✅", help="Acertei", type="primary"):
                    srs = progresso_itens.get(row['Inglês'], {}).get('srs', 0)
                    novo_srs = min(srs + 1, len(INTERVALOS) - 1)
                    prox_data = (datetime.now() + timedelta(days=INTERVALOS[novo_srs])).strftime("%Y-%m-%d")
                    progresso_itens[row['Inglês']] = {"srs": novo_srs, "prox": prox_data}
                    salvar_progresso(xp_atual + XP_ACERTO, progresso_itens)
                    st.session_state.revelado = False; st.session_state.idx += 1; st.rerun()

elif menu == "📊 Stats":
    st.title("📊 Painel")
    st.write(f"Palavras em estudo: {len(progresso_itens)}")
    st.bar_chart(df['Nível'].value_counts())

elif menu == "📖 Glossário":
    st.title("📖 Glossário")
    busca = st.text_input("Filtrar...")
    st.dataframe(df[df['Inglês'].str.contains(busca, case=False)], use_container_width=True)
