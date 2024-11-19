@echo off
setlocal

echo Running: python setup.py sdist bdist_wheel
python setup.py sdist bdist_wheel

if %ERRORLEVEL% NEQ 0 (
    echo Failed to build the distribution.
    exit /b %ERRORLEVEL%
)

echo Running: pip install .
pip install .

if %ERRORLEVEL% NEQ 0 (
    echo Failed to install the package.
    exit /b %ERRORLEVEL%
)

echo Commands executed successfully.
endlocal
pause
