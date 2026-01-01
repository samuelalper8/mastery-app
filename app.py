import streamlit as st
import pandas as pd
import glob
import os
import json
from datetime import datetime, timedelta
from gtts import gTTS
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÕES E CONSTANTES (ATUALIZADO PARA 3 ANOS)
# ==============================================================================
st.set_page_config(page_title="Samuel's SRS Pro (3 Years)", page_icon="🧠", layout="wide")
DATA_PATH = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(DATA_PATH, "progresso.json")

# --- LISTA DE INTERVALOS (Em dias) ---
# Lógica: Curto prazo -> Médio prazo -> Longo prazo (até 3 anos)
INTERVALOS = [
    1,      # Nível 0: Revisar amanhã
    3,      # Nível 1: 3 dias
    7,      # Nível 2: 1 semana
    15,     # Nível 3: 2 semanas
    30,     # Nível 4: 1 mês
    60,     # Nível 5: 2 meses
    90,     # Nível 6: 3 meses
    180,    # Nível 7: 6 meses
    365,    # Nível 8: 1 ano
    540,    # Nível 9: 1 ano e meio
    730,    # Nível 10: 2 anos
    1095    # Nível 11: 3 anos (MASTERIZADO)
]

# Configuração de XP
XP_ACERTO = 15 # Aumentei um pouco pois o compromisso é longo
XP_ERRO = 1 
XP_MISSAO = 50
XP_BASE_NIVEL = 100

