@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%EPICONTROL_PYTHON%"
if not defined PYTHON set "PYTHON=%LOCALAPPDATA%\Python\bin\python.exe"
if not exist "%PYTHON%" (
  for /f "delims=" %%I in ('where python 2^>nul') do if not defined PYTHON_FOUND set "PYTHON_FOUND=%%I"
  if defined PYTHON_FOUND set "PYTHON=%PYTHON_FOUND%"
)
if not exist "%PYTHON%" (
  echo ERRO: instale Python 3.11 ou superior para preparar o pacote.
  pause
  exit /b 1
)

"%PYTHON%" -c "import PyInstaller, sqlalchemy, reportlab, openpyxl"
if errorlevel 1 (
  echo ERRO: faltam dependencias de build. Instale app\requirements.txt e PyInstaller.
  pause
  exit /b 1
)

if not exist "app\assets\icone_sistema.ico" (
  echo ERRO: app\assets\icone_sistema.ico nao encontrado.
  pause
  exit /b 1
)
if not exist "app\MANUAL_DE_INSTRUCOES.md" (
  echo ERRO: app\MANUAL_DE_INSTRUCOES.md nao encontrado.
  pause
  exit /b 1
)

"%PYTHON%" PREPARAR_BANCO_EXE.py
if errorlevel 1 exit /b 1

set "EPICONTROL_WORKPATH=build_instalacao_%RANDOM%"
"%PYTHON%" -m PyInstaller --clean --noconfirm --distpath dist_instalacao --workpath "%EPICONTROL_WORKPATH%" EpiControl.spec
if errorlevel 1 (
  echo ERRO ao gerar EpiControl.exe.
  pause
  exit /b 1
)

set "ISCC=%EPICONTROL_ISCC%"
for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%I"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo EpiControl.exe foi gerado em dist_instalacao.
  echo Para compilar o instalador, instale Inno Setup 6 e execute este arquivo novamente.
  pause
  exit /b 2
)

"%ISCC%" Instalador_EpiControl.iss
if errorlevel 1 (
  echo ERRO ao compilar o instalador.
  pause
  exit /b 1
)

rmdir /s /q "%EPICONTROL_WORKPATH%"
echo Instalador criado em dist_instalador\EpiControlSetup-1.0.1.exe
echo Nenhum banco de dados, certificado ou configuracao local foi incluido.
pause
