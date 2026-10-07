@echo off
setlocal
cd /d "%~dp0"

echo [1/6] Creating virtual environment...
if not exist ".venv\Scripts\python.exe" python -m venv .venv
call ".venv\Scripts\activate.bat"

echo [2/6] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [3/6] Creating .env...
if not exist ".env" copy /Y ".env.example" ".env" >nul

echo [4/6] Running migrations...
python manage.py migrate
if errorlevel 1 goto :error

echo [5/6] Importing 8,151 fuel stations and batch geocoding...
python manage.py import_fuel_prices data\fuel-prices.csv --geocode
if errorlevel 1 goto :error

echo [6/6] Running Django checks...
python manage.py check
if errorlevel 1 goto :error

echo.
echo Setup complete. Start the app with:
echo   .venv\Scripts\activate
echo   python manage.py runserver
echo.
echo Then open http://127.0.0.1:8000/
exit /b 0

:error
echo.
echo Setup failed. Read the error above.
exit /b 1