st.markdown("""
    <style>
    .flashcard {
        background: white; padding: 40px; border-radius: 20px;
        border: 2px solid #e2e8f0; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        min-height: 350px; display: flex; flex-direction: column; 
        justify-content: center; align-items: center;
    }
    /* Classe especial para cartas Masterizadas (Nível Máximo) */
    .mastered {
        border: 4px solid #fbbf24 !important; /* Dourado */
        background: #fffbeb !important;
    }
    .eng-word { color: #0f172a; font-size: 42px; font-weight: 800; margin-bottom: 10px; }
    .pt-word { color: #2563eb; font-size: 28px; font-weight: 600; margin-top: 15px; }
    .status-badge { font-size: 14px; padding: 5px 10px; border-radius: 15px; background: #f1f5f9; color: #64748b; margin-bottom: 15px; border: 1px solid #cbd5e1; }
    .gold-badge { background: #fbbf24; color: #78350f; font-weight:bold; border:none; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. GERENCIAMENTO DE DADOS E PROGRESSO
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
        # Tenta subir de nível, mas não passa do último índice da lista
        proximo_nivel = min(nivel_atual + 1, len(INTERVALOS) - 1)
        dias_para_add = INTERVALOS[proximo_nivel]
        nova_data = (datetime.now() + timedelta(days=dias_para_add)).strftime("%Y-%m-%d")
        
        progresso[termo_ingles] = {
            "nivel_srs": proximo_nivel,
            "proxima_revisao": nova_data,
            "ultimo_estudo": hoje_str
        }
    else:
        # Errou: Volta para o Nível 0 (1 dia) ou Nível 1 (3 dias)?
        # Rigoroso: Volta para o 0 (Revisar amanhã)
        progresso[termo_ingles] = {
            "nivel_srs": 0,
            "proxima_revisao": hoje_str, 
            "ultimo_estudo": hoje_str
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
                for line in f:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3 and not line.startswith("//"):
                        all_data.append({
                            "Inglês": parts[0],
                            "Pronúncia": parts[1] if len(parts) > 1 else "-",
                            "Tradução": parts[2] if len(parts) > 2 else "-",
                            "Categoria": parts[3] if len(parts) > 3 else "Geral",
                            "Nível": parts[4] if len(parts) > 4 else "Geral",
                        })
        except: continue
    
    if not all_data: return pd.DataFrame()
    return pd.DataFrame(all_data).drop_duplicates(subset=['Inglês'])

# ==============================================================================
# 3. SISTEMA DE GAMIFICATION
# ==============================================================================
if 'xp' not in st.session_state: st.session_state.xp = 0
if 'nivel' not in st.session_state: st.session_state.nivel = 1
if 'conquistas' not in st.session_state: st.session_state.conquistas = []
if 'missoes_feitas' not in st.session_state: st.session_state.missoes_feitas = []

def adicionar_xp(qtd, motivo=""):
    st.session_state.xp += qtd
    meta = st.session_state.nivel * XP_BASE_NIVEL
    if st.session_state.xp >= meta:
        st.session_state.nivel += 1
        st.balloons()
        st.toast(f"LEVEL UP! Nível {st.session_state.nivel}!", icon="🎉")
    if motivo: st.toast(f"+{qtd} XP: {motivo}", icon="✨")

# ==============================================================================
# 4. PREPARAÇÃO DOS DADOS
# ==============================================================================
df = load_data()
progresso_db = carregar_progresso()

df['Proxima_Revisao'] = df['Inglês'].apply(lambda x: progresso_db.get(x, {}).get('proxima_revisao', '2000-01-01'))
df['Nivel_SRS'] = df['Inglês'].apply(lambda x: progresso_db.get(x, {}).get('nivel_srs', 0))

hoje = datetime.now().strftime("%Y-%m-%d")
# Apenas cartas para hoje OU atrasadas
df_revisao = df[ (df['Proxima_Revisao'] <= hoje) & (df['Categoria'] != 'Missão') ].copy()
# Cartas futuras
df_futuro = df[ (df['Proxima_Revisao'] > hoje) & (df['Categoria'] != 'Missão') ].copy()
df_missoes = df[df['Categoria'] == 'Missão'].copy()

# SIDEBAR
with st.sidebar:
    st.header(f"🛡️ Nível {st.session_state.nivel}")
    st.progress(min(st.session_state.xp / (st.session_state.nivel * XP_BASE_NIVEL), 1.0))
    st.write(f"XP: {st.session_state.xp}")
    st.divider()
    st.metric("📬 Para Revisar Hoje", len(df_revisao))
    st.metric("💤 Futuras", len(df_futuro))
    
    modo = st.radio("Menu", ["🧠 Revisão SRS", "📜 Missões", "📖 Banco de Dados"])

# ==============================================================================
# 5. LÓGICA DE REVISÃO
# ==============================================================================
if modo == "🧠 Revisão SRS":
    st.title("🧠 Modo Foco: Jornada de 3 Anos")
    
    if df_revisao.empty:
        st.success("🎉 Todas as revisões do dia concluídas!")
        if not df_futuro.empty:
            st.write("Próximas revisões agendadas:")
            # Mostra data formatada bonitinha
            st.dataframe(df_futuro[['Inglês', 'Proxima_Revisao']].sort_values('Proxima_Revisao').head(5), use_container_width=True)
    else:
        if 'idx_rev' not in st.session_state: st.session_state.idx_rev = 0
        if 'show_ans' not in st.session_state: st.session_state.show_ans = False
        
        if st.session_state.idx_rev >= len(df_revisao): st.session_state.idx_rev = 0
        row = df_revisao.iloc[st.session_state.idx_rev]
        
        # Lógica Visual
        nivel_atual = row['Nivel_SRS']
        # Proteção para caso o índice salvo no JSON seja maior que a nova lista (caso mude o código dps)
        idx_intervalo = min(nivel_atual, len(INTERVALOS)-1)
        dias_intervalo = INTERVALOS[idx_intervalo]
        
        # Verifica se é "Masterizado" (Último nível)
        is_mastered = (dias_intervalo == 1095)
        css_class = "flashcard mastered" if is_mastered else "flashcard"
        badge_class = "status-badge gold-badge" if is_mastered else "status-badge"
        texto_badge = "🏆 MASTERIZADO (3 Anos)" if is_mastered else f"Nível {nivel_atual} • Próx: {dias_intervalo} dias"

        st.markdown(f"""
        <div class="{css_class}">
            <div class="{badge_class}">{texto_badge}</div>
            <div class="eng-word">{row['Inglês']}</div>
            {f'<hr style="width:50%; margin:20px 0;"><div class="pt-word">{row["Tradução"]}</div><div class="pron">🗣️ {row["Pronúncia"]}</div>' 
              if st.session_state.show_ans else 
              '<div style="margin-top:40px; color:#94a3b8; cursor:pointer;">(Pense na tradução...)</div>'}
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.write("")
            if not st.session_state.show_ans:
                if st.button("👁️ REVELAR", type="primary", use_container_width=True):
                    st.session_state.show_ans = True
                    st.rerun()
            else:
                col_err, col_acert = st.columns(2)
                with col_err:
                    if st.button("❌ Esqueci", use_container_width=True):
                        atualizar_revisao(row['Inglês'], acertou=False)
                        adicionar_xp(XP_ERRO, "Não desista!")
                        st.session_state.show_ans = False
                        st.session_state.idx_rev = (st.session_state.idx_rev + 1) % len(df_revisao)
                        st.rerun()
                with col_acert:
                    if st.button("✅ Lembrei", type="primary", use_container_width=True):
                        dias = atualizar_revisao(row['Inglês'], acertou=True)
                        adicionar_xp(XP_ACERTO, "Memória fortificada!")
                        st.toast(f"Agendado para +{dias} dias!")
                        st.session_state.show_ans = False
                        st.rerun()

        if st.button("🔊 Pronúncia"):
            try:
                sound = BytesIO()
                tts = gTTS(text=row['Inglês'], lang='en')
                tts.write_to_fp(sound)
                st.audio(sound, format='audio/mp3', start_time=0)
            except: st.error("Erro áudio")

# ==============================================================================
# 6. OUTRAS ABAS
# ==============================================================================
elif modo == "📜 Missões":
    st.title("Missões Semanais")
    if df_missoes.empty: st.info("Sem missões cadastradas.")
    for idx, row in df_missoes.iterrows():
        concluida = row['Inglês'] in st.session_state.missoes_feitas
        cor = "#dcfce7" if concluida else "#fff"
        with st.container(border=True):
            st.markdown(f"**{row['Inglês']}**")
            st.caption(row['Tradução'])
            if not concluida:
                if st.button("Completar", key=f"m_{idx}"):
                    st.session_state.missoes_feitas.append(row['Inglês'])
                    adicionar_xp(XP_MISSAO, "Missão Cumprida!")
                    st.rerun()
            else: st.success("Feito! ✅")

elif modo == "📖 Banco de Dados":
    st.title("Status da Memória")
    # Tabela mais bonita mostrando dias restantes
    df_show = df[['Inglês', 'Tradução', 'Nível', 'Proxima_Revisao', 'Nivel_SRS']].copy()
    st.dataframe(df_show, use_container_width=True)
