from sentence_transformers import SentenceTransformer
from pathlib import Path

model = SentenceTransformer('all-MiniLM-L6-v2')
RUTA_PENDIENTES = Path("pendientes_revision.csv")