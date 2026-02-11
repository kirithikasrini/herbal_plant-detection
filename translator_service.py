from deep_translator import GoogleTranslator
import concurrent.futures

def get_plant_translations(text):
    """
    Translates the given text (plant name) into Tamil, Hindi, and Telugu.
    Returns a dictionary of translations.
    """
    target_languages = {
        'Tamil': 'ta',
        'Hindi': 'hi',
        'Telugu': 'te'
    }
    
    translations = {}
    
    # Check if text is valid
    if not text or text == "Unknown":
        return {lang: "N/A" for lang in target_languages}

    def translate_to_lang(lang_name, lang_code):
        try:
            # Use GoogleTranslator
            translated = GoogleTranslator(source='auto', target=lang_code).translate(text)
            return lang_name, translated
        except Exception as e:
            print(f"Error translating to {lang_name}: {e}")
            return lang_name, text # Fallback to original text

    # Use threading for faster parallel translation
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_lang = {
            executor.submit(translate_to_lang, lang, code): lang 
            for lang, code in target_languages.items()
        }
        
        for future in concurrent.futures.as_completed(future_to_lang):
            lang_name, result = future.result()
            translations[lang_name] = result
            
    return translations
