import os
import random
import secrets
import pytz
from datetime import datetime
from copy import deepcopy

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# =============================
# CONFIGURAÇÃO
# =============================

DATABASE_URL=postgresql://postgres:provasanter@aws-0-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require


timezone_br = pytz.timezone("America/Sao_Paulo")

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# =============================
# BANCO DE DADOS
# =============================

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS resultados (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            codigo TEXT NOT NULL,
            nota INTEGER NOT NULL,
            data TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS codigos_validos (
            codigo TEXT PRIMARY KEY,
            usado BOOLEAN DEFAULT FALSE
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


@app.on_event("startup")
def startup():
    try:
        init_db()
        print("Banco inicializado com sucesso")
    except Exception as e:
        print("Erro ao inicializar banco:", e)

# =============================
# PERGUNTAS
# =============================

PERGUNTAS = [
    {"id": 1, "texto": "Ao chegar na residência para o plantão o que devemos primeiramente fazer?", "opcoes": ["Dar bom dia ou cumprimentar a todos da residência para dar inicio ao plantão.", "Entrar na residência, lavar as mãos trocar de roupae começar a trabalhar.", "Entrar na residencia, lavar as mãos e proceder com o metodo anti-covid(tomar banho, trocar de roupa) lavar as mãos novamente e cumprimentar a todos procurando saber as comorbidades do paciente", "Entrar, proceder com o metodo anti-covid e se dirigir ao paciente pos ele e responsavel por si mesmo"], "correta": "Entrar na residencia, lavar as mãos e proceder com o metodo anti-covid(tomar banho, trocar de roupa) lavar as mãos novamente e cumprimentar a todos procurando saber as comorbidades do paciente"},
    {"id": 2, "texto": "O que são comorbidades?", "opcoes": ["É a presença de uma doença contagiosa onde temos que manter isolado o paciente.", "É a ocorrência de duas ou mais doenças simultaneamente num mesmo paciente contraidas nos hospitais.", "É a presença de duas ou mais doenças ou condições de saúde simultâneas em um mesmo indivíduo.", "O termo se refere a doenças pré-existentes, que quando adquiridas em algum lugar podem agravar o quadro biológico."], "correta": "É a presença de duas ou mais doenças ou condições de saúde simultâneas em um mesmo indivíduo."}
]

# =============================
# ROTAS
# =============================

@app.get("/verificar_codigo/{codigo}")
async def verificar_codigo(codigo: str):
    codigo = codigo.strip().upper()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT usado FROM codigos_validos WHERE codigo = %s", (codigo,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if row is None:
        return {"status": "erro", "mensagem": "Código inexistente"}
    if row[0]:
        return {"status": "erro", "mensagem": "Código já utilizado"}

    return {"status": "sucesso"}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    perguntas = deepcopy(PERGUNTAS)
    random.shuffle(perguntas)
    for p in perguntas:
        random.shuffle(p["opcoes"])

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "perguntas": perguntas}
    )


@app.post("/submit")
async def submit(request: Request, nome: str = Form(...), codigo: str = Form(...)):
    codigo = codigo.strip().upper()
    form_data = await request.form()

    acertos = 0
    for p in PERGUNTAS:
        resposta = form_data.get(f"pergunta_{p['id']}")
        if resposta and resposta.strip() == p["correta"].strip():
            acertos += 1

    data = datetime.now(timezone_br).strftime("%d/%m/%Y %H:%M")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO resultados (nome, codigo, nota, data) VALUES (%s, %s, %s, %s)",
        (nome, codigo, acertos, data)
    )

    cur.execute(
        "UPDATE codigos_validos SET usado = TRUE WHERE codigo = %s",
        (codigo,)
    )

    conn.commit()
    cur.close()
    conn.close()

    return templates.TemplateResponse(
        "resultado.html",
        {"request": request, "nome": nome, "acertos": acertos, "total": len(PERGUNTAS)}
    )


@app.get("/login", response_class=HTMLResponse)
async def login():
    return """
    <h2>Login Admin</h2>
    <form method='post' action='/admin'>
        <input name='user' placeholder='Usuário'><br>
        <input type='password' name='password' placeholder='Senha'><br>
        <button>Entrar</button>
    </form>
    """


@app.api_route("/admin", methods=["GET", "POST"], response_class=HTMLResponse)
async def admin(request: Request, user: str = Form(None), password: str = Form(None)):
    if request.method == "POST":
        if user != "leandro" or password != "14562917776":
            raise HTTPException(status_code=403, detail="Acesso negado")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT nome, codigo, nota, data FROM resultados ORDER BY id DESC")
    resultados = cur.fetchall()

    cur.execute("SELECT codigo FROM codigos_validos WHERE usado = FALSE")
    codigos = cur.fetchall()

    cur.close()
    conn.close()

    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "resultados": resultados, "codigos": codigos}
    )


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

