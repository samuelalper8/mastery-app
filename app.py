import streamlit as st
import pandas as pd
import glob
import os
from gtts import gTTS
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Samuel's Mastery Pro", 
    page_icon="🎓", 
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_PATH = os.path.dirname(os.path.abspath(__file__))

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .flashcard {
        background: white; padding: 40px; border-radius: 20px;
        border: 2px solid #e2e8f0; text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        min-height: 350px; display: flex; flex-direction: column; justify-content: center;
        align-items: center;
    }
    .eng-word { color: #0f172a; font-size: 42px; font-weight: 800; margin-bottom: 10px; line-height: 1.2; }
    .pt-word { color: #2563eb; font-size: 28px; font-weight: 600; margin-top: 15px; }
    .pron { color: #64748b; font-family: monospace; font-size: 18px; background: #f1f5f9; padding: 5px 15px; border-radius: 8px; display: inline-block; margin-top: 10px; border: 1px solid #cbd5e1; }
    .meta { font-size: 12px; font-weight: bold; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 20px; }
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MOTOR DE LEITURA
# ==============================================================================
@st.cache_data(ttl=60)
def load_data():
    all_data = []
    target_file = os.path.join(DATA_PATH, "dados_concluidos.txt")
    
    if os.path.exists(target_file):
        files = [target_file]
    else:
        files = glob.glob(os.path.join(DATA_PATH, "*.txt"))

    for file in files:
        fname = os.path.basename(file)
        if fname.endswith(".py") or fname.startswith("."): continue # Ignora script e arquivos ocultos

        try:
            with open(file, 'r', encoding='utf-8') as f: lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith("//"): continue
                parts = [p.strip() for p in line.split('|')]
                
                if len(parts) >= 3:
                    item = {
                        "Inglês": parts[0],
                        "Pronúncia": parts[1] if len(parts) > 1 else "-",
                        "Tradução": parts[2] if len(parts) > 2 else "-",
                        "Categoria": parts[3] if len(parts) > 3 else "Geral",
                        "Nível": parts[4] if len(parts) > 4 else "Geral",
                    }
                    all_data.append(item)
        except Exception as e:
            continue

    if not all_data:
        return pd.DataFrame(columns=["Inglês", "Pronúncia", "Tradução", "Categoria", "Nível"])

    return pd.DataFrame(all_data).drop_duplicates(subset=['Inglês'])

df = load_data()

# ==============================================================================
# 3. INTERFACE
# ==============================================================================
st.sidebar.title("🎓 Samuel's Mastery")

if df.empty:
    st.error("⚠️ Nenhum dado encontrado!")
    st.info(f"Coloque o arquivo 'dados_concluidos.txt' na pasta:\n`{DATA_PATH}`")
    if st.button("Tentar Novamente"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

# Métricas
total = len(df)
st.sidebar.metric("Total de Expressões", total)
nivel_predominante = df['Nível'].mode()[0] if not df.empty else "-"
st.sidebar.info(f"Nível Predominante: **{nivel_predominante}**")

menu = st.sidebar.radio("Modo de Estudo", ["🗂️ Flashcards", "📖 Dicionário", "📊 Estatísticas"])

if menu == "🗂️ Flashcards":
    st.title("🗂️ Treino Focado")
    
    cats = ["Todas"] + sorted([x for x in df["Categoria"].unique() if x and x != "Geral"])
    lvls = ["Todos"] + sorted([x for x in df["Nível"].unique() if x and x != "Geral"])
    
    c1, c2 = st.columns(2)
    sel_cat = c1.selectbox("Categoria", cats)
    sel_lvl = c2.selectbox("Nível", lvls)
    
    f_df = df.copy()
    if sel_cat != "Todas": f_df = f_df[f_df["Categoria"] == sel_cat]
    if sel_lvl != "Todos": f_df = f_df[f_df["Nível"] == sel_lvl]
    
    if not f_df.empty:
        if 'idx' not in st.session_state: st.session_state.idx = 0
        if 'show' not in st.session_state: st.session_state.show = False
        
        if st.session_state.idx >= len(f_df): st.session_state.idx = 0
        row = f_df.iloc[st.session_state.idx]
        
        # --- CARTÃO ---
        st.markdown(f"""
        <div class="flashcard">
            <div class="meta">{row['Categoria']} • {row['Nível']}</div>
            <div class="eng-word">{row['Inglês']}</div>
            {f'<hr style="width:50%; margin: 20px 0;"><div class="pt-word">{row["Tradução"]}</div><div class="pron">🗣️ {row["Pronúncia"]}</div>' 
              if st.session_state.show else 
              '<div style="margin-top:40px; color:#94a3b8; font-style:italic; cursor:pointer;">(Clique em VER RESPOSTA)</div>'}
        </div>
        """, unsafe_allow_html=True)
        
        # --- ÁUDIO E CONTROLES ---
        col_audio, col_btns = st.columns([1, 2])
        
        with col_audio:
            # Botão de áudio só aparece quando a resposta é revelada ou sempre? 
            # Coloquei para aparecer sempre para ajudar na pronúncia antes de ver a tradução.
            if st.button("🔊 Ouvir Pronúncia"):
                try:
                    sound = BytesIO()
                    tts = gTTS(text=row['Inglês'], lang='en')
                    tts.write_to_fp(sound)
                    st.audio(sound, format='audio/mp3', start_time=0)
                except:
                    st.error("Erro ao gerar áudio (verifique a internet).")

        with col_btns:
            c_prev, c_show, c_next = st.columns([1, 2, 1])
            with c_prev:
                if st.button("⬅️"):
                    st.session_state.idx = (st.session_state.idx - 1) % len(f_df)
                    st.session_state.show = False
                    st.rerun()
            with c_show:
                if st.button("👁️ VER / ESCONDER", type="primary"):
                    st.session_state.show = not st.session_state.show
                    st.rerun()
            with c_next:
                if st.button("➡️"):
                    st.session_state.idx = (st.session_state.idx + 1) % len(f_df)
                    st.session_state.show = False
                    st.rerun()
        
        st.caption(f"Card {st.session_state.idx + 1} de {len(f_df)}")
        
    else:
        st.warning("Nenhuma palavra encontrada.")

elif menu == "📖 Dicionário":
    st.title("📖 Glossário")
    search = st.text_input("🔍 Pesquisar...")
    if search:
        mask = df["Inglês"].str.contains(search, case=False, na=False) | df["Tradução"].str.contains(search, case=False, na=False)
        st.dataframe(df[mask], use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

elif menu == "📊 Estatísticas":
    st.title("📊 Raio-X")
    c1, c2 = st.columns(2)
    with c1: st.bar_chart(df["Categoria"].value_counts())
    with c2: st.bar_chart(df["Nível"].value_counts())