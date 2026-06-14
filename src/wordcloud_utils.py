import matplotlib.pyplot as plt
from wordcloud import WordCloud
import pandas as pd

# Liste de mots vides en français à exclure
FRENCH_STOP_WORDS = {
    # Mots demandés
    "le", "la", "les", "de", "des", "un", "une", "et", "à", "du", "pour", "avec", "dans",
    # Mots supplémentaires pour un meilleur rendu
    "en", "au", "aux", "par", "sur", "pas", "que", "qui", "est", "sont", "ce", "ces", 
    "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses", "notre", "nos", 
    "votre", "vos", "leur", "leurs", "je", "tu", "il", "elle", "nous", "vous", 
    "ils", "elles", "se", "ne", "y", "ou", "mais", "donc", "car", "ni", "si"
}

def generate_wordcloud(df: pd.DataFrame) -> plt.Figure:
    """
    Génère un nuage de mots à partir du DataFrame de réponses.
    Exclut les mots vides en français.
    Retourne une Figure Matplotlib ou None s'il n'y a pas de données.
    """
    if df.empty or 'response_text' not in df.columns:
        return None
        
    # Nettoyer et joindre toutes les réponses en une seule chaîne de texte
    all_text = " ".join(df['response_text'].dropna().astype(str))
    
    # Vérifier s'il y a du contenu après nettoyage
    if not all_text.strip():
        return None

    # Création du nuage de mots
    # colormap 'Blues' pour respecter le style STM
    wc = WordCloud(
        width=800,
        height=400,
        background_color='white',
        colormap='Blues',
        stopwords=FRENCH_STOP_WORDS,
        collocations=False,  # Évite les répétitions de bigrammes
        random_state=42
    ).generate(all_text)
    
    # Génération de la figure matplotlib
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='white')
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    plt.tight_layout(pad=0)
    
    return fig
