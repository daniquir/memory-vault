"""Internationalization (i18n) system for bilingual support."""

import os
import locale
from pathlib import Path
from typing import Dict


class I18n:
    """Manages translations for English and Spanish."""
    
    # Default translations
    TRANSLATIONS = {
        "en_US": {
            "setup_welcome": "Welcome to The Memory Vault Setup",
            "setup_bucket": "Enter your Wasabi bucket name:",
            "setup_access_key": "Enter your Wasabi Access Key ID:",
            "setup_secret_key": "Enter your Wasabi Secret Access Key:",
            "setup_region": "Enter Wasabi region (default: us-east-1):",
            "setup_password": "Enter encryption password for snapshots:",
            "setup_object_lock": "Enable Object Lock (WORM mode)? (y/n, default: y):",
            "setup_lock_days": "Enter lock retention days (default: 90):",
            "setup_success": "Setup completed successfully!",
            "setup_error": "Setup failed: {}",
            "open_mounting": "Mounting vault...",
            "open_success": "Vault mounted at {}",
            "open_error": "Failed to mount: {}",
            "close_unmounting": "Unmounting vault...",
            "close_success": "Vault unmounted successfully",
            "close_error": "Failed to unmount: {}",
            "snap_creating": "Creating snapshot...",
            "snap_success": "Snapshot created: {}",
            "snap_error": "Failed to create snapshot: {}",
            "snap_no_path": "No path specified for snapshot",
            "list_snapshots": "Snapshots for host '{}':",
            "list_no_snapshots": "No snapshots found",
            "list_all_devices": "All registered devices:",
            "restore_restoring": "Restoring snapshot {} to {}...",
            "restore_success": "Restore completed successfully",
            "restore_error": "Failed to restore: {}",
            "config_current": "Current sync folders: {}",
            "config_add": "Add folder to sync (or 'done' to finish):",
            "config_remove": "Remove folder from sync (or 'done' to finish):",
            "config_saved": "Configuration saved",
            "shield_enabling": "Enabling RM-Shield...",
            "shield_disabling": "Disabling RM-Shield...",
            "shield_enabled": "RM-Shield enabled in shell config",
            "shield_disabled": "RM-Shield disabled",
            "shield_error": "Failed to modify shell config: {}",
            "status_mounted": "Mounted: {}",
            "status_not_mounted": "Not mounted",
            "status_last_snap": "Last snapshot: {}",
            "status_no_snap": "No snapshots yet",
            "status_space": "Used space: {}",
            "status_error": "Failed to get status: {}",
            "error_not_configured": "Vault not configured. Run 'vault setup' first.",
            "error_worm_enabled": "Cannot delete: Object Lock is enabled",
            "error_invalid_id": "Invalid snapshot ID: {}",
            "error_path_not_found": "Path not found: {}",
            # GUI translations
            "gui_title": "The Memory Vault",
            "gui_dashboard": "Dashboard",
            "gui_snapshots": "Snapshots",
            "gui_sync": "Sync",
            "gui_logs": "Logs",
            "gui_setup": "Setup",
            "gui_edit": "Edit Configuration",
            "gui_open_vault": "Open Vault",
            "gui_close_vault": "Close Vault",
            "gui_sync_folders": "Sync Folders",
            "gui_create_snapshot": "Create Snapshot",
            "gui_list_snapshots": "List Snapshots",
            "gui_add_folder": "Add Folder",
            "gui_remove_folder": "Remove Folder",
            "gui_clear_logs": "Clear Logs",
            "gui_rm_shield": "RM-Shield",
            "gui_auto_sync": "Auto-Sync (every 5 min)",
            "gui_emergency_actions": "Emergency Actions",
            "gui_panic_button": "PANIC: Emergency Close",
            "gui_config_status": "Configuration Status",
            "gui_sync_configured": "Sync Configured",
            "gui_snapshots_configured": "Snapshots Configured",
            "gui_shield_enabled": "RM-Shield Enabled",
            "gui_auto_sync_enabled": "Auto-Sync Enabled",
            "gui_quick_actions": "Quick Actions",
            "gui_language": "Language",
            "gui_snapshots_management": "Snapshots Management",
            "gui_sync_folders_config": "Sync Folders Configuration",
            "gui_activity_logs": "Activity Logs",
            "gui_shield_subtitle": "Protect against accidental rm commands by replacing with trash",
            "gui_auto_sync_subtitle": "Automatically sync configured folders to Wasabi every 5 minutes",
            "gui_sync_filter": "Sync Filter",
            "gui_no_errors": "No errors",
            "gui_syncing": "Syncing",
            "gui_errors": "Errors",
            "gui_security_center": "Security Center"
        },
        "es_ES": {
            "setup_welcome": "Bienvenido a la configuración de The Memory Vault",
            "setup_bucket": "Introduce el nombre de tu bucket Wasabi:",
            "setup_access_key": "Introduce tu Access Key ID de Wasabi:",
            "setup_secret_key": "Introduce tu Secret Access Key de Wasabi:",
            "setup_region": "Introduce la región Wasabi (por defecto: us-east-1):",
            "setup_password": "Introduce la contraseña de cifrado para snapshots:",
            "setup_object_lock": "¿Activar Object Lock (modo Búnker)? (y/n, por defecto: y):",
            "setup_lock_days": "Introduce días de retención (por defecto: 90):",
            "setup_success": "¡Configuración completada con éxito!",
            "setup_error": "La configuración falló: {}",
            "open_mounting": "Montando el baúl...",
            "open_success": "Baúl montado en {}",
            "open_error": "Fallo al montar: {}",
            "close_unmounting": "Desmontando el baúl...",
            "close_success": "Baúl desmontado con éxito",
            "close_error": "Fallo al desmontar: {}",
            "snap_creating": "Creando snapshot...",
            "snap_success": "Snapshot creado: {}",
            "snap_error": "Fallo al crear snapshot: {}",
            "snap_no_path": "No se especificó ruta para el snapshot",
            "list_snapshots": "Snapshots para el host '{}':",
            "list_no_snapshots": "No se encontraron snapshots",
            "list_all_devices": "Todos los dispositivos registrados:",
            "restore_restoring": "Restaurando snapshot {} a {}...",
            "restore_success": "Restauración completada con éxito",
            "restore_error": "Fallo al restaurar: {}",
            "config_current": "Carpetas de sincronización actuales: {}",
            "config_add": "Añadir carpeta a sincronizar (o 'done' para terminar):",
            "config_remove": "Eliminar carpeta de sincronización (o 'done' para terminar):",
            "config_saved": "Configuración guardada",
            "shield_enabling": "Activando RM-Shield...",
            "shield_disabling": "Desactivando RM-Shield...",
            "shield_enabled": "RM-Shield activado en la configuración del shell",
            "shield_disabled": "RM-Shield desactivado",
            "shield_error": "Fallo al modificar configuración del shell: {}",
            "status_mounted": "Montado: {}",
            "status_not_mounted": "No montado",
            "status_last_snap": "Último snapshot: {}",
            "status_no_snap": "Sin snapshots aún",
            "status_space": "Espacio usado: {}",
            "status_error": "Fallo al obtener estado: {}",
            "error_not_configured": "Baúl no configurado. Ejecuta 'vault setup' primero.",
            "error_worm_enabled": "No se puede eliminar: Object Lock está activado",
            "error_invalid_id": "ID de snapshot inválido: {}",
            "error_path_not_found": "Ruta no encontrada: {}",
            # GUI translations
            "gui_title": "The Memory Vault",
            "gui_dashboard": "Panel",
            "gui_snapshots": "Snapshots",
            "gui_sync": "Sincronización",
            "gui_logs": "Registros",
            "gui_setup": "Configurar",
            "gui_edit": "Editar Configuración",
            "gui_open_vault": "Abrir Baúl",
            "gui_close_vault": "Cerrar Baúl",
            "gui_sync_folders": "Sincronizar Carpetas",
            "gui_create_snapshot": "Crear Snapshot",
            "gui_list_snapshots": "Ver Snapshots",
            "gui_add_folder": "Añadir Carpeta",
            "gui_remove_folder": "Eliminar Carpeta",
            "gui_clear_logs": "Limpiar Registros",
            "gui_rm_shield": "RM-Shield",
            "gui_auto_sync": "Auto-Sync (cada 5 min)",
            "gui_emergency_actions": "Acciones de Emergencia",
            "gui_panic_button": "PÁNICO: Cierre de Emergencia",
            "gui_config_status": "Estado de Configuración",
            "gui_sync_configured": "Sincronización Configurada",
            "gui_snapshots_configured": "Snapshots Configurados",
            "gui_shield_enabled": "RM-Shield Activado",
            "gui_auto_sync_enabled": "Auto-Sync Activado",
            "gui_quick_actions": "Acciones Rápidas",
            "gui_language": "Idioma",
            "gui_snapshots_management": "Gestión de Snapshots",
            "gui_sync_folders_config": "Configuración de Sincronización",
            "gui_activity_logs": "Registros de Actividad",
            "gui_shield_subtitle": "Protege contra comandos rm accidentales reemplazándolos con papelera",
            "gui_auto_sync_subtitle": "Sincroniza automáticamente las carpetas configuradas con Wasabi cada 5 minutos",
            "gui_sync_filter": "Filtro de Sincronización",
            "gui_no_errors": "Sin errores",
            "gui_syncing": "Sincronizando",
            "gui_errors": "Errores",
            "gui_security_center": "Centro de Seguridad"
        }
    }
    
    def __init__(self, language: str = "auto"):
        """Initialize i18n system.
        
        Args:
            language: Language code ('auto', 'en_US', 'es_ES')
        """
        self.language = self._detect_language(language)
        self.translations = self.TRANSLATIONS.get(self.language, self.TRANSLATIONS["en_US"])
    
    def _detect_language(self, language: str) -> str:
        """Detect system language or use specified language.
        
        Args:
            language: Language code or 'auto'
        
        Returns:
            Detected language code
        """
        if language != "auto":
            return language if language in self.TRANSLATIONS else "en_US"
        
        # Detect from system locale
        try:
            system_lang = locale.getdefaultlocale()[0]
            if system_lang:
                if system_lang.startswith("es"):
                    return "es_ES"
                elif system_lang.startswith("en"):
                    return "en_US"
        except (ValueError, AttributeError):
            pass
        
        # Check LANG environment variable
        lang_env = os.environ.get("LANG", "")
        if lang_env.startswith("es"):
            return "es_ES"
        elif lang_env.startswith("en"):
            return "en_US"
        
        # Default to English
        return "en_US"
    
    def t(self, key: str, *args) -> str:
        """Get translated string.
        
        Args:
            key: Translation key
            *args: Arguments for string formatting
        
        Returns:
            Translated string
        """
        template = self.translations.get(key, key)
        if args:
            return template.format(*args)
        return template
    
    def set_language(self, language: str) -> None:
        """Set language manually.
        
        Args:
            language: Language code ('en_US', 'es_ES')
        """
        if language in self.TRANSLATIONS:
            self.language = language
            self.translations = self.TRANSLATIONS[language]
