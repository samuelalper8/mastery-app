import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from gtts import gTTS
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÕES E ESTILOS DINÂMICOS (Efeito "Dentro do Cartão")
# ==============================================================================
st.set_page_config(page_title="Samuel's Mastery RPG", page_icon="⚔️", layout="wide")

ARQUIVO_DADOS = "dados_concluidos.txt"
PROGRESS_FILE = "progresso_rpg.json"
INTERVALOS = [1, 3, 7, 15, 30, 60, 90, 180, 365, 540, 730, 1095]
XP_ACERTO, XP_ERRO, XP_BASE_NIVEL = 15, 2, 100

def get_card_style(nivel, revelado):
    cores = {
        "A1": "#dcfce7", "A2": "#f0fdf4",
        "B1": "#fef9c3", "B2": "#ffedd5",
        "C1": "#fee2e2", "C2": "#fecaca"
    }
    bg_color = cores.get(nivel.upper(), "#ffffff")
    
    # Se revelado, a borda fica mais forte para destacar a "virada"
    border_color = "#2563eb" if revelado else "#cbd5e1"
    
    return f"""
    <style>
    .flashcard {{
        background-color: {bg_color}; 
        padding: 40px; 
        border-radius: 25px;
        border: 4px solid {border_color}; 
        text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        min-height: 450px; 
        display: flex; 
        flex-direction: column; 
        justify-content: center; 
        align-items: center; 
        margin: 0 auto 25px auto;
        max-width: 800px;
        transition: all 0.4s ease-in-out;
    }}
    .listening-icon {{ font-size: 100px; color: #3b82f6; }}
    .eng-word {{ color: #0f172a; font-size: 46px; font-weight: 800; line-height: 1.2; }}
    .pt-word {{ color: #1e40af; font-size: 30px; font-weight: 700; margin-top: 10px; border-top: 2px solid rgba(0,0,0,0.1); padding-top: 20px; width: 80%; }}
    .pron {{ color: #475569; font-size: 22px; font-style: italic; background: rgba(255,255,255,0.6); 
             padding: 10px 20px; border-radius: 12px; margin-top: 15px; border: 1px solid rgba(0,0,0,0.1); }}
    .card-meta {{ color: #64748b; font-size: 14px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 20px; }}
    </style>
    """

# ==============================================================================
# 2. LÓGICA DE PERSISTÊNCIA E ÁUDIO
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
# 3. INTERFACE (SIDEBAR E FILTROS)
# ==============================================================================

with st.sidebar:
    st.title("⚔️ Mastery RPG")
    nivel_rpg = (xp_atual // XP_BASE_NIVEL) + 1
    st.metric("Level", nivel_rpg)
    st.progress(min((xp_atual % XP_BASE_NIVEL) / XP_BASE_NIVEL, 1.0))
    
    menu = st.radio("Menu", ["📖 Treinamento", "📊 Estatísticas", "📖 Glossário"])
    
    if menu == "📖 Treinamento":
        st.divider()
        modo_estudo = st.selectbox("Foco:", ["Leitura", "🎧 Escuta"])
        tipo_filtro = st.selectbox("Filtrar por:", ["Tudo (SRS)", "Módulo", "Nível"])
        
        filtro_val = None
        if tipo_filtro == "Módulo":
            filtro_val = st.selectbox("Qual Módulo?", sorted(df['Categoria'].unique()))
        elif tipo_filtro == "Nível":
            filtro_val = st.selectbox("Qual Nível?", ["A1", "A2", "B1", "B2", "C1", "C2"])

# ==============================================================================
# 4. ÁREA DE TREINAMENTO (O CARTÃO)
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
        st.success("✨ Meta batida! Escolha outro módulo.")
    else:
        st.session_state.idx %= len(deck)
        row = deck.iloc[st.session_state.idx]
        
        # Aplicar Estilo Dinâmico (Cor muda conforme nível)
        st.markdown(get_card_style(row['Nível'], st.session_state.revelado), unsafe_allow_html=True)
        
        # O CARTÃO
        st.markdown('<div class="flashcard">', unsafe_allow_html=True)
        
        if modo_estudo == "🎧 Escuta" and not st.session_state.revelado:
            st.markdown('<div class="listening-icon">🔊</div>', unsafe_allow_html=True)
            audio_data = gerar_audio(row['Inglês'])
            if audio_data: st.audio(audio_data, format='audio/mp3', autoplay=True)
        else:
            # Texto aparece "dentro" do cartão
            st.markdown(f'<div class="card-meta">{row["Categoria"]} • {row["Nível"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="eng-word">{row["Inglês"]}</div>', unsafe_allow_html=True)
            
            if st.session_state.revelado:
                st.markdown(f'<div class="pt-word">{row["Tradução"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="pron">🗣️ {row["Pronúncia"]}</div>', unsafe_allow_html=True)
                # No modo leitura, o som toca após revelar
                if modo_estudo == "Leitura":
                    audio_data = gerar_audio(row['Inglês'])
                    if audio_data: st.audio(audio_data, format='audio/mp3', autoplay=True)

        st.markdown('</div>', unsafe_allow_html=True)
        
        # BOTÕES (Aparecem logo abaixo do cartão, de forma fixa)
        if not st.session_state.revelado:
            if st.button("👁️ REVELAR RESPOSTA", use_container_width=True, type="primary"):
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
    st.title("📊 Painel")
    st.write(f"Palavras no deck: {len(df)}")
    st.bar_chart(df['Nível'].value_counts())

elif menu == "📖 Glossário":
    st.title("📖 Biblioteca")
    busca = st.text_input("Buscar...")
    st.dataframe(df[df['Inglês'].str.contains(busca, case=False)], use_container_width=True)
