import os
import random
import secrets
import pytz
import asyncio
import httpx
from datetime import datetime
from copy import deepcopy
import csv
import io
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from fastapi import Form
from fastapi.staticfiles import StaticFiles

# Isso diz: "Tudo que começar com /static, procure na pasta física chamada static"
pp = FastAPI()

# Pega o caminho de onde o main.py está rodando no Render
base_dir = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(base_dir, "static")

# DEBUG: Isso vai nos confirmar no log se o caminho montado bate com o real
print(f"Tentando montar a pasta em: {static_path}")

if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
else:
    # Caso o Render mude a estrutura, essa linha tenta o caminho que deu certo no seu log
    fallback_path = "/opt/render/project/src/site/static"
    if os.path.exists(fallback_path):
        app.mount("/static", StaticFiles(directory=fallback_path), name="static")


# =============================
# CONFIGURAÇÃO
# =============================

DATABASE_URL = os.getenv("DATABASE_URL").strip()
timezone_br = pytz.timezone("America/Sao_Paulo")

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# =============================
# SISTEMA ANTI-SLEEP (RENDER)
# =============================

async def self_ping():
    """Mantém o Render acordado mandando um pulso interno a cada 40s"""
    # Substitua pela sua URL real do Render
    url = "https://prova-0rr1.onrender.com/health-check" 
    await asyncio.sleep(15) 
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await client.get(url)
            except Exception:
                pass 
            await asyncio.sleep(40)

# =============================
# BANCO DE DADOS
# =============================

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Tabela de Resultados
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resultados (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            codigo TEXT NOT NULL,
            nota INTEGER NOT NULL,
            data TEXT NOT NULL
        )
    """)
    # Tabela de Códigos
    cur.execute("""
        CREATE TABLE IF NOT EXISTS codigos_validos (
            codigo TEXT PRIMARY KEY,
            usado BOOLEAN DEFAULT FALSE
        )
    """)
   # Tabela de Candidatos
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidatos (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            telefone TEXT NOT NULL,
            horarios TEXT NOT NULL,
            ja_presta_servico TEXT NOT NULL,
            data_cadastro TEXT NOT NULL,
            bairro TEXT
        )
    """)

    # --- AGORA A PARTE IMPORTANTE: ADICIONAR AS NOVAS COLUNAS ---
    # O comando abaixo adiciona a coluna se ela ainda não existir
    cur.execute("ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS tipo_plantao TEXT")
    cur.execute("ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS turno TEXT")
    cur.execute("ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS bairro TEXT")

    conn.commit()
    cur.close()
    conn.close()

@app.on_event("startup")
def startup():
    try:
        init_db()
        asyncio.create_task(self_ping())
        print("Servidor iniciado e banco ok.")
    except Exception as e:
        print("Erro no startup:", e)

# 1. Rota para mostrar a página de perfil
@app.get("/perfil", response_class=HTMLResponse)
async def mostrar_perfil(request: Request):
    return templates.TemplateResponse("perfil.html", {"request": request})

# 2. Rota que recebe os dados do botão "Salvar"
@app.post("/atualizar-perfil")
async def processar_perfil(
    peso: float = Form(...), 
    qualidades: str = Form(...)
):
    # Aqui você usará o seu código do Supabase para dar o UPDATE
    # UPDATE candidatos SET peso = %s, qualidades = %s WHERE email = ...
    
    print(f"Dados recebidos: Peso {peso}, Qualidades: {qualidades}")
    
    # Após salvar, você pode mandar ele para a página de plantões
    return {"status": "Perfil Salvo!", "proximo_passo": "Ver Plantões"}





@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

# =============================
# PERGUNTAS (Base de Dados)
# =============================

PERGUNTAS = [
    {"id": 1, "texto": "Ao chegar na residência para o plantão o que devemos primeiramente fazer?", "opcoes": ["Dar bom dia ou cumprimentar a todos da residência para dar inicio ao plantão.", "Entrar na residência, lavar as mãos trocar de roupae começar a trabalhar.", "Entrar na residencia, lavar as mãos e proceder com o metodo anti-covid(tomar banho, trocar de roupa) lavar as mãos novamente e cumprimentar a todos procurando saber as comorbidades do paciente", "Entrar, proceder com o metodo anti-covid e se dirigir ao paciente pos ele e responsavel por si mesmo"], "correta": "Entrar na residencia, lavar as mãos e proceder com o metodo anti-covid(tomar banho, trocar de roupa) lavar as mãos novamente e cumprimentar a todos procurando saber as comorbidades do paciente"},
    {"id": 2, "texto": "O que são comorbidades?", "opcoes": ["É a presença de uma doença contagiosa onde temos que manter isolado o paciente.", "É a ocorrência de duas ou mais doenças simultaneamente num mesmo paciente contraidas nos hospitais.", "É a presença de duas ou mais doenças ou condições de saúde simultâneas em um mesmo indivíduo.", "O termo se refere a doenças pré-existentes, que quando adquiridas em algum lugar podem agravar o quadro biológico."], "correta": "É a presença de duas ou mais doenças ou condições de saúde simultâneas em um mesmo indivíduo."},
    {"id": 3, "texto": "O nome dado ao aparelho para aferir a pressão arterial:", "opcoes": ["Estetoscopiômetro.", "Esfignomanômetro.", "Esfigmomanômetro.", "Digital Analógico P.A."], "correta": "Esfigmomanômetro."},
    {"id": 4, "texto": "Na ordem, os significados dos nomes acima são: Termômetro - Oxímetro - Glicosímetro", "opcoes": ["Glicose - Saturação - Temperatura.", "Saturação - Temperatura - Glicose.", "Temperatura - Glicose - Saturação", "Temperatura - Saturação - Glicose."], "correta": "Temperatura - Saturação - Glicose."},
    {"id": 5, "texto": "Quais são os sinais vitais?", "opcoes": ["Pressão arterial, frequência moderada, saturação, frequência total e temporização.", "Temperatura, saturação, pressão arterial, frequência cardíaca, frequência moderada.", "Pressão arterial, frequência cardíaca, saturação, frequência respiratória e temperatura.", "Pressão arterial, saturação, temperatura, frequência brônquio traqueal e frequência cardíaca."], "correta": "Pressão arterial, frequência cardíaca, saturação, frequência respiratória e temperatura."},
    {"id": 6, "texto": "Quando o idoso apresenta uma dor de cabeça, febre ou dor no corpo, o médico receitou a ele:", "opcoes": ["Anciolítico.", "Antiespasmódico.", "Analgésico.", "Anti-inflamatório."], "correta": "Analgésico."},
    {"id": 7, "texto": "Quando o idoso apresenta uma infecção, o médico receitou a ele um:", "opcoes": ["Antibiótico.", "Antiespasmódico.", "Antipirético.", "Barbitúrico."], "correta": "Antibiótico."},
    {"id": 8, "texto": "Na ordem, quais os tipos de banho que toma um idoso que deambula, que possui deficiência ao deambular ou cadeirante e o acamado?", "opcoes": ["Banho de Ofurô, Cadeira higiênica em aspersão e Banho de leito.", "Banho por aspersão, Cadeira higiênica por aspersão e banho de leito.", "Banho de banheira, banho de chuveiro e banho de pano umedecido.", "Banho por aspersão, banho de caneco, banho no leito."], "correta": "Banho por aspersão, Cadeira higiênica por aspersão e banho de leito."},
    {"id": 9, "texto": "O idoso apresentou em aferição a pressão arterial 16 x 10. Logo é uma pressão? E o idoso é?", "opcoes": ["alta, hipotenso", "baixa, hipertenso", "alta, hipertenso", "baixa, hipotenso"], "correta": "alta, hipertenso"},
    {"id": 10, "texto": "O idoso se auto medicou para a pressão arterial. Aferiu a mesma e se encontrava em 9 x 5, logo é uma pressão? E o idoso ficou?", "opcoes": ["baixa, hipotenso", "baixa, oscilatória", "alta, hipotenso", "baixa, hipertenso"], "correta": "baixa, hipotenso"},
    {"id": 11, "texto": "SVA e SVD são:", "opcoes": ["Sondas vasculares de aferir e demorar.", "Sondas", "Sondas Vesicais de Alívio e Demora.", "Sondas Vivais de Absorção e Demanda."], "correta": "Sondas Vesicais de Alívio e Demora."},
    {"id": 12, "texto": "Colostomia, TQT e GTT são:", "opcoes": ["Aparelhos", "Monitores", "Controles", "Dispositivos"], "correta": "Dispositivos"},
    {"id": 13, "texto": "Um idoso aferiu seu HGT e sua glicose estava em 305. A glicose estava? Logo é um paciente?", "opcoes": ["alta, hiperglicêmico", "alta, hiperglyfásico", "baixa, hipofágico", "alta, hipoglicêmico"], "correta": "alta, hiperglicêmico"},
    {"id": 14, "texto": "Por fim, o idoso teimoso se medicou sozinho e a glicemia dele foi a 52. Logo a glicose estava? E ele se tornou um paciente?", "opcoes": ["baixa, hiperfágico", "baixa, hiperglifágico", "alta, hiperativo", "baixa, hipoglicêmico"], "correta": "baixa, hipoglicêmico"},
    {"id": 15, "texto": "Quetiapina e Clonazepam são medicações para pacientes de quadro:", "opcoes": ["Animados", "Nefrológicos", "Neurológicos", "Nasogástricos"], "correta": "Neurológicos"},
    {"id": 16, "texto": "O que é COGNITIVO?", "opcoes": ["Tudo que está relacionado aos processos visuais.", "Tudo que está relacionado aos processos mentais.", "Tudo que está relacionado aos processos perceptivos.", "Todas as alternativas."], "correta": "Todas as alternativas."},
    {"id": 17, "texto": "O paciente é deitado em decúbito dorsal (barriga p/ cima) numa maca inclinada, com os pés mais inclinados que a cabeça p/ quando a PA estiver baixa. Essa manobra se chama:", "opcoes": ["Manobra dorsal", "Trendelenburg", "Albert Schweitzer", "Pittsburg"], "correta": "Trendelenburg"},
    {"id": 18, "texto": "Para a reanimação cardíaca, quantas contrações torácicas são necessárias p/ frequência cardíaca (cardiovascular):", "opcoes": ["De 90 a 110 por minuto.", "De 100 a 120 por minuto.", "De 150 a 180 por minuto.", "De 60 a 80 por minuto."], "correta": "De 100 a 120 por minuto."},
    {"id": 19, "texto": "Diante de um idoso chorando, escolha a opção mais correta:", "opcoes": ["Distrair o idoso.", "Ouvi-lo e acolhê-lo.", "Ignorar até passar.", "Repreendê-lo."], "correta": "Ouvi-lo e acolhê-lo."},
    {"id": 20, "texto": "Diante de um idoso agressivo, qual a alternativa correta:", "opcoes": ["Manter distância.", "Buscar entender a causa.", "Acalmar o idoso.", "Todas as alternativas."], "correta": "Todas as alternativas."},
    {"id": 21, "texto": "Sobre o uso do Oxímetro qual o nível certo de percentagem p/ o paciente:", "opcoes": ["A-De 98 a 100", "B-De 90 a 94", "C- De 95 a 97", "D-A letra 'a' e 'b' estão corretas."], "correta": "D-A letra 'a' e 'b' estão corretas."},
    {"id": 22, "texto": "Em caso de queda de saturação o que você deve fazer e qual a porcentagem de saturação você deve agir imediatamente?", "opcoes": ["94 de saturação ligar p/ família", "92 de saturação entrar em contato c/ responsável técnico e ligar p/ família.", "91 de sat. entrar em contato c/ a empresa, família e o SAMU.", "89 de saturação. Verificar c/ a família se o paciente é DPOC ou se possui alguma doença pulmonar, entrar em contato c/ a empresa e aguardar as orientações."], "correta": "89 de saturação. Verificar c/ a família se o paciente é DPOC ou se possui alguma doença pulmonar, entrar em contato c/ a empresa e aguardar as orientações."},
    {"id": 23, "texto": "Paciente está tendo uma hipoglicemia o que você pode ofertar p/ que o paciente recupere a sua glicose:", "opcoes": ["A-Água c/ açúcar", "B-Fruta inteira", "C-Mel", "D-A C e a B estão corretas."], "correta": " C-Mel"},
    {"id": 24, "texto": "Para um atendimento com segurança:", "opcoes": ["Você deve manter as unhas cortadas, retirar os adornos, fazer uso de touca e se precisar máscara. Porque esses itens fazem parte do atendimento com segurança?", "Pois o paciente pode arrancar num momento de agressividade do paciente.", "Para a proteção do paciente não é utilizado adornos pois trazem consigo contaminações. A touca para a própria segurança e transparece higiene.", "Não é ético nem higiênico usar brincos e anéis pois coloca a segurança do paciente em risco."], "correta": "Para a proteção do paciente não é utilizado adornos pois trazem consigo contaminações. A touca para a própria segurança e transparece higiene."},
    {"id": 25, "texto": "Porque os responsáveis pelos idosos contratam uma empresa de cuidadoria esperando ter um cuidado de excelência dos seus 'entes':", "opcoes": ["Porque precisam trabalhar p/ levar o sustento.", "Porque amam seus entes e precisam de uma pessoa para não deixá-los sozinhos.", "Porque o abandono do idoso é crime conforme previsto no artigo 133 do Cód. Penal (abandono de incapaz) com pena entre 2 a 5 anos de reclusão.", "Todas as alternativas acima estão corretas."], "correta": "Todas as alternativas acima estão corretas."}
]

# =============================
# ROTAS PÚBLICAS
# =============================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Página Inicial: Prova Santer Saúde"""
    perguntas = deepcopy(PERGUNTAS)
    random.shuffle(perguntas)
    for p in perguntas:
        random.shuffle(p["opcoes"])
    return templates.TemplateResponse("index.html", {"request": request, "perguntas": perguntas})

@app.get("/cadastro", response_class=HTMLResponse)
async def pagina_cadastro(request: Request):
    """Página de Cadastro de Candidatos"""
    return templates.TemplateResponse("cadastro.html", {"request": request})

@app.post("/cadastrar_candidato")
async def cadastrar_candidato(
    nome: str = Form(...),
    telefone: str = Form(...),
    bairro: str = Form(...),         # Adicionado: Recebe o bairro do formulário
    horarios: list = Form([]),       # Mudado para [] para não dar erro se nada for marcado
    servico: str = Form(...),
    tipo_plantao: list = Form([]),   # Mudado para [] para segurança
    turno: list = Form([])           # Mudado para [] para segurança
):
    # Transformamos as listas em texto separado por vírgula
    horarios_str = ", ".join(horarios)
    tipo_str = ", ".join(tipo_plantao)
    turno_str = ", ".join(turno)
    
    data_atual = datetime.now(timezone_br).strftime("%d/%m/%Y %H:%M")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Atualizamos o INSERT para incluir a coluna 'bairro'
    cur.execute(
        """INSERT INTO candidatos 
           (nome, telefone, bairro, horarios, ja_presta_servico, data_cadastro, tipo_plantao, turno) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (nome, telefone, bairro, horarios_str, servico, data_atual, tipo_str, turno_str)
    )
    
    conn.commit()
    cur.close()
    conn.close()
    
    return HTMLResponse("<script>alert('Cadastro realizado com sucesso!'); window.location.href='/cadastro';</script>")

@app.post("/api/salvar-usuario")
async def salvar_usuario(dados: dict):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Verifica se o usuário já existe, se não, cria
    cur.execute("""
        INSERT INTO candidatos (nome, email, foto_url) 
        VALUES (%s, %s, %s)
        ON CONFLICT (email) DO UPDATE SET nome = EXCLUDED.nome
    """, (dados['nome'], dados['email'], dados['foto']))
    
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "sucesso"}





@app.get("/verificar_codigo/{codigo}")
async def verificar_codigo(codigo: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT usado FROM codigos_validos WHERE codigo = %s", (codigo.upper(),))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result is None: return {"status": "erro", "mensagem": "Inexistente"}
    if result[0]: return {"status": "erro", "mensagem": "Usado"}
    return {"status": "sucesso"}

@app.get("/api/bairros")
async def listar_bairros():
    conn = get_db_connection()
    cur = conn.cursor()
    # Pega nomes de bairros únicos, ignorando vazios e ordenando
    cur.execute("SELECT DISTINCT bairro FROM candidatos WHERE bairro IS NOT NULL AND bairro != '' ORDER BY bairro ASC")
    bairros = [linha[0] for linha in cur.fetchall()]
    cur.close()
    conn.close()
    return bairros

    
    
@app.post("/submit")
async def submit(request: Request, nome: str = Form(...), codigo: str = Form(...), fraude: str = Form(None)):
    codigo = codigo.strip().upper()
    form_data = await request.form()
    foi_fraude = (fraude == "true")
    nome_final = f"{nome} (FRAUDE)" if foi_fraude else nome
    acertos = 0
    
    if not foi_fraude:
        for p in PERGUNTAS:
            resp = form_data.get(f"pergunta_{p['id']}")
            if resp and resp.strip() == p["correta"].strip():
                acertos += 1

    data_atual = datetime.now(timezone_br).strftime("%d/%m/%Y %H:%M")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO resultados (nome, codigo, nota, data) VALUES (%s, %s, %s, %s)", (nome_final, codigo, acertos, data_atual))
    cur.execute("UPDATE codigos_validos SET usado = TRUE WHERE codigo = %s", (codigo,))
    conn.commit()
    cur.close()
    conn.close()

    # Renderiza a página de resultado
    return templates.TemplateResponse("resultado.html", {
        "request": request, 
        "nome": nome_final, 
        "acertos": acertos, 
        "total": len(PERGUNTAS), 
        "fraude": foi_fraude
    })
    return templates.TemplateResponse("resultado.html", {"request": request, "nome": nome_final, "acertos": acertos, "total": len(PERGUNTAS), "fraude": foi_fraude})

@app.get("/health-check")
async def health_check():
    return {"status": "still_alive"}

# =============================
# ADMINISTRAÇÃO
# =============================

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return """
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>Login</title></head>
<body style="display:flex; justify-content:center; align-items:center; height:100vh; background:#2c3e50; font-family:sans-serif;">
<div style="background:#fff; padding:30px; border-radius:10px;">
    <h2>Painel Admin</h2>
    <form action="/admin" method="post">
        <input name="user" placeholder="Usuário" required style="width:100%; margin-bottom:10px; padding:8px;"><br>
        <input type="password" name="password" placeholder="Senha" required style="width:100%; margin-bottom:20px; padding:8px;"><br>
        <button type="submit" style="width:100%; padding:10px; background:#1abc9c; color:white; border:none; cursor:pointer;">Entrar</button>
    </form>
</div>
</body>
</html>
"""

@app.post("/admin")
async def admin_login(user: str = Form(...), password: str = Form(...)):
    if user == "leandro" and password == "14562917776":
        response = RedirectResponse("/admin", status_code=303)
        response.set_cookie("admin", "logado", httponly=True)
        return response
    return RedirectResponse("/login")

@app.get("/admin", response_class=HTMLResponse)
async def painel_admin(request: Request):
    # 1. Conecta ao banco
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # 2. BUSCA OS CÓDIGOS
    cur.execute("SELECT codigo FROM codigos_validos WHERE usado = FALSE ORDER BY codigo DESC")
    codigos_db = cur.fetchall()

    # 3. Busca Resultados e Candidatos
    cur.execute("SELECT * FROM resultados ORDER BY nota DESC")
    resultados_db = cur.fetchall()
    
    cur.execute("SELECT * FROM candidatos ORDER BY id DESC")
    candidatos_db = cur.fetchall()

    # --- NOVO: BUSCA BAIRROS ÚNICOS PARA O FILTRO ---
    cur.execute("SELECT DISTINCT bairro FROM candidatos WHERE bairro IS NOT NULL AND bairro != '' ORDER BY bairro ASC")
    bairros_db = [linha['bairro'] for linha in cur.fetchall()]

    cur.close()
    conn.close()

    # 4. Renderiza a página passando as QUATRO listas
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "codigos": codigos_db,
        "resultados": resultados_db,
        "candidatos": candidatos_db,
        "bairros_unicos": bairros_db  # <--- Enviando a lista de bairros para o HTML
    })
@app.post("/gerar")
async def gerar_codigo():
    codigo = secrets.token_hex(3).upper()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO codigos_validos (codigo, usado) VALUES (%s, FALSE)",
        (codigo,)
    )

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(url="/admin", status_code=303)

@app.get("/resultados", response_class=HTMLResponse)
async def resultados_publicos(request: Request):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # 1. Busca Resultados da Prova
    cur.execute("""
        SELECT nome, codigo, nota, data 
        FROM resultados 
        ORDER BY nota DESC, TO_TIMESTAMP(data, 'DD/MM/YYYY HH24:MI') ASC
    """)
    dados_provas = cur.fetchall()

    # 2. Busca Candidatos
    cur.execute("""
        SELECT nome, telefone, bairro, horarios, ja_presta_servico, data_cadastro, tipo_plantao, turno 
        FROM candidatos 
        ORDER BY id DESC
    """)
    dados_candidatos = cur.fetchall()

    # 3. NOVO: Busca apenas os bairros únicos que já estão cadastrados para o Filtro
    cur.execute("SELECT DISTINCT bairro FROM candidatos WHERE bairro IS NOT NULL AND bairro != '' ORDER BY bairro ASC")
    bairros_unicos = [linha['bairro'] for linha in cur.fetchall()]

    cur.close()
    conn.close()

    # Gerar opções para o SELECT de bairros
    opcoes_bairros = '<option value="todos">Bairro: Todos</option>'
    for b in bairros_unicos:
        opcoes_bairros += f'<option value="{b.lower()}">{b}</option>'

    # Gerar linhas da tabela de PROVAS
    linhas_provas = ""
    for r in dados_provas:
        tag_fraude = '<span style="color:red; font-size:10px"> [FRAUDE]</span>' if "(FRAUDE)" in r['nome'] else ""
        linhas_provas += f"""
        <tr>
            <td style="padding:12px; border-bottom:1px solid #eee">{r['nome']}{tag_fraude}</td>
            <td style="padding:12px; border-bottom:1px solid #eee">{r['codigo']}</td>
            <td style="padding:12px; border-bottom:1px solid #eee"><strong>{r['nota']}</strong></td>
            <td style="padding:12px; border-bottom:1px solid #eee">{r['data']}</td>
        </tr>
        """

    # Gerar linhas da tabela de CANDIDATOS
    linhas_candidatos = ""
    for c in dados_candidatos:
        tel_limpo = c['telefone'].replace('(','').replace(')','').replace('-','').replace(' ','')
        tipo = (c['tipo_plantao'] or "").lower()
        turno = (c['turno'] or "").lower()
        bairro_val = (c['bairro'] or "Não informado")
        
        linhas_candidatos += f"""
        <tr class="linha-candidato" 
            data-horarios="{c['horarios'].lower()}" 
            data-nome="{c['nome'].lower()}"
            data-bairro="{bairro_val.lower()}"
            data-tipo="{tipo}"
            data-turno="{turno}">
            <td style="padding:12px; border-bottom:1px solid #eee">{c['nome']}</td>
            <td style="padding:12px; border-bottom:1px solid #eee">
                <a href="https://wa.me/55{tel_limpo}" target="_blank" style="background:#25D366; color:white; padding:4px 8px; border-radius:4px; text-decoration:none; font-size:12px">
                    📱 {c['telefone']}
                </a>
            </td>
            <td style="padding:12px; border-bottom:1px solid #eee">{bairro_val}</td>
            <td style="padding:12px; border-bottom:1px solid #eee"><strong>{c['horarios']}</strong></td>
            <td style="padding:12px; border-bottom:1px solid #eee; font-size:12px">{c['tipo_plantao'] or ''} / {c['turno'] or ''}</td>
            <td style="padding:12px; border-bottom:1px solid #eee">{c['ja_presta_servico']}</td>
            <td style="padding:12px; border-bottom:1px solid #eee; font-size:11px; color:#888">{c['data_cadastro']}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Painel de Resultados - Santer Saúde</title>
        <style>
            .filter-box {{ background:white; padding:15px; margin-bottom:15px; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.05); display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
            input, select {{ padding:8px; border-radius:5px; border:1px solid #ccc; }}
            th {{ text-align:left; padding:12px; }}
            .linha-candidato:hover {{ background:#f9f9f9; }}
        </style>
    </head>
    <body style="font-family:Arial, sans-serif; background:#f4f6f8; padding:30px">

        <div style="max-width:1200px; margin:auto">
            <h2 style="color:#2a5298">📝 Resultados das Provas</h2>
            <table style="width:100%; border-collapse:collapse; background:white; box-shadow:0 10px 30px rgba(0,0,0,.1); margin-bottom:50px">
                <tr style="background:#2a5298; color:white">
                    <th>Nome</th><th>Código</th><th>Nota</th><th>Data</th>
                </tr>
                {linhas_provas}
            </table>

            <h2 style="color:#1abc9c">📋 Candidatos Interessados</h2>

            <div class="filter-box">
                <strong>🔍 Filtros:</strong>
                <input type="text" id="buscaNome" placeholder="Nome..." onkeyup="filtrarTudo()" style="width:180px">
                
                <select id="filtroBairro" onchange="filtrarTudo()">
                    {opcoes_bairros}
                </select>
                
                <select id="filtroHorario" onchange="filtrarTudo()">
                    <option value="todos">Carga: Todas</option>
                    <option value="8">8h</option><option value="12">12h</option><option value="24">24h</option><option value="48">48h</option>
                </select>

                <select id="filtroTipo" onchange="filtrarTudo()">
                    <option value="todos">Vínculo: Todos</option>
                    <option value="fixo">Fixo</option>
                    <option value="coringa">Coringa</option>
                </select>

                <select id="filtroTurno" onchange="filtrarTudo()">
                    <option value="todos">Turno: Todos</option>
                    <option value="diurno">Diurno</option>
                    <option value="noturno">Noturno</option>
                </select>

                <span id="contador" style="font-weight:bold; color:#1abc9c"></span>
            </div>

            <table id="tabelaCandidatos" style="width:100%; border-collapse:collapse; background:white; box-shadow:0 10px 30px rgba(0,0,0,.1)">
                <tr style="background:#1abc9c; color:white">
                    <th style="padding:12px">Nome</th>
                    <th>WhatsApp</th>
                    <th>Bairro</th>
                    <th>Disponibilidade</th>
                    <th>Tipo/Turno</th>
                    <th>É Santer?</th>
                    <th>Data Cadastro</th>
                </tr>
                {linhas_candidatos}
            </table>
        </div>

        <script>
        function filtrarTudo() {{
            const buscaN = document.getElementById('buscaNome').value.toLowerCase();
            const filtroB = document.getElementById('filtroBairro').value.toLowerCase();
            const filtroH = document.getElementById('filtroHorario').value;
            const filtroT = document.getElementById('filtroTipo').value;
            const filtroTur = document.getElementById('filtroTurno').value;
            
            const linhas = document.getElementsByClassName('linha-candidato');
            let visiveis = 0;

            for (let i = 0; i < linhas.length; i++) {{
                const nome = linhas[i].getAttribute('data-nome');
                const bairro = linhas[i].getAttribute('data-bairro');
                const horarios = linhas[i].getAttribute('data-horarios');
                const tipo = linhas[i].getAttribute('data-tipo');
                const turno = linhas[i].getAttribute('data-turno');

                const bateNome = nome.includes(buscaN);
                const bateBairro = (filtroB === "todos") || (bairro === filtroB);
                const bateHorario = (filtroH === "todos") || (horarios.includes(filtroH));
                const bateTipo = (filtroT === "todos") || (tipo.includes(filtroT));
                const bateTurno = (filtroTur === "todos") || (turno.includes(filtroTur));

                if (bateNome && bateBairro && bateHorario && bateTipo && bateTurno) {{
                    linhas[i].style.display = "";
                    visiveis++;
                }} else {{
                    linhas[i].style.display = "none";
                }}
            }}
            document.getElementById('contador').innerText = "(" + visiveis + " encontrados)";
        }}
        window.onload = filtrarTudo;
        </script>
    </body>
    </html>
    """






















