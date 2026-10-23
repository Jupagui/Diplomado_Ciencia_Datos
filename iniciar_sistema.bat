@echo off
cd /d %~dp0
color 0A
echo ===================================================
echo   INICIADOR AUTOMATICO DE MICRONEGOCIO
echo ===================================================
echo.

echo [1/4] Preparando entorno Backend...
cd backend
if not exist venv (
    echo Creando entorno virtual de Python...
    python -m venv venv
)
echo Activando entorno virtual...
call .\venv\Scripts\activate
echo Instalando y actualizando dependencias del Backend...
pip install -r requirements.txt
if not exist .env (
    echo Creando .env a partir de .env.example...
    copy .env.example .env >nul
)
cd ..

echo.
echo [2/4] Preparando entorno Frontend...
cd frontend
echo Instalando librerias del Frontend, esto puede tomar unos minutos...
call npm install
if not exist .env (
    copy .env.example .env >nul
)
cd ..

echo.
echo [3/4] Levantando servidor Backend (FastAPI)...
start "MICRONEGOCIO Backend" cmd /k "color 0B && cd /d %~dp0backend && call .\venv\Scripts\activate && echo Levantando Backend en puerto 8010... && uvicorn app.main:app --port 8010 --reload"

echo.
echo [4/4] Levantando servidor Frontend (React/Vite)...
start "MICRONEGOCIO Frontend" cmd /k "color 0E && cd /d %~dp0frontend && echo Levantando Frontend en puerto 5180... && npm run dev"

echo.
echo ===================================================
echo        INSTALACION Y LANZAMIENTO COMPLETADOS
echo ===================================================
echo.
echo - El Backend y el Frontend se abrieron en ventanas nuevas.
echo - La primera vez el backend siembra datos sinteticos (unos 20 s).
echo - No cierres esas ventanas mientras uses la aplicacion.
echo.
echo Accede a la plataforma: http://localhost:5180
echo Usuario demo: admin   Contrasena: admin123
echo Documentacion de la API: http://localhost:8010/docs
echo.
pause
