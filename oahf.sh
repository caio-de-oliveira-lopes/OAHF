#!/bin/bash
set -e  # Encerra o script se algum comando falhar

echo "Running: python setup.py sdist bdist_wheel"
python setup.py sdist bdist_wheel || {
    echo "Failed to build the distribution."
    exit 1
}

echo "Running: pip install ."
pip install . || {
    echo "Failed to install the package."
    exit 1
}

echo "Commands executed successfully."

read -p "Pressione Enter para sair..."  # equivalente ao 'pause' do Windows