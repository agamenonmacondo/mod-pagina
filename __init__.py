# Paquete llmpagina
# Este archivo permite que el directorio sea importable

import sys
import os

# Añadir el directorio raíz al path de Python
root_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(root_dir)

# Añadir tanto la ruta actual como la ruta padre al path de Python
# para permitir importaciones desde ambas ubicaciones
if root_dir not in sys.path:
    sys.path.append(root_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

print(f"Initialized paths: Added {root_dir} and {parent_dir} to sys.path") 