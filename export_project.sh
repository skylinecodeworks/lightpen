#!/usr/bin/env bash
#
# Genera un único fichero TXT que contiene:
# 1) El resultado de `tree` desde la raíz del proyecto (excluyendo .venv)
# 2) El contenido de todos los ficheros de texto, precedido por su ruta y nombre
#

OUTFILE="project_full.txt"

# 1) Eliminamos si existe el fichero de salida
[ -f "$OUTFILE" ] && rm "$OUTFILE"

# 2) Añadimos el árbol de directorios, ignorando .venv
echo "=== Árbol de directorios (sin .venv) ===" >> "$OUTFILE"
tree -I ".venv" . >> "$OUTFILE"

echo -e "\n\n=== Contenido de ficheros (sin .venv) ===\n" >> "$OUTFILE"

# 3) Recorremos todos los ficheros de texto, excluyendo .venv y el propio OUTFILE
find . \
  -path "./.venv" -prune \
  -o \
  -type f \( \
      -name '*.py'   -o \
      -name '*.html' -o \
      -name '*.css'  -o \
      -name '*.js'   -o \
      -name '*.json' -o \
      -name '*.md'   -o \
      -name '*.yaml' -o \
      -name '*.yml'  -o \
      -name '*.toml' -o \
      -name '*.env'  -o \
      -name '*.txt'  \
  \) ! -name "$(basename "$OUTFILE")" -print \
  | sort \
  | while read -r file; do
      echo "----- Fichero: $file -----" >> "$OUTFILE"
      cat "$file" >> "$OUTFILE"
      echo -e "\n" >> "$OUTFILE"
    done

echo "✅ Proyecto exportado en $OUTFILE (excluyendo .venv)"

