import io
import pandas as pd

def export_to_csv(df: pd.DataFrame) -> bytes:
    """
    Exporte le DataFrame en format CSV encodé en UTF-8-sig.
    L'encodage utf-8-sig ajoute un BOM (Byte Order Mark) indispensable
    pour que Microsoft Excel ouvre les caractères accentués français correctement.
    """
    if df.empty:
        return b""
    # Remplacer les retours à la ligne dans les réponses pour ne pas casser le CSV
    df_clean = df.copy()
    if 'response_text' in df_clean.columns:
        df_clean['response_text'] = df_clean['response_text'].astype(str).str.replace('\n', ' ', regex=False)
    
    # Utilisation de la virgule comme délimiteur standard
    return df_clean.to_csv(index=False).encode('utf-8-sig')

def export_to_excel(df: pd.DataFrame) -> bytes:
    """
    Exporte le DataFrame en format Excel (XLSX) en mémoire.
    Ajuste automatiquement la largeur des colonnes pour un rendu professionnel.
    """
    if df.empty:
        return b""
        
    df_clean = df.copy()
    # Renommer les colonnes pour l'export utilisateur
    column_mapping = {
        'id': 'ID',
        'question_id': 'ID Question',
        'question_text': 'Question',
        'response_text': 'Réponse',
        'created_at': 'Date de création'
    }
    df_clean = df_clean.rename(columns={k: v for k, v in column_mapping.items() if k in df_clean.columns})
    
    output = io.BytesIO()
    # xlsxwriter est robuste et performant
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_clean.to_excel(writer, index=False, sheet_name='Sondage STM')
        
        workbook  = writer.book
        worksheet = writer.sheets['Sondage STM']
        
        # Styles de formatage
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#005696',
            'font_color': 'white',
            'border': 1
        })
        
        # Appliquer les styles aux en-têtes
        for col_num, value in enumerate(df_clean.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        # Ajustement automatique de la largeur des colonnes
        for i, col in enumerate(df_clean.columns):
            # Calculer la longueur maximale du texte de la colonne
            max_len = max(
                df_clean[col].astype(str).map(len).max(),
                len(col)
            ) + 4
            # Limiter à 60 caractères pour éviter des colonnes trop larges en cas de longues phrases
            max_len = min(max_len, 60)
            worksheet.set_column(i, i, max_len)
            
    return output.getvalue()
