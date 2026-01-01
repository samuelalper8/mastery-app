import streamlit as st
import pandas as pd
import glob
import os
import json
from datetime import datetime, timedelta
from gtts import gTTS
from io import BytesIO

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
    .eng-word { color: #0f172a; font-size: 36px; font-weight: 800; margin-bottom: 10px; line-height: 1.2; }
    .pt-word { color: #2563eb; font-size: 24px; font-weight: 600; margin-top: 15px; }
    .status-badge { font-size: 11px; padding: 4px 10px; border-radius: 12px; background: #f1f5f9; color: #64748b; margin-bottom: 15px; border: 1px solid #cbd5e1; display: inline-block; }
    .gold-badge { background: #fbbf24; color: #78350f; border:none; font-weight:bold; }
    
    /* Estilo para métricas de desempenho */
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
        # Erro: Volta ao nível 0
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
                    
                    if len(parts) >= 1: # Aceita linhas parciais para não perder dados
                        item = {
                            "Inglês": parts[0],
                            "Pronúncia": parts[1] if len(parts) > 1 else "-",
                            "Tradução": parts[2] if len(parts) > 2 else "-",
                            "Categoria": parts[3] if len(parts) > 3 else "Geral",
                            "Nível": parts[4] if len(parts) > 4 else "Geral",
                        }
                        all_data.append(item)
        except: continue
    
    if not all_data: return pd.DataFrame()
    # Remove apenas duplicatas exatas de linha inteira
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
    # Calcula 'Saúde' da palavra (0 a 100%) baseado no nível máximo (11)
    df['Retencao'] = (df['Nivel_SRS'] / 11) * 100
    
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
    c1.metric("🔥 Atrasados", len(df_revisao), delta_color="inverse")
    c2.metric("💤 Futuro", len(df_futuro))

    st.divider()
    modo = st.radio("Menu Principal", ["🧠 Revisão Diária", "📊 Dashboard", "📜 Missões", "📖 Banco de Dados"])
    
    with st.expander("ℹ️ Sobre o SRS"):
        st.caption("Intervalos de revisão atuais:")
        st.caption(f"{INTERVALOS}")

# ==============================================================================
# 5. PÁGINAS DO APP
# ==============================================================================

# --- MODO 1: REVISÃO (SRS) ---
if modo == "🧠 Revisão Diária":
    st.title("🧠 Modo Foco")
    
    if df_revisao.empty:
        st.success("🎉 Você está em dia! Nenhuma revisão pendente.")
        if not df_futuro.empty:
            st.info("Próximas revisões:")
            st.dataframe(df_futuro[['Inglês', 'Categoria', 'Proxima_Revisao']].sort_values('Proxima_Revisao').head(5), use_container_width=True)
    else:
        # Controle de Sessão
        if 'idx_rev' not in st.session_state: st.session_state.idx_rev = 0
        if 'show_ans' not in st.session_state: st.session_state.show_ans = False
        
        if st.session_state.idx_rev >= len(df_revisao): st.session_state.idx_rev = 0
        row = df_revisao.iloc[st.session_state.idx_rev]
        
        # Dados do Card
        lvl = row['Nivel_SRS']
        dias = INTERVALOS[min(lvl, len(INTERVALOS)-1)]
        mastered = (dias >= 1095)
        
        css = "flashcard mastered" if mastered else "flashcard"
        badge = "🏆 MASTERIZADO" if mastered else f"Nível {lvl} • Próx: {dias} dias"
        bg_badge = "gold-badge" if mastered else ""

        # Layout do Card
        st.markdown(f"""
        <div class="{css}">
            <div class="meta-info">{row['Categoria']} • {row['Nível']}</div>
            <div class="status-badge {bg_badge}">{badge}</div>
            <div class="eng-word">{row['Inglês']}</div>
            {f'<hr style="width:50%; margin:20px 0;"><div class="pt-word">{row["Tradução"]}</div><div class="pron">🗣️ {row["Pronúncia"]}</div>' 
              if st.session_state.show_ans else 
              '<div style="margin-top:40px; color:#94a3b8; cursor:pointer;">(Toque em REVELAR)</div>'}
        </div>
        """, unsafe_allow_html=True)
        
        # Botões
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.write("")
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
                        st.toast("Não desanime! Vai melhorar.")
                        st.session_state.show_ans = False
                        st.session_state.idx_rev = (st.session_state.idx_rev + 1) % len(df_revisao)
                        st.rerun()
                with col_a:
                    if st.button("✅ Lembrei", type="primary", use_container_width=True):
                        novos_dias = atualizar_revisao(row['Inglês'], True)
                        adicionar_xp(XP_ACERTO)
                        st.toast(f"Ótimo! +{novos_dias} dias.")
                        st.session_state.show_ans = False
                        st.rerun() # Recarrega para remover o card da lista atual

        if st.button("🔊 Ouvir Pronúncia"):
            try:
                sound = BytesIO()
                tts = gTTS(text=row['Inglês'], lang='en')
                tts.write_to_fp(sound)
                st.audio(sound, format='audio/mp3', start_time=0)
            except: st.error("Erro no áudio.")

# --- MODO 2: DASHBOARD DE DESEMPENHO (NOVO) ---
elif modo == "📊 Dashboard":
    st.title("📊 Análise de Desempenho")
    
    if df.empty:
        st.warning("Sem dados suficientes para análise.")
    else:
        # KPIs Principais
        total_cards = len(df[df['Categoria'] != 'Missão'])
        # Consideramos 'Aprendidas' qualquer carta que não seja Nível 0
        aprendidas = len(df[(df['Nivel_SRS'] > 0) & (df['Categoria'] != 'Missão')])
        # Masterizadas (Nível > 10, ou seja, 3 anos)
        masterizadas = len(df[(df['Nivel_SRS'] >= 10) & (df['Categoria'] != 'Missão')])
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Total de Cartas", total_cards)
        k2.metric("Em Processo de Aprendizagem", aprendidas, f"{round((aprendidas/total_cards)*100)}%")
        k3.metric("🏆 Masterizadas (3 Anos)", masterizadas)

        st.divider()

        # Gráfico 1: Curva de Memória (Distribuição SRS)
        st.subheader("🧠 Saúde da Memória")
        st.caption("Quantas cartas você tem em cada estágio de retenção (Dias)")
        
        # Mapeia nível SRS para dias
        srs_counts = df[df['Categoria'] != 'Missão']['Nivel_SRS'].value_counts().sort_index()
        # Cria um DF bonito para o gráfico
        chart_data = pd.DataFrame({
            "Nível SRS": srs_counts.index,
            "Quantidade": srs_counts.values,
            "Dias (Intervalo)": [str(INTERVALOS[min(i, 11)]) + 'd' for i in srs_counts.index]
        })
        st.bar_chart(chart_data, x="Dias (Intervalo)", y="Quantidade", color="#3b82f6")

        c_left, c_right = st.columns(2)
        
        with c_left:
            st.subheader("📚 Top 5 Módulos Fortes")
            # Agrupa por categoria e calcula média do Nível SRS
            ranking = df[df['Categoria'] != 'Missão'].groupby('Categoria')['Nivel_SRS'].mean().sort_values(ascending=False).head(5)
            st.dataframe(ranking, use_container_width=True, column_config={"Nivel_SRS": st.column_config.ProgressColumn("Retenção Média", min_value=0, max_value=11)})
            
        with c_right:
            st.subheader("⚠️ Módulos Precisando de Atenção")
            # Os 5 piores
            ranking_worst = df[df['Categoria'] != 'Missão'].groupby('Categoria')['Nivel_SRS'].mean().sort_values(ascending=True).head(5)
            st.dataframe(ranking_worst, use_container_width=True, column_config={"Nivel_SRS": st.column_config.ProgressColumn("Retenção Média", min_value=0, max_value=11, format="%.1f")})

# --- MODO 3: MISSÕES ---
elif modo == "📜 Missões":
    st.title("📜 Quadro de Missões")
    if df_missoes.empty: st.info("Nenhuma missão ativa.")
    
    for idx, row in df_missoes.iterrows():
        feita = row['Inglês'] in st.session_state.missoes_feitas
        with st.container(border=True):
            cols = st.columns([4, 1])
            cols[0].markdown(f"**{row['Inglês']}**")
            cols[0].caption(row['Tradução'])
            
            if feita:
                cols[1].success("✅")
            else:
                if cols[1].button("Concluir", key=f"mis_{idx}"):
                    st.session_state.missoes_feitas.append(row['Inglês'])
                    adicionar_xp(XP_MISSAO)
                    st.rerun()

# --- MODO 4: BANCO DE DADOS ---
elif modo == "📖 Banco de Dados":
    st.title("📖 Glossário Completo")
    
    with st.expander("🛠️ Diagnóstico do Sistema"):
        st.write(f"Linhas totais: {len(df)}")
        st.write(f"Duplicatas removidas na carga: {len(df) - len(df.drop_duplicates(subset=['Inglês']))} (apenas info)")
    
    termo = st.text_input("🔍 Pesquisar palavra...")
    filtro_cat = st.selectbox("Filtrar Categoria", ["Todas"] + sorted(list(df['Categoria'].unique())))
    
    df_show = df.copy()
    if filtro_cat != "Todas":
        df_show = df_show[df_show['Categoria'] == filtro_cat]
    if termo:
        df_show = df_show[df_show['Inglês'].str.contains(termo, case=False) | df_show['Tradução'].str.contains(termo, case=False)]
        
    st.dataframe(
        df_show[['Inglês', 'Tradução', 'Categoria', 'Nivel_SRS', 'Proxima_Revisao']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Nivel_SRS": st.column_config.NumberColumn("Nível", help="0 a 11"),
            "Proxima_Revisao": st.column_config.DateColumn("Revisar Em", format="DD/MM/YYYY")
        }
    )
