#!/bin/bash

# Verificar que token.txt existe
if [ ! -f "token.txt" ]; then
    echo "El archivo token.txt no existe."
    exit 1
fi

# Leer token desde el archivo
TOKEN=$(<token.txt)

# Verificar que el token no esté vacío
if [ -z "$TOKEN" ]; then
    echo "El token está vacío. Edita token.txt e intenta de nuevo."
    exit 1
fi

# Ejecutar el script Python con el token
python3 main.py "$TOKEN"
