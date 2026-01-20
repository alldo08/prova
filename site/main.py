import psycopg2
import psycopg2.extras
import random
import secrets
import pytz
from datetime import datetime
from copy import deepcopy
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# CONFIGURAÇÃO DO SUPABASE (Substituí o sqlite3 por psycopg2)
# Substituí [provasanter] pela senha que você forneceu no URI
DATABASE_URL = "postgresql://postgres.cemkjzuumwucitxgoeem:provasanter@aws-0-sa-east-1.pooler.supabase.com:5432/postgres"
app = FastAPI()
templates = Jinja2Templates(directory="templates")
timezone_br = pytz.timezone('America/Sao_Paulo')

def get_db_connection():
    # Cria a conexão com o Supabase
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Inicialização do Banco (Agora no PostgreSQL)
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # No Postgres usamos SERIAL para IDs automáticos e TEXT para strings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resultados (
            id SERIAL PRIMARY KEY,
            nome TEXT,
            codigo TEXT,
            nota INTEGER,
            data TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS codigos_validos (
            codigo TEXT PRIMARY KEY,
            usado INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

init_db()

PERGUNTAS = [
    {"id": 1, "texto": "Ao chegar na residência para o plantão o que devemos primeiramente fazer?", "opcoes": ["Dar bom dia ou cumprimentar a todos da residência para dar inicio ao plantão.", "Entrar na residência, lavar as mãos trocar de roupae começar a trabalhar.", "Entrar na residencia, lavar as mãos e proceder com o metodo anti-covid(tomar banho, trocar de roupa) lavar as mãos novamente e cumprimentar a todos procurando saber as comorbidades do paciente", "Entrar, proceder com o metodo anti-covid e se dirigir ao paciente pos ele e responsavel por si mesmo"], "correta": "Entrar na residencia, lavar as mãos e proceder com o metodo anti-covid(tomar banho, trocar de roupa) lavar as mãos novamente e cumprimentar a todos procurando saber as comorbidades do paciente"},
    {"id": 2, "texto": "O que são comorbidades?", "opcoes": ["É a presença de uma doença contagiosa onde temos que manter isolado o paciente.", "É a ocorrência de duas ou mais doenças simultaneamente num mesmo paciente contraidas nos hospitais.", "É a presença de duas ou mais doenças ou condições de saúde simultâneas em um mesmo indivíduo.", "O termo se refere a doenças pré-existentes, que quando adquiridas em algum lugar podem agravar o quadro biológico."], "correta": "É a presença de duas ou mais doenças ou condições de saúde simultâneas em um mesmo indivíduo."},
    {"id": 3, "texto": "O nome dado ao aparelho para aferir a pressão arterial:", "opcoes": ["Estetoscopiômetro.", "Esfignomanômetro.", "Esfigmomanômetro.", "Digital Analógico P.A."], "correta": "Esfignomanômetro."},
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
    {"id": 20, "texto": "Diante de um idoso agressivo, qual a alternativa correta:", "opcoes": ["Manter distância.", "Buscar entender a causa.", "Pedir substituição do plantão.", "Responder igual para impor limites."], "correta": "Buscar entender a causa."}
]

@app.get("/verificar_codigo/{codigo}")
async def verificar_codigo(codigo: str):
    codigo = codigo.strip().upper()
    conn = get_db_connection()
    cursor = conn.cursor()
    # No Postgres usamos %s em vez de ?
    cursor.execute("SELECT usado FROM codigos_validos WHERE codigo = %s", (codigo,))
    resultado = cursor.fetchone()
    cursor.close()
    conn.close()

    if resultado is None:
        return {"status": "erro", "mensagem": "Código inexistente!"}
    elif resultado[0] == 1:
        return {"status": "erro", "mensagem": "Este código já foi usado!"}
    
    return {"status": "sucesso"} 

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    perguntas_aleatorias = deepcopy(PERGUNTAS)
    random.shuffle(perguntas_aleatorias)
    for p in perguntas_aleatorias:
        random.shuffle(p["opcoes"])
    return templates.TemplateResponse("index.html", {"request": request, "perguntas": perguntas_aleatorias})

@app.post("/submit")
async def submit(request: Request, nome: str = Form(...), codigo: str = Form(...)):
    codigo = codigo.strip().upper()
    form_data = await request.form()
    acertos = 0
    for p in PERGUNTAS:
        resposta_aluno = form_data.get(f"pergunta_{p['id']}")
        if resposta_aluno and str(resposta_aluno).strip() == str(p['correta']).strip():
            acertos += 1
    
    agora_br = datetime.now(timezone_br)
    data_formatada = agora_br.strftime("%d/%m/%Y %H:%M")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # %s para o Postgres
        cursor.execute("INSERT INTO resultados (nome, codigo, nota, data) VALUES (%s, %s, %s, %s)", 
                       (nome, codigo, acertos, data_formatada))
        cursor.execute("UPDATE codigos_validos SET usado = 1 WHERE codigo = %s", (codigo,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao salvar no banco: {e}")

    return templates.TemplateResponse("resultado.html", {
        "request": request, "nome": nome, "acertos": acertos, "total": len(PERGUNTAS)
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return """
    <html>
    <head><title>Login Admin</title></head>
    <body style="font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh; background:#f4f4f9; margin:0;">
        <form action="/admin" method="post" style="background:white; padding:40px; border-radius:12px; box-shadow:0 10px 25px rgba(0,0,0,0.1); width:300px;">
            <h2 style="text-align:center; color:#2c3e50;">Acesso Admin</h2>
            <input type="text" name="user" placeholder="Usuário" required style="width:100%; padding:12px; margin:10px 0; border:1px solid #ddd; border-radius:6px; box-sizing:border-box;">
            <input type="password" name="password" placeholder="Senha" required style="width:100%; padding:12px; margin:10px 0; border:1px solid #ddd; border-radius:6px; box-sizing:border-box;">
            <button type="submit" style="width:100%; padding:12px; background:#3498db; color:white; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">Entrar</button>
        </form>
    </body>
    </html>
    """

@app.get("/admin", response_class=HTMLResponse)
@app.post("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, user: str = Form(None), password: str = Form(None)):
    if request.method == "POST" and user:
        if user != "leandro" or password != "14562917776":
            return "<h1>Acesso Negado</h1><a href='/login'>Voltar</a>"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, codigo, nota, data FROM resultados ORDER BY data DESC")
    res = cursor.fetchall()
    cursor.execute("SELECT codigo FROM codigos_validos WHERE usado = 0")
    cods = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return templates.TemplateResponse("admin.html", {"request": request, "resultados": res, "codigos": cods})

@app.post("/gerar")
async def gerar_codigo():
    novo_codigo = secrets.token_hex(3).upper() 
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO codigos_validos (codigo, usado) VALUES (%s, 0)", (novo_codigo,))
    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse(url="/admin", status_code=303)

