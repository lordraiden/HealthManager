# Internationalization module for Blood Work Tracker
translations = {
    'es': {
        'settings': 'Ajustes',
        'language': 'Idioma',
        'english': 'Inglés',
        'spanish': 'Español',
        'dashboard': 'Panel Principal',
        'patients': 'Pacientes',
        'reports': 'Informes',
        'documents': 'Documentos',
        'analytics': 'Analíticas',
        'ai_consultation': 'Consulta IA',
        'logout': 'Cerrar Sesión',
        'login': 'Iniciar Sesión',
        'username': 'Nombre de usuario',
        'password': 'Contraseña',
        'remember_me': 'Recordarme',
        'blood_work_tracker': 'Blood Work Tracker',
        'manage_your_lab_results': 'Gestiona tus resultados de laboratorio',
        'welcome_back': 'Bienvenido de nuevo',
        'select_language': 'Seleccionar Idioma',
        'save_settings': 'Guardar Ajustes',
        'settings_saved': 'Ajustes guardados correctamente'
    },
    'en': {
        'settings': 'Settings',
        'language': 'Language',
        'english': 'English',
        'spanish': 'Spanish',
        'dashboard': 'Dashboard',
        'patients': 'Patients',
        'reports': 'Reports',
        'documents': 'Documents',
        'analytics': 'Analytics',
        'ai_consultation': 'AI Consultation',
        'logout': 'Logout',
        'login': 'Login',
        'username': 'Username',
        'password': 'Password',
        'remember_me': 'Remember me',
        'blood_work_tracker': 'Blood Work Tracker',
        'manage_your_lab_results': 'Manage your lab results',
        'welcome_back': 'Welcome back',
        'select_language': 'Select Language',
        'save_settings': 'Save Settings',
        'settings_saved': 'Settings saved successfully'
    }
}


def get_text(key, lang='en'):
    """
    Get translated text based on key and language
    """
    if lang not in translations:
        lang = 'en'  # fallback to English
    
    return translations[lang].get(key, key)


def get_available_languages():
    """
    Get list of available languages
    """
    return [
        {'code': 'en', 'name': 'English'},
        {'code': 'es', 'name': 'Español'}
    ]