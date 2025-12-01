from . import model

def embed(text: str):
    """
    Genera un embedding normalizado para el texto dado.
    Retorna una lista de floats.
    """
    vec = model.encode([text])[0].astype("float32")
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()