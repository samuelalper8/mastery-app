import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from gtts import gTTS
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÕES E ESTILOS
# ==============================================================================
st.set_page_config(page_title="Samuel's Mastery RPG", page_icon="⚔️", layout="wide")

ARQUIVO_DADOS = "dados_concluidos.txt"
PROGRESS_FILE = "progresso_rpg.json"
INTERVALOS = [1, 3, 7, 15, 30, 60, 90, 180, 365, 540, 730, 1095]
XP_ACERTO, XP_ERRO, XP_MISSAO, XP_BASE_NIVEL = 15, 2, 50, 100

st.markdown("""
    <style>
    .flashcard {
        background: white; padding: 40px; border-radius: 25px;
        border: 2px solid #e2e8f0; text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        min-height: 400px; display: flex; flex-direction: column; 
        justify-content: center; align-items: center; margin-bottom: 20px;
    }
    .eng-word { color: #0f172a; font-size: 42px; font-weight: 800; margin-bottom: 15px; }
    .pt-word { color: #2563eb; font-size: 26px; font-weight: 600; margin-top: 20px; }
    .pron { color: #475569; font-size: 20px; font-style: italic; background: #f8fafc; padding: 5px 15px; border-radius: 8px; margin-top: 10px; }
    .stProgress > div > div > div > div { background-color: #2563eb; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES DE DADOS E PERSISTÊNCIA
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
                    "Nível": p[4] if len(p)>4 else "A1"
                })
    return pd.DataFrame(itens).drop_duplicates(subset=['Inglês'])

# Inicialização
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
    st.metric("Level", nivel_rpg)
    st.progress(min((xp_atual % XP_BASE_NIVEL) / XP_BASE_NIVEL, 1.0))
    st.caption(f"XP Total: {xp_atual}")
    
    st.divider()
    menu = st.radio("Menu", ["📖 Treinamento", "📊 Estatísticas", "📜 Missões", "📖 Glossário"])
    
    if menu == "📖 Treinamento":
        st.divider()
        st.subheader("🎯 Foco de Estudo")
        tipo_estudo = st.selectbox("Estudar por:", ["Tudo (SRS)", "Módulo Específico", "Nível Específico"])
        
        filtro_final = None
        if tipo_estudo == "Módulo Específico":
            lista_modulos = sorted(df['Categoria'].unique())
            filtro_final = st.selectbox("Selecione o Módulo:", lista_modulos)
        elif tipo_estudo == "Nível Específico":
            lista_niveis = sorted(df['Nível'].unique())
            filtro_final = st.selectbox("Selecione o Nível:", lista_niveis)

# ==============================================================================
# 4. LÓGICA DE FILTRAGEM DE CARTAS
# ==============================================================================

hoje = datetime.now().strftime("%Y-%m-%d")
df['Proxima'] = df['Inglês'].apply(lambda x: progresso_itens.get(x, {}).get('prox', '2000-01-01'))

if menu == "📖 Treinamento":
    if tipo_estudo == "Tudo (SRS)":
        deck_atual = df[df['Proxima'] <= hoje].copy()
    elif tipo_estudo == "Módulo Específico":
        deck_atual = df[df['Categoria'] == filtro_final].copy()
    else: # Nível
        deck_atual = df[df['Nível'] == filtro_final].copy()

# ==============================================================================
# 5. INTERFACE DE TREINAMENTO
# ==============================================================================

if menu == "📖 Treinamento":
    if deck_atual.empty:
        st.success("✨ **Objetivo Concluído!** Não há mais cartas neste filtro para hoje.")
    else:
        st.session_state.idx %= len(deck_atual)
        row = deck_atual.iloc[st.session_state.idx]
        
        st.markdown(f"""
            <div class="flashcard">
                <span style="color:#64748b; font-weight:bold;">{row['Categoria'].upper()} • {row['Nível']}</span>
                <div class="eng-word">{row['Inglês']}</div>
                {"<hr style='width:30%'>" if st.session_state.revelado else ""}
                {f'<div class="pt-word">{row["Tradução"]}</div><div class="pron">🗣️ {row["Pronúncia"]}</div>' if st.session_state.revelado else ""}
            </div>
        """, unsafe_allow_html=True)
        
        if not st.session_state.revelado:
            if st.button("👁️ REVELAR", use_container_width=True, type="primary"):
                st.session_state.revelado = True
                st.rerun()
        else:
            # Áudio
            tts = gTTS(text=row['Inglês'], lang='en')
            audio_fp = BytesIO(); tts.write_to_fp(audio_fp)
            st.audio(audio_fp, format='audio/mp3', autoplay=True)
            
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
    st.title("📊 Seu Progresso Militar")
    col1, col2 = st.columns(2)
    with col1:
        st.write("### Domínio por Nível")
        srs_data = pd.Series([v.get('srs', 0) for v in progresso_itens.values()]).value_counts().sort_index()
        st.bar_chart(srs_data)
    with col2:
        st.write("### Conhecimento por Módulo")
        st.write(df['Categoria'].value_counts())

elif menu == "📜 Missões":
    st.title("📜 Missões Disponíveis")
    df_m = df[df['Categoria'] == 'Missão']
    for i, r in df_m.iterrows():
        with st.expander(f"🚩 {r['Inglês']}"):
            st.write(r['Tradução'])
            if st.button("Completar Missão", key=f"m{i}"):
                st.session_state.data['xp'] += XP_MISSAO
                salvar_progresso(st.session_state.data['xp'], progresso_itens)
                st.balloons()

elif menu == "📖 Glossário":
    st.title("📖 Biblioteca de Termos")
    busca = st.text_input("Pesquisar termo...")
    df_view = df[df['Inglês'].str.contains(busca, case=False) | df['Tradução'].str.contains(busca, case=False)]
    st.dataframe(df_view[['Inglês', 'Tradução', 'Pronúncia', 'Categoria', 'Nível']], use_container_width=True)
