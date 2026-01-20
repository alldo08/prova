import os
import random
import secrets
import pytz
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

# =============================
# CONFIGURAÇÃO
# =============================

DATABASE_URL = os.getenv("DATABASE_URL").strip()


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
    {"id": 20, "texto": "Diante de um idoso agressivo, qual a alternativa correta:", "opcoes": ["Manter distância.", "Buscar entender a causa.", "Pedir substituição do plantão.", "Responder igual para impor limites."], "correta": "Buscar entender a causa."}
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
async def login_page():
    return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Login Admin</title>
</head>
<body style="
    margin:0;
    height:100vh;
    display:flex;
    justify-content:center;
    align-items:center;
    background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);
    font-family:Segoe UI,Tahoma,sans-serif;
">

<div style="
    background:#fff;
    width:340px;
    padding:40px;
    border-radius:16px;
    box-shadow:0 30px 70px rgba(0,0,0,.3);
">

<h2 style="text-align:center;margin-bottom:25px;color:#2c3e50;">
    🔐 Área Administrativa
</h2>

<form action="/admin" method="post">
    <label style="font-size:14px;color:#555;">Usuário</label>
    <input name="user" required
        style="
            width:100%;
            padding:12px;
            margin:6px 0 16px;
            border-radius:8px;
            border:1px solid #ccc;
            font-size:14px;
        ">

    <label style="font-size:14px;color:#555;">Senha</label>
    <div style="position:relative;">
        <input id="senha" type="password" name="password" required
            style="
                width:100%;
                padding:12px 40px 12px 12px;
                margin:6px 0 22px;
                border-radius:8px;
                border:1px solid #ccc;
                font-size:14px;
            ">
        <span onclick="toggleSenha()"
            style="
                position:absolute;
                right:12px;
                top:50%;
                transform:translateY(-50%);
                cursor:pointer;
                color:#777;
                font-size:14px;
            ">👁</span>
    </div>

    <button type="submit"
        style="
            width:100%;
            padding:12px;
            border:none;
            border-radius:8px;
            background:#2c5364;
            color:white;
            font-size:15px;
            font-weight:600;
            cursor:pointer;
        ">
        Entrar
    </button>
</form>

<p style="text-align:center;margin-top:20px;font-size:12px;color:#999;">
    Acesso restrito
</p>

</div>

<script>
function toggleSenha(){
    const s = document.getElementById("senha");
    s.type = s.type === "password" ? "text" : "password";
}
</script>

</body>
</html>
"""


@app.post("/admin")
async def admin_login(request: Request, user: str = Form(...), password: str = Form(...)):
    if user != "leandro" or password != "14562917776":
        return HTMLResponse("""
        <script>
            alert("Usuário ou senha inválidos");
            window.location.href = "/login";
        </script>
        """)

    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie("admin", "logado", httponly=True)
    return response


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    if request.cookies.get("admin") != "logado":
        return RedirectResponse("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, codigo, nota, data FROM resultados ORDER BY data DESC")
    res = cursor.fetchall()
    cursor.execute("SELECT codigo FROM codigos_validos WHERE usado = false")
    cods = cursor.fetchall()
    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "resultados": res, "codigos": cods}
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

@app.get("/resultados/csv")
def exportar_resultados_csv():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        nome,
        nota,
        data
    FROM resultados
    ORDER BY nota DESC, data ASC
""")

    dados = cursor.fetchall()

    cursor.close()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    # cabeçalho
    writer.writerow(["Nome", "Acertos", "Total", "Data"])

    for nome, acertos, total, data in dados:
        writer.writerow([nome, acertos, total, data.strftime("%d/%m/%Y")])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=resultados_prova.csv"
        }
    )


@app.get("/resultados", response_class=HTMLResponse)
async def resultados_publicos():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        nome,
        codigo,
        nota,
        TO_CHAR(data::date, 'DD/MM/YYYY') AS data
    FROM resultados
    ORDER BY nota DESC, data::date ASC
""")

    dados = cursor.fetchall()

    cursor.close()
    conn.close()

    linhas = ""
    for nome, codigo, nota, data in dados:
        linhas += f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #eee">{nome}</td>
            <td style="border-bottom:1px solid #eee">{codigo}</td>
            <td style="border-bottom:1px solid #eee;font-weight:bold">{nota}</td>
            <td style="border-bottom:1px solid #eee">{data}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Resultados da Prova</title>
    </head>
    <body style="font-family:Arial; background:#f4f6f8; padding:30px">

        <div style="max-width:900px;margin:auto">

            <div style="display:flex;justify-content:space-between;align-items:center">
                <h2>Resultados da Prova</h2>

                <a href="/resultados/csv" style="
                    background:#2a5298;
                    color:white;
                    padding:10px 16px;
                    border-radius:6px;
                    text-decoration:none;
                    font-weight:bold;
                ">
                    ⬇ Exportar CSV
                </a>
            </div>

            <table style="
                width:100%;
                margin-top:15px;
                border-collapse:collapse;
                background:white;
                box-shadow:0 10px 30px rgba(0,0,0,.1)
            ">
                <tr style="background:#2a5298;color:white">
                    <th style="padding:12px">Nome</th>
                    <th>Código</th>
                    <th>Nota</th>
                    <th>Data</th>
                </tr>
                {linhas}
            </table>

        </div>

    </body>
    </html>
    """









