import streamlit as st
import pandas as pd
import glob
import os
import json
from datetime import datetime, timedelta
from gtts import gTTS
from io import BytesIO
import random

# ==============================================================================
# 1. CONFIGURAÇÕES E CONSTANTES
# ==============================================================================
st.set_page_config(page_title="Samuel's Mastery RPG", page_icon="⚔️", layout="wide")

DATA_PATH = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(DATA_PATH, "progresso.json")

# Ciclo de 3 anos (Curva de Ebbinghaus estendida)
INTERVALOS = [1, 3, 7, 15, 30, 60, 90, 180, 365, 540, 730, 1095]

# Configurações de XP
XP_ACERTO = 15
XP_ERRO = 1 
XP_MISSAO = 50
XP_BASE_NIVEL = 100

st.markdown("""
    <style>
    .flashcard {
        background: white; padding: 30px; border-radius: 20px;
        border: 2px solid #e2e8f0; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        min-height: 400px; display: flex; flex-direction: column; 
        justify-content: center; align-items: center; position: relative;
    }
    .mastered { border: 4px solid #fbbf24 !important; background: #fffbeb !important; }
    .meta-info { font-size: 12px; font-weight: bold; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
    .eng-word { color: #1e293b; font-size: 38px; font-weight: 800; margin-bottom: 10px; line-height: 1.2; }
    .pt-word { color: #2563eb; font-size: 24px; font-weight: 600; margin-top: 15px; margin-bottom: 10px; }
    
    /* CORREÇÃO DA PRONÚNCIA: Fundo cinza suave e texto escuro para legibilidade total */
    .pron { 
        color: #1e293b !important; 
        font-size: 19px; 
        font-weight: 500;
        background: #f1f5f9; 
        padding: 8px 20px; 
        border-radius: 12px;
        margin-top: 10px;
        display: inline-block;
        border: 1px solid #e2e8f0;
    }

    .status-badge { font-size: 11px; padding: 4px 10px; border-radius: 12px; background: #f1f5f9; color: #64748b; margin-bottom: 15px; border: 1px solid #cbd5e1; display: inline-block; }
    .gold-badge { background: #fbbf24; color: #78350f; border:none; font-weight:bold; }
    
    .metric-card { background: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; text-align: center; }
    .metric-num { font-size: 24px; font-weight: bold; color: #3b82f6; }
    .metric-label { font-size: 14px; color: #64748b; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. GERENCIAMENTO DE DADOS
# ==============================================================================

def carregar_progresso():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def salvar_progresso(dados):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4)

def atualizar_revisao(termo_ingles, acertou):
    progresso = carregar_progresso()
    hoje_str = datetime.now().strftime("%Y-%m-%d")
    
    registro = progresso.get(termo_ingles, {"nivel_srs": 0, "proxima_revisao": hoje_str})
    nivel_atual = registro["nivel_srs"]

    if acertou:
        proximo_nivel = min(nivel_atual + 1, len(INTERVALOS) - 1)
        dias_para_add = INTERVALOS[proximo_nivel]
        nova_data = (datetime.now() + timedelta(days=dias_para_add)).strftime("%Y-%m-%d")
        
        progresso[termo_ingles] = {
            "nivel_srs": proximo_nivel,
            "proxima_revisao": nova_data,
            "ultimo_estudo": hoje_str,
            "acertos_consecutivos": registro.get("acertos_consecutivos", 0) + 1
        }
    else:
        progresso[termo_ingles] = {
            "nivel_srs": 0,
            "proxima_revisao": hoje_str, 
            "ultimo_estudo": hoje_str,
            "acertos_consecutivos": 0
        }
    
    salvar_progresso(progresso)
    return dias_para_add if acertou else 0

@st.cache_data(ttl=60)
def load_data():
    all_data = []
    # Busca por arquivos .txt ou dados_concluidos.txt
    target_file = os.path.join(DATA_PATH, "dados_concluidos.txt")
    files = [target_file] if os.path.exists(target_file) else glob.glob(os.path.join(DATA_PATH, "*.txt"))

    for file in files:
        if file.endswith(".py") or "progresso.json" in file: continue
        try:
            with open(file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("//"): continue
                    parts = [p.strip() for p in line.split('|')]
                    
                    if len(parts) >= 3:
                        item = {
                            "Inglês": parts[0],
                            "Pronúncia": parts[1],
                            "Tradução": parts[2],
                            "Categoria": parts[3] if len(parts) > 3 else "Geral",
                            "Nível": parts[4] if len(parts) > 4 else "Geral",
                        }
                        all_data.append(item)
        except: continue
    
    if not all_data: return pd.DataFrame()
    df = pd.DataFrame(all_data).drop_duplicates()
    return df

# Gamification Init
if 'xp' not in st.session_state: st.session_state.xp = 0
if 'nivel' not in st.session_state: st.session_state.nivel = 1
if 'missoes_feitas' not in st.session_state: st.session_state.missoes_feitas = []

def adicionar_xp(qtd):
    st.session_state.xp += qtd
    meta = st.session_state.nivel * XP_BASE_NIVEL
    if st.session_state.xp >= meta:
        st.session_state.nivel += 1
        st.balloons()
        st.toast(f"LEVEL UP! Nível {st.session_state.nivel}!", icon="🎉")

# ==============================================================================
# 3. PREPARAÇÃO DE DADOS
# ==============================================================================
df = load_data()
progresso_db = carregar_progresso()

if not df.empty:
    df['Proxima_Revisao'] = df['Inglês'].apply(lambda x: progresso_db.get(x, {}).get('proxima_revisao', '2000-01-01'))
    df['Nivel_SRS'] = df['Inglês'].apply(lambda x: progresso_db.get(x, {}).get('nivel_srs', 0))
    
    hoje = datetime.now().strftime("%Y-%m-%d")
    df_revisao = df[ (df['Proxima_Revisao'] <= hoje) & (df['Categoria'] != 'Missão') ].copy()
    df_futuro = df[ (df['Proxima_Revisao'] > hoje) & (df['Categoria'] != 'Missão') ].copy()
    df_missoes = df[df['Categoria'] == 'Missão'].copy()
else:
    df_revisao, df_futuro, df_missoes = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ==============================================================================
# 4. SIDEBAR
# ==============================================================================
with st.sidebar:
    st.header(f"🛡️ Nível {st.session_state.nivel}")
    progresso_xp = min(st.session_state.xp / (st.session_state.nivel * XP_BASE_NIVEL), 1.0)
    st.progress(progresso_xp)
    st.caption(f"XP Total: {st.session_state.xp}")
    
    st.divider()
    
    c1, c2 = st.columns(2)
    c1.metric("🔥 Atrasados", len(df_revisao))
    c2.metric("💤 Futuro", len(df_futuro))

    st.divider()
    modo = st.radio("Menu Principal", ["🧠 Revisão Diária (SRS)", "🏋️ Treino por Módulo", "📊 Dashboard", "📜 Missões", "📖 Banco de Dados"])

# ==============================================================================
# 5. PÁGINAS DO APP
# ==============================================================================

if modo == "🧠 Revisão Diária (SRS)":
    st.title("🧠 Revisão Inteligente")
    
    if df_revisao.empty:
        st.success("🎉 Você está em dia!")
    else:
        if 'idx_rev' not in st.session_state: st.session_state.idx_rev = 0
        if 'show_ans' not in st.session_state: st.session_state.show_ans = False
        
        if st.session_state.idx_rev >= len(df_revisao): st.session_state.idx_rev = 0
        row = df_revisao.iloc[st.session_state.idx_rev]
        
        st.markdown(f"""
        <div class="flashcard">
            <div class="meta-info">{row['Categoria']} • {row['Nível']}</div>
            <div class="eng-word">{row['Inglês']}</div>
            {f'<hr style="width:50%; margin:20px 0;"><div class="pt-word">{row["Tradução"]}</div><div class="pron">🗣️ {row["Pronúncia"]}</div>' 
              if st.session_state.show_ans else 
              '<div style="margin-top:40px; color:#94a3b8;">(Toque em REVELAR)</div>'}
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if not st.session_state.show_ans:
                if st.button("👁️ REVELAR RESPOSTA", type="primary", use_container_width=True):
                    st.session_state.show_ans = True
                    st.rerun()
            else:
                col_e, col_a = st.columns(2)
                with col_e:
                    if st.button("❌ Esqueci", use_container_width=True):
                        atualizar_revisao(row['Inglês'], False)
                        adicionar_xp(XP_ERRO)
                        st.session_state.show_ans = False
                        st.session_state.idx_rev = (st.session_state.idx_rev + 1) % len(df_revisao)
                        st.rerun()
                with col_a:
                    if st.button("✅ Lembrei", type="primary", use_container_width=True):
                        atualizar_revisao(row['Inglês'], True)
                        adicionar_xp(XP_ACERTO)
                        st.session_state.show_ans = False
                        st.rerun()

elif modo == "🏋️ Treino por Módulo":
    st.title("🏋️ Treino Específico")
    categorias = sorted([c for c in df['Categoria'].unique() if c != 'Missão'])
    selecao = st.selectbox("Escolha o Módulo:", categorias)
    df_treino = df[df['Categoria'] == selecao].copy()
    
    if not df_treino.empty:
        if 'idx_treino' not in st.session_state: st.session_state.idx_treino = 0
        if 'show_ans_treino' not in st.session_state: st.session_state.show_ans_treino = False
        
        if st.session_state.idx_treino >= len(df_treino): st.session_state.idx_treino = 0
        row = df_treino.iloc[st.session_state.idx_treino]
        
        st.markdown(f"""
        <div class="flashcard" style="border-color: #3b82f6;">
            <div class="meta-info" style="color: #3b82f6;">TREINO • {row['Categoria']}</div>
            <div class="eng-word">{row['Inglês']}</div>
            {f'<hr style="width:50%; margin:20px 0;"><div class="pt-word">{row["Tradução"]}</div><div class="pron">🗣️ {row["Pronúncia"]}</div>' 
              if st.session_state.show_ans_treino else 
              '<div style="margin-top:40px; color:#94a3b8;">(Pense na resposta...)</div>'}
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if not st.session_state.show_ans_treino:
                if st.button("👁️ REVELAR", type="primary", use_container_width=True):
                    st.session_state.show_ans_treino = True
                    st.rerun()
            else:
                col_e, col_a = st.columns(2)
                with col_e:
                    if st.button("❌ Errei", use_container_width=True):
                        atualizar_revisao(row['Inglês'], False)
                        st.session_state.show_ans_treino = False
                        st.session_state.idx_treino = (st.session_state.idx_treino + 1) % len(df_treino)
                        st.rerun()
                with col_a:
                    if st.button("✅ Acertei", type="primary", use_container_width=True):
                        atualizar_revisao(row['Inglês'], True)
                        adicionar_xp(XP_ACERTO)
                        st.session_state.show_ans_treino = False
                        st.session_state.idx_treino = (st.session_state.idx_treino + 1) % len(df_treino)
                        st.rerun()

elif modo == "📊 Dashboard":
    st.title("📊 Desempenho")
    total_cards = len(df[df['Categoria'] != 'Missão'])
    masterizadas = len(df[df['Nivel_SRS'] >= 10])
    st.metric("Total de Cartas", total_cards)
    st.metric("🏆 Masterizadas", masterizadas)
    st.bar_chart(df[df['Categoria'] != 'Missão']['Nivel_SRS'].value_counts())

elif modo == "📜 Missões":
    st.title("📜 Missões")
    for idx, row in df_missoes.iterrows():
        feita = row['Inglês'] in st.session_state.missoes_feitas
        with st.container(border=True):
            c_m1, c_m2 = st.columns([4,1])
            c_m1.markdown(f"**{row['Inglês']}**")
            c_m1.caption(row['Tradução'])
            if feita: c_m2.success("✅")
            elif c_m2.button("Concluir", key=f"m_{idx}"):
                st.session_state.missoes_feitas.append(row['Inglês'])
                adicionar_xp(XP_MISSAO)
                st.rerun()

elif modo == "📖 Banco de Dados":
    st.title("📖 Glossário")
    st.dataframe(df[['Inglês', 'Tradução', 'Categoria', 'Nivel_SRS']], use_container_width=True)
