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
st.set_page_config(page_title="Samuel's SRS Pro", page_icon="🧠", layout="wide")
DATA_PATH = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(DATA_PATH, "progresso.json")

# Intervalos de revisão em dias (Rigorous Mode)
INTERVALOS = [1, 7, 15, 30, 60, 90, 180, 365]

# Configuração de XP
XP_ACERTO = 10
XP_ERRO = 1  # Ganha pouco XP se errar, mas ganha por tentar
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
    .eng-word { color: #0f172a; font-size: 42px; font-weight: 800; margin-bottom: 10px; }
    .pt-word { color: #2563eb; font-size: 28px; font-weight: 600; margin-top: 15px; }
    .status-badge { font-size: 14px; padding: 5px 10px; border-radius: 15px; background: #f1f5f9; color: #64748b; margin-bottom: 15px; border: 1px solid #cbd5e1; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. GERENCIAMENTO DE DADOS E PROGRESSO (O CÉREBRO)
# ==============================================================================

def carregar_progresso():
    """Carrega o arquivo JSON que contém as datas de revisão."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def salvar_progresso(dados):
    """Salva o progresso no arquivo JSON."""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4)

def atualizar_revisao(termo_ingles, acertou):
    """Calcula a próxima data de revisão baseada no acerto/erro."""
    progresso = carregar_progresso()
    hoje_str = datetime.now().strftime("%Y-%m-%d")
    
    # Recupera dados atuais ou cria novo registro
    registro = progresso.get(termo_ingles, {"nivel_srs": 0, "proxima_revisao": hoje_str})
    nivel_atual = registro["nivel_srs"]

    if acertou:
        # Se acertou, sobe de nível (aumenta o intervalo)
        proximo_nivel = min(nivel_atual + 1, len(INTERVALOS) - 1)
        dias_para_add = INTERVALOS[proximo_nivel]
        nova_data = (datetime.now() + timedelta(days=dias_para_add)).strftime("%Y-%m-%d")
        
        progresso[termo_ingles] = {
            "nivel_srs": proximo_nivel,
            "proxima_revisao": nova_data,
            "ultimo_estudo": hoje_str
        }
    else:
        # Se errou, reseta para o nível 0 (revisar amanhã/hoje)
        progresso[termo_ingles] = {
            "nivel_srs": 0,
            "proxima_revisao": hoje_str, # Mantém para hoje/amanhã
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
# 4. INTERFACE PRINCIPAL
# ==============================================================================
df = load_data()
progresso_db = carregar_progresso()

# Mesclar dados do arquivo TXT com dados de Progresso JSON
df['Proxima_Revisao'] = df['Inglês'].apply(lambda x: progresso_db.get(x, {}).get('proxima_revisao', '2000-01-01'))
df['Nivel_SRS'] = df['Inglês'].apply(lambda x: progresso_db.get(x, {}).get('nivel_srs', 0))

# Filtrar o que precisa ser revisado HOJE (Data <= Hoje)
hoje = datetime.now().strftime("%Y-%m-%d")
df_revisao = df[ (df['Proxima_Revisao'] <= hoje) & (df['Categoria'] != 'Missão') ].copy()
df_futuro = df[ (df['Proxima_Revisao'] > hoje) & (df['Categoria'] != 'Missão') ].copy()
df_missoes = df[df['Categoria'] == 'Missão'].copy()

# SIDEBAR
with st.sidebar:
    st.header(f"🛡️ Nível {st.session_state.nivel}")
    st.progress(min(st.session_state.xp / (st.session_state.nivel * XP_BASE_NIVEL), 1.0))
    st.write(f"XP: {st.session_state.xp}")
    
    st.divider()
    
    st.metric("📬 Para Revisar Hoje", len(df_revisao))
    st.metric("💤 Aprendidas (Futuro)", len(df_futuro))
    
    modo = st.radio("Menu", ["🧠 Revisão SRS", "📜 Missões", "📖 Banco de Dados"])

# ==============================================================================
# 5. PÁGINA DE REVISÃO (SRS)
# ==============================================================================
if modo == "🧠 Revisão SRS":
    st.title("🧠 Modo Foco: Spaced Repetition")
    
    if df_revisao.empty:
        st.success("🎉 Parabéns! Você zerou suas revisões de hoje!")
        st.info("Volte amanhã ou revise as cartas futuras no modo 'Banco de Dados'.")
        if not df_futuro.empty:
            st.write("Cartas agendadas para o futuro:")
            st.dataframe(df_futuro[['Inglês', 'Proxima_Revisao']], use_container_width=True)
    else:
        # Lógica de Navegação
        if 'idx_rev' not in st.session_state: st.session_state.idx_rev = 0
        if 'show_ans' not in st.session_state: st.session_state.show_ans = False
        
        # Garante indice válido
        if st.session_state.idx_rev >= len(df_revisao): st.session_state.idx_rev = 0
        
        row = df_revisao.iloc[st.session_state.idx_rev]
        
        # Visualização do Card
        dias_intervalo = INTERVALOS[min(row['Nivel_SRS'], len(INTERVALOS)-1)]
        
        st.markdown(f"""
        <div class="flashcard">
            <div class="status-badge">Intervalo Atual: {dias_intervalo} dias</div>
            <div class="eng-word">{row['Inglês']}</div>
            {f'<hr style="width:50%; margin:20px 0;"><div class="pt-word">{row["Tradução"]}</div><div class="pron">🗣️ {row["Pronúncia"]}</div>' 
              if st.session_state.show_ans else 
              '<div style="margin-top:40px; color:#94a3b8; cursor:pointer;">(Tente lembrar antes de revelar)</div>'}
        </div>
        """, unsafe_allow_html=True)
        
        # Botões de Ação
        c1, c2, c3 = st.columns([1, 2, 1])
        
        with c2:
            st.write("")
            if not st.session_state.show_ans:
                if st.button("👁️ REVELAR RESPOSTA", type="primary", use_container_width=True):
                    st.session_state.show_ans = True
                    st.rerun()
            else:
                # Botões de Classificação (SRS)
                col_err, col_acert = st.columns(2)
                with col_err:
                    if st.button("❌ Errei / Esqueci", use_container_width=True):
                        atualizar_revisao(row['Inglês'], acertou=False)
                        adicionar_xp(XP_ERRO, "Continua tentando!")
                        st.session_state.show_ans = False
                        st.session_state.idx_rev = (st.session_state.idx_rev + 1) % len(df_revisao) # Passa para o próximo mesmo errando para não travar
                        st.rerun()
                        
                with col_acert:
                    if st.button("✅ Acertei / Fácil", type="primary", use_container_width=True):
                        dias = atualizar_revisao(row['Inglês'], acertou=True)
                        adicionar_xp(XP_ACERTO, "Boa memória!")
                        st.toast(f"Agendado para daqui a {dias} dias!")
                        st.session_state.show_ans = False
                        # Recarrega a página para atualizar a lista de revisão (remove o item feito)
                        st.rerun()

        # Áudio
        if st.button("🔊 Pronúncia", use_container_width=False):
            try:
                sound = BytesIO()
                tts = gTTS(text=row['Inglês'], lang='en')
                tts.write_to_fp(sound)
                st.audio(sound, format='audio/mp3', start_time=0)
            except: st.error("Erro de áudio")

# ==============================================================================
# 6. OUTRAS PÁGINAS
# ==============================================================================
elif modo == "📜 Missões":
    st.title("Missões Semanais")
    for idx, row in df_missoes.iterrows():
        concluida = row['Inglês'] in st.session_state.missoes_feitas
        cor = "#dcfce7" if concluida else "#fff"
        with st.container(border=True):
            st.markdown(f"**{row['Inglês']}** - {row['Tradução']}")
            if not concluida:
                if st.button("Completar", key=f"mis_{idx}"):
                    st.session_state.missoes_feitas.append(row['Inglês'])
                    adicionar_xp(XP_MISSAO, "Missão Cumprida!")
                    st.rerun()
            else:
                st.success("Completada!")

elif modo == "📖 Banco de Dados":
    st.title("Todas as Palavras")
    st.dataframe(df[['Inglês', 'Tradução', 'Nível', 'Proxima_Revisao', 'Nivel_SRS']], use_container_width=True)
