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

# Nome do arquivo conforme solicitado
ARQUIVO_DADOS = "dados_concluidos.txt"
PROGRESS_FILE = "progresso_rpg.json"

# Ciclo de repetição (SRS)
INTERVALOS = [1, 3, 7, 15, 30, 60, 90, 180, 365, 540, 730, 1095]
XP_ACERTO, XP_ERRO, XP_MISSAO, XP_BASE_NIVEL = 15, 1, 50, 100

st.markdown("""
    <style>
    .flashcard {
        background: white; padding: 30px; border-radius: 20px;
        border: 2px solid #e2e8f0; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        min-height: 350px; display: flex; flex-direction: column; 
        justify-content: center; align-items: center;
    }
    .meta-info { font-size: 12px; font-weight: bold; color: #94a3b8; text-transform: uppercase; margin-bottom: 5px; }
    .eng-word { color: #1e293b; font-size: 38px; font-weight: 800; margin-bottom: 10px; }
    .pt-word { color: #2563eb; font-size: 24px; font-weight: 600; margin-top: 15px; }
    .pron { 
        color: #1e293b; font-size: 18px; font-weight: 500;
        background: #f1f5f9; padding: 8px 15px; border-radius: 10px;
        margin-top: 10px; border: 1px solid #e2e8f0;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LÓGICA DE DADOS E ÁUDIO
# ==============================================================================

def tocar_audio(texto):
    """Gera e toca o áudio da frase em inglês"""
    try:
        tts = gTTS(text=texto, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp, format='audio/mp3', autoplay=True)
    except Exception as e:
        st.error(f"Erro no áudio: {e}")

def carregar_progresso():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def salvar_progresso(dados):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4)

@st.cache_data
def carregar_dados_do_arquivo():
    """Lê o arquivo dados_concluidos.txt e transforma em DataFrame"""
    itens = []
    
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
            linhas = f.readlines()
    else:
        st.warning(f"Arquivo {ARQUIVO_DADOS} não encontrado. Usando dados de exemplo.")
        # Dados de exemplo caso o arquivo não exista
        linhas = [
            "Welcome | Uél-cam | Bem-vindo | Geral | A1",
            "Example | Eg-zém-pol | Exemplo | Geral | A1"
        ]

    for linha in linhas:
        linha = linha.strip()
        if not linha or linha.startswith("//"):
            continue
        partes = [p.strip() for p in linha.split('|')]
        if len(partes) >= 3:
            itens.append({
                "Inglês": partes[0],
                "Pronúncia": partes[1],
                "Tradução": partes[2],
                "Categoria": partes[3] if len(partes) > 3 else "Geral",
                "Nível": partes[4] if len(partes) > 4 else "A1"
            })
    return pd.DataFrame(itens)

# ==============================================================================
# 3. CONTROLE DE ESTADO E GAMIFICAÇÃO
# ==============================================================================

if 'xp' not in st.session_state: st.session_state.xp = 0
if 'nivel' not in st.session_state: st.session_state.nivel = 1

df = carregar_dados_do_arquivo()
progresso_db = carregar_progresso()
hoje_str = datetime.now().strftime("%Y-%m-%d")

# Mesclar progresso com os dados carregados
df['Proxima'] = df['Inglês'].apply(lambda x: progresso_db.get(x, {}).get('proxima_revisao', '2000-01-01'))
df_revisao = df[(df['Proxima'] <= hoje_str) & (df['Categoria'] != 'Missão')].copy()
df_missoes = df[df['Categoria'] == 'Missão'].copy()

# ==============================================================================
# 4. INTERFACE DO USUÁRIO
# ==============================================================================

with st.sidebar:
    st.title("⚔️ Samuel's RPG")
    st.subheader(f"🛡️ Nível {st.session_state.nivel}")
    progresso_barra = min((st.session_state.xp % XP_BASE_NIVEL) / XP_BASE_NIVEL, 1.0)
    st.progress(progresso_barra)
    st.write(f"XP Total: {st.session_state.xp}")
    st.divider()
    modo = st.radio("Navegação", ["🧠 Revisão Diária", "📜 Missões Ativas", "📖 Glossário"])

if modo == "🧠 Revisão Diária":
    st.header("Sessão de Treinamento")
    
    if df_revisao.empty:
        st.success("🎉 Excelente! Você completou todas as revisões de hoje.")
    else:
        if 'idx' not in st.session_state: st.session_state.idx = 0
        if 'revelado' not in st.session_state: st.session_state.revelado = False
        
        # Garantia de índice
        idx = st.session_state.idx % len(df_revisao)
        row = df_revisao.iloc[idx]
        
        st.markdown(f"""
            <div class="flashcard">
                <div class="meta-info">{row['Categoria']} • {row['Nível']}</div>
                <div class="eng-word">{row['Inglês']}</div>
                {f'<hr style="width:50%"><div class="pt-word">{row["Tradução"]}</div><div class="pron">🗣️ {row["Pronúncia"]}</div>' if st.session_state.revelado else '<div style="margin-top:20px; color:#cbd5e1;">(Pense na resposta e clique em revelar)</div>'}
            </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.revelado:
            tocar_audio(row['Inglês'])
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("❌ Esqueci", use_container_width=True):
                    # Lógica SRS para erro
                    progresso_db[row['Inglês']] = {"nivel_srs": 0, "proxima_revisao": hoje_str}
                    salvar_progresso(progresso_db)
                    st.session_state.xp += XP_ERRO
                    st.session_state.revelado = False
                    st.session_state.idx += 1
                    st.rerun()
            with c2:
                if st.button("✅ Acertei", use_container_width=True, type="primary"):
                    # Lógica SRS para acerto
                    nv_atual = progresso_db.get(row['Inglês'], {}).get('nivel_srs', 0)
                    novo_nv = min(nv_atual + 1, len(INTERVALOS) - 1)
                    nova_data = (datetime.now() + timedelta(days=INTERVALOS[novo_nv])).strftime("%Y-%m-%d")
                    progresso_db[row['Inglês']] = {"nivel_srs": novo_nv, "proxima_revisao": nova_data}
                    salvar_progresso(progresso_db)
                    st.session_state.xp += XP_ACERTO
                    st.session_state.revelado = False
                    st.session_state.idx += 1
                    # Level up check
                    if st.session_state.xp // XP_BASE_NIVEL > (st.session_state.xp - XP_ACERTO) // XP_BASE_NIVEL:
                        st.session_state.nivel += 1
                        st.balloons()
                    st.rerun()
        else:
            if st.button("👁️ REVELAR RESPOSTA", use_container_width=True, type="primary"):
                st.session_state.revelado = True
                st.rerun()

elif modo == "📜 Missões Ativas":
    st.header("Missões de Campo")
    if df_missoes.empty:
        st.info("Nenhuma missão cadastrada no arquivo.")
    else:
        for i, m in df_missoes.iterrows():
            with st.expander(f"🚩 {m['Inglês']}"):
                st.write(f"**Descrição:** {m['Tradução']}")
                if st.button("Marcar como Concluída", key=f"mis_{i}"):
                    st.session_state.xp += XP_MISSAO
                    st.toast(f"Missão concluída! +{XP_MISSAO} XP")

elif modo == "📖 Glossário":
    st.header("Biblioteca de Conhecimento")
    busca = st.text_input("Filtrar termo:")
    df_mostra = df[df['Inglês'].str.contains(busca, case=False)] if busca else df
    st.dataframe(df_mostra[['Inglês', 'Tradução', 'Pronúncia', 'Categoria', 'Nível']], use_container_width=True)
