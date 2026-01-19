import sys
from pathlib import Path

# Adiciona o diretório pai ao path para funcionar quando executado diretamente
sys.path.insert(0, str(Path(__file__).parent.parent))

from mixtura.main import main

if __name__ == "__main__":
    main()
