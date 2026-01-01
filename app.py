import streamlit as st
import pandas as pd
import glob
import os
import json
from datetime import datetime, timedelta
from gtts import gTTS
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÕES E CONSTANTES (3 ANOS)
# ==============================================================================
st.set_page_config(page_title="Samuel's Mastery Pro", page_icon="⚔️", layout="wide")
DATA_PATH = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(DATA_PATH, "progresso.json")

# Intervalos espaçados até 3 anos (1095 dias)
INTERVALOS = [1, 3, 7, 15, 30, 60, 90, 180, 365, 540, 730, 1095]

XP_ACERTO = 15
XP_ERRO = 1 
XP_MISSAO = 50
XP_BASE_NIVEL = 100

st.markdown("""
    <style>
    .flashcard {
        background: white; padding: 40px; border-radius: 20px;
        border: 2px solid #e2e8f0; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        min-height: 400px; display: flex; flex-direction: column; 
        justify-content: center; align-items: center; position: relative;
    }
    .mastered {
        border: 4px solid #fbbf24 !important; background: #fffbeb !important;
    }
    .meta-info {
        font-size: 12px; font-weight: bold; color: #94a3b8; 
        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px;
    }
    .eng-word { color: #0f172a; font-size: 38px; font-weight: 800; margin-bottom: 10px; line-height: 1.2; }
    .pt-word { color: #2563eb; font-size: 24px; font-weight: 600; margin-top: 15px; }
    .status-badge { 
        font-size: 12px; padding: 4px 12px; border-radius: 12px; 
        background: #f1f5f9; color: #64748b; margin-bottom: 20px; 
        border: 1px solid #cbd5e1; display: inline-block;
    }
    .gold-badge { background: #fbbf24; color: #78350f; border:none; font-weight:bold; }
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
            "ultimo_estudo": hoje_str
        }
    else:
        # Se errou, volta ao início (Rigoroso)
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

# Gamification State
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
# 3. PREPARAÇÃO DOS DADOS
# ==============================================================================
df = load_data()
progresso_db = carregar_progresso()

if not df.empty:
    df['Proxima_Revisao'] = df['Inglês'].apply(lambda x: progresso_db.get(x, {}).get('proxima_revisao', '2000-01-01'))
    df['Nivel_SRS'] = df['Inglês'].apply(lambda x: progresso_db.get(x, {}).get('nivel_srs', 0))

    hoje = datetime.now().strftime("%Y-%m-%d")
    
    # Filtros
    df_revisao = df[ (df['Proxima_Revisao'] <= hoje) & (df['Categoria'] != 'Missão') ].copy()
    df_futuro = df[ (df['Proxima_Revisao'] > hoje) & (df['Categoria'] != 'Missão') ].copy()
    df_missoes = df[df['Categoria'] == 'Missão'].copy()
else:
    df_revisao = pd.DataFrame()
    df_futuro = pd.DataFrame()
    df_missoes = pd.DataFrame()

# ==============================================================================
# 4. SIDEBAR (ATUALIZADA COM MÓDULOS)
# ==============================================================================
with st.sidebar:
    st.header(f"🛡️ Nível {st.session_state.nivel}")
    xp_ratio = min(st.session_state.xp / (st.session_state.nivel * XP_BASE_NIVEL), 1.0)
    st.progress(xp_ratio)
    st.caption(f"XP: {st.session_state.xp} / Meta: {st.session_state.nivel * XP_BASE_NIVEL}")
    
    st.divider()
    
    # Resumo Geral
    c1, c2 = st.columns(2)
    c1.metric("📬 Revisar", len(df_revisao))
    c2.metric("💤 Futuro", len(df_futuro))

    # --- NOVO: PROGRESSO POR MÓDULO ---
    with st.expander("📊 Progresso por Módulo", expanded=False):
        if not df.empty:
            # Pega lista de categorias ignorando 'Missão'
            categorias = [c for c in df['Categoria'].unique() if c != 'Missão']
            
            for cat in categorias:
                df_cat = df[df['Categoria'] == cat]
                total_cat = len(df_cat)
                
                # Consideramos "Estudado" qualquer carta que não esteja no Nível 0 (ou seja, já acertou pelo menos uma vez)
                # Ou podemos considerar Cartas Futuras como "aprendidas" temporariamente
                estudadas = len(df_cat[df_cat['Nivel_SRS'] > 0])
                
                if total_cat > 0:
                    pct = estudadas / total_cat
                    st.write(f"**{cat}**")
                    st.progress(pct)
                    st.caption(f"{estudadas}/{total_cat} iniciadas")
        else:
            st.caption("Sem dados.")

    st.divider()
    modo = st.radio("Navegação", ["🧠 Revisão SRS", "📜 Missões", "📖 Banco de Dados"])

# ==============================================================================
# 5. PÁGINA PRINCIPAL
# ==============================================================================
if modo == "🧠 Revisão SRS":
    st.title("🧠 Modo Foco: Jornada de 3 Anos")
    
    if df_revisao.empty:
        st.success("🎉 Todas as revisões do dia concluídas!")
        if not df_futuro.empty:
            st.info("Veja abaixo o que vem por aí nos próximos dias:")
            st.dataframe(df_futuro[['Inglês', 'Categoria', 'Proxima_Revisao']].sort_values('Proxima_Revisao').head(10), use_container_width=True)
    else:
        if 'idx_rev' not in st.session_state: st.session_state.idx_rev = 0
        if 'show_ans' not in st.session_state: st.session_state.show_ans = False
        
        # Garante índice
        if st.session_state.idx_rev >= len(df_revisao): st.session_state.idx_rev = 0
        row = df_revisao.iloc[st.session_state.idx_rev]
        
        # Dados para exibição
        nivel_atual = row['Nivel_SRS']
        idx_intervalo = min(nivel_atual, len(INTERVALOS)-1)
        dias_intervalo = INTERVALOS[idx_intervalo]
        
        # Checagem Masterizado
        is_mastered = (dias_intervalo == 1095)
        css_class = "flashcard mastered" if is_mastered else "flashcard"
        badge_class = "status-badge gold-badge" if is_mastered else "status-badge"
        texto_badge = "🏆 MASTERIZADO" if is_mastered else f"Nível {nivel_atual} • Próx: {dias_intervalo} dias"

        # --- FLASHCARD (ATUALIZADO COM META INFO) ---
        st.markdown(f"""
        <div class="{css_class}">
            <div class="meta-info">{row['Categoria']} • {row['Nível']}</div>
            
            <div class="{badge_class}">{texto_badge}</div>
            
            <div class="eng-word">{row['Inglês']}</div>
            
            {f'<hr style="width:50%; margin:20px 0;"><div class="pt-word">{row["Tradução"]}</div><div class="pron">🗣️ {row["Pronúncia"]}</div>' 
              if st.session_state.show_ans else 
              '<div style="margin-top:40px; color:#94a3b8; cursor:pointer;">(Pense na tradução...)</div>'}
        </div>
        """, unsafe_allow_html=True)
        
        # Botões
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
                        adicionar_xp(XP_ERRO, "Vamos repetir!")
                        st.session_state.show_ans = False
                        st.session_state.idx_rev = (st.session_state.idx_rev + 1) % len(df_revisao)
                        st.rerun()
                with col_acert:
                    if st.button("✅ Acertei", type="primary", use_container_width=True):
                        dias = atualizar_revisao(row['Inglês'], acertou=True)
                        adicionar_xp(XP_ACERTO, "Excelente!")
                        st.toast(f"Revisão agendada para +{dias} dias!")
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
    if df_missoes.empty: st.info("Sem missões ativas.")
    for idx, row in df_missoes.iterrows():
        concluida = row['Inglês'] in st.session_state.missoes_feitas
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
    st.title("Visão Geral do Curso")
    st.caption("Aqui você vê todas as palavras cadastradas e seus níveis de memória.")
    
    # Filtro por módulo no Banco de Dados
    modulos = ["Todos"] + list(df['Categoria'].unique())
    filtro = st.selectbox("Filtrar por Módulo:", modulos)
    
    df_show = df.copy()
    if filtro != "Todos":
        df_show = df_show[df_show['Categoria'] == filtro]
        
    st.dataframe(df_show[['Inglês', 'Tradução', 'Categoria', 'Nível', 'Proxima_Revisao', 'Nivel_SRS']], use_container_width=True)
