import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from gtts import gTTS
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÕES, CONSTANTES E ESTILOS (UI/UX)
# ==============================================================================
st.set_page_config(page_title="Samuel's Mastery RPG", page_icon="⚔️", layout="wide")

ARQUIVO_DADOS = "dados_concluidos.txt"
PROGRESS_FILE = "progresso_rpg.json"
INTERVALOS = [1, 3, 7, 15, 30, 60, 90, 180, 365, 540, 730, 1095]
XP_ACERTO, XP_ERRO, XP_MISSAO, XP_BASE_NIVEL = 15, 1, 50, 100

st.markdown("""
    <style>
    .flashcard {
        background: white; padding: 30px; border-radius: 20px;
        border: 2px solid #e2e8f0; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        min-height: 400px; display: flex; flex-direction: column; 
        justify-content: center; align-items: center; position: relative;
    }
    .eng-word { color: #1e293b; font-size: 38px; font-weight: 800; margin-bottom: 10px; line-height: 1.2; }
    .pt-word { color: #2563eb; font-size: 24px; font-weight: 600; margin-top: 15px; }
    .pron { 
        color: #1e293b !important; font-size: 19px; font-weight: 500;
        background: #f1f5f9; padding: 8px 20px; border-radius: 12px;
        margin-top: 10px; display: inline-block; border: 1px solid #e2e8f0;
    }
    .metric-card { background: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; text-align: center; }
    .metric-num { font-size: 24px; font-weight: bold; color: #3b82f6; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. GESTÃO DE DADOS E ÁUDIO
# ==============================================================================

def carregar_progresso():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def salvar_progresso(dados):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4)

def tocar_audio(texto):
    try:
        tts = gTTS(text=texto, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp, format='audio/mp3', autoplay=True)
    except: pass

@st.cache_data(ttl=60)
def load_data():
    all_data = []
    if not os.path.exists(ARQUIVO_DADOS):
        return pd.DataFrame()
    
    with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"): continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3:
                all_data.append({
                    "Inglês": parts[0], "Pronúncia": parts[1], "Tradução": parts[2],
                    "Categoria": parts[3] if len(parts) > 3 else "Geral",
                    "Nível": parts[4] if len(parts) > 4 else "A1"
                })
    return pd.DataFrame(all_data).drop_duplicates()

# ==============================================================================
# 3. ESTADOS DA SESSÃO
# ==============================================================================
if 'xp' not in st.session_state: st.session_state.xp = 0
if 'nivel' not in st.session_state: st.session_state.nivel = 1
if 'missoes_feitas' not in st.session_state: st.session_state.missoes_feitas = []

df = load_data()
progresso_db = carregar_progresso()
hoje = datetime.now().strftime("%Y-%m-%d")

if not df.empty:
    df['Proxima_Revisao'] = df['Inglês'].apply(lambda x: progresso_db.get(x, {}).get('proxima_revisao', '2000-01-01'))
    df['Nivel_SRS'] = df['Inglês'].apply(lambda x: progresso_db.get(x, {}).get('nivel_srs', 0))
    df_rev = df[(df['Proxima_Revisao'] <= hoje) & (df['Categoria'] != 'Missão')].copy()
    df_missoes = df[df['Categoria'] == 'Missão'].copy()
else:
    st.error("Arquivo de dados não encontrado!")
    st.stop()

# ==============================================================================
# 4. SIDEBAR (CONTROLO DE XP)
# ==============================================================================
with st.sidebar:
    st.header(f"🛡️ Nível {st.session_state.nivel}")
    progresso_xp = min((st.session_state.xp % XP_BASE_NIVEL) / XP_BASE_NIVEL, 1.0)
    st.progress(progresso_xp)
    st.caption(f"XP Total: {st.session_state.xp}")
    st.divider()
    
    c1, c2 = st.columns(2)
    c1.metric("🔥 Atrasados", len(df_rev))
    c2.metric("🏆 Master", len(df[df['Nivel_SRS'] >= 10]))
    
    modo = st.radio("Menu Principal", ["🧠 Revisão SRS", "🏋️ Treino por Módulo", "📊 Dashboard", "📜 Missões", "📖 Glossário"])

# ==============================================================================
# 5. FUNCIONALIDADES RESTAURADAS
# ==============================================================================

if modo == "🧠 Revisão SRS":
    st.title("🧠 Revisão Inteligente")
    if df_rev.empty:
        st.success("🎉 Tudo limpo por hoje! Descansa, Guerreiro.")
    else:
        if 'idx_rev' not in st.session_state: st.session_state.idx_rev = 0
        if 'show_ans' not in st.session_state: st.session_state.show_ans = False
        
        row = df_rev.iloc[st.session_state.idx_rev % len(df_rev)]
        
        st.markdown(f"""
            <div class="flashcard">
                <div class="meta-info">{row['Categoria']} • {row['Nível']}</div>
                <div class="eng-word">{row['Inglês']}</div>
                {f'<hr style="width:50%"><div class="pt-word">{row["Tradução"]}</div><div class="pron">🗣️ {row["Pronúncia"]}</div>' if st.session_state.show_ans else '<div style="margin-top:40px; color:#94a3b8;">(Toque em REVELAR)</div>'}
            </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.show_ans:
            tocar_audio(row['Inglês'])
            col_e, col_a = st.columns(2)
            if col_e.button("❌ Esqueci", use_container_width=True):
                progresso_db[row['Inglês']] = {"nivel_srs": 0, "proxima_revisao": hoje}
                salvar_progresso(progresso_db)
                st.session_state.show_ans = False
                st.session_state.idx_rev += 1
                st.rerun()
            if col_a.button("✅ Lembrei", type="primary", use_container_width=True):
                nv = progresso_db.get(row['Inglês'], {}).get('nivel_srs', 0)
                novo_nv = min(nv + 1, len(INTERVALOS) - 1)
                nova_data = (datetime.now() + timedelta(days=INTERVALOS[novo_nv])).strftime("%Y-%m-%d")
                progresso_db[row['Inglês']] = {"nivel_srs": novo_nv, "proxima_revisao": nova_data}
                salvar_progresso(progresso_db)
                st.session_state.xp += XP_ACERTO
                if st.session_state.xp // XP_BASE_NIVEL >= st.session_state.nivel: st.session_state.nivel += 1
                st.session_state.show_ans = False
                st.session_state.idx_rev += 1
                st.rerun()
        else:
            if st.button("👁️ REVELAR RESPOSTA", type="primary", use_container_width=True):
                st.session_state.revelado = True; st.session_state.show_ans = True; st.rerun()

elif modo == "🏋️ Treino por Módulo":
    st.title("🏋️ Treino de Elite")
    cat = st.selectbox("Escolha o Módulo:", sorted(df[df['Categoria'] != 'Missão']['Categoria'].unique()))
    df_t = df[df['Categoria'] == cat].copy()
    
    if 'idx_t' not in st.session_state: st.session_state.idx_t = 0
    row = df_t.iloc[st.session_state.idx_t % len(df_t)]
    
    st.markdown(f'<div class="flashcard" style="border-color:#3b82f6"><div class="eng-word">{row["Inglês"]}</div></div>', unsafe_allow_html=True)
    if st.button("🔊 Tocar Áudio e Próximo"):
        tocar_audio(row['Inglês'])
        st.session_state.idx_t += 1
        st.rerun()

elif modo == "📊 Dashboard":
    st.title("📊 Desempenho")
    col1, col2, col3 = st.columns(3)
    col1.metric("Cartas no Deck", len(df))
    col2.metric("XP Total", st.session_state.xp)
    col3.metric("Nível Atual", st.session_state.nivel)
    st.subheader("Distribuição por Nível de Domínio (SRS)")
    st.bar_chart(df['Nivel_SRS'].value_counts().sort_index())

elif modo == "📜 Missões":
    st.title("📜 Missões Ativas")
    for idx, row in df_missoes.iterrows():
        status = "✅" if row['Inglês'] in st.session_state.missoes_feitas else "⏳"
        with st.container(border=True):
            c1, c2 = st.columns([4,1])
            c1.markdown(f"### {status} {row['Inglês']}")
            c1.write(row['Tradução'])
            if status == "⏳" and c2.button("Completar", key=f"mis_{idx}"):
                st.session_state.missoes_feitas.append(row['Inglês'])
                st.session_state.xp += XP_MISSAO
                st.balloons(); st.rerun()

elif modo == "📖 Glossário":
    st.title("📖 Banco de Conhecimento")
    busca = st.text_input("🔍 Pesquisar em Inglês ou Português:")
    df_view = df[df['Inglês'].str.contains(busca, case=False) | df['Tradução'].str.contains(busca, case=False)]
    st.dataframe(df_view[['Inglês', 'Tradução', 'Pronúncia', 'Categoria', 'Nivel_SRS']], use_container_width=True)
