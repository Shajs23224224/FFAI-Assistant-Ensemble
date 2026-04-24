package com.ffai.assistant.cloud

import android.content.Context
import android.content.SharedPreferences
import com.ffai.assistant.utils.Logger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

/**
 * IA 100% LOCAL - Sistema de backup local (sin Google Drive).
 * 
 * Este gestor maneja almacenamiento local de modelos, checkpoints y datos.
 * Todos los archivos se guardan en el dispositivo en /Android/data/com.ffai.assistant/files/
 * 
 * Características:
 * - Backup local automático
 * - Sin dependencias de cloud
 * - Optimizado para Samsung A21S
 * - Sin conexión a internet requerida
 */
class LocalSyncManager(private val context: Context) {

    companion object {
        const val PREFS_NAME = "local_sync_prefs"
        const val KEY_LAST_BACKUP = "last_backup_time"
        
        const val FOLDER_MODELS = "models"
        const val FOLDER_CHECKPOINTS = "checkpoints"
        const val FOLDER_DATA = "data"
        const val FOLDER_SESSIONS = "sessions"
        const val FOLDER_BACKUP = "backup"
        
        const val MAX_FILE_SIZE_MB = 100
    }

    private val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private val baseDir: File = context.getExternalFilesDir(null) ?: context.filesDir
    
    var syncProgressCallback: ((SyncProgress) -> Unit)? = null

    init {
        // Crear estructura de carpetas local
        createLocalStructure()
    }

    private fun createLocalStructure() {
        val folders = listOf(FOLDER_MODELS, FOLDER_CHECKPOINTS, FOLDER_DATA, FOLDER_SESSIONS, FOLDER_BACKUP)
        folders.forEach { folderName ->
            val folder = File(baseDir, folderName)
            if (!folder.exists()) {
                folder.mkdirs()
                Logger.i("LocalSyncManager", "Carpeta local creada: ${folder.absolutePath}")
            }
        }
    }

    fun getLocalFolder(folderName: String): File {
        return File(baseDir, folderName).apply {
            if (!exists()) mkdirs()
        }
    }

    /**
     * Copia un archivo a la carpeta local de backup.
     */
    suspend fun backupFile(
        sourceFile: File,
        folderName: String = FOLDER_MODELS,
        customName: String? = null
    ): String? = withContext(Dispatchers.IO) {
        return@withContext try {
            val fileName = customName ?: sourceFile.name
            val destFolder = getLocalFolder(folderName)
            val destFile = File(destFolder, fileName)
            
            syncProgressCallback?.invoke(SyncProgress.Uploading(fileName, 0, sourceFile.length()))
            
            // Copiar archivo
            sourceFile.copyTo(destFile, overwrite = true)
            
            Logger.i("LocalSyncManager", "Archivo respaldado localmente: ${destFile.absolutePath}")
            syncProgressCallback?.invoke(SyncProgress.UploadComplete(fileName, destFile.absolutePath))
            destFile.absolutePath
        } catch (e: Exception) {
            Logger.e("LocalSyncManager", "Error respaldando archivo", e)
            syncProgressCallback?.invoke(SyncProgress.Error("Backup failed: ${e.message}"))
            null
        }
    }

    /**
     * Restaura un archivo desde backup local.
     */
    suspend fun restoreFile(
        fileName: String,
        folderName: String = FOLDER_MODELS,
        destinationFile: File
    ): Boolean = withContext(Dispatchers.IO) {
        return@withContext try {
            val sourceFolder = getLocalFolder(folderName)
            val sourceFile = File(sourceFolder, fileName)
            
            if (!sourceFile.exists()) {
                Logger.w("LocalSyncManager", "Archivo no encontrado en backup: $fileName")
                return@withContext false
            }
            
            syncProgressCallback?.invoke(SyncProgress.Downloading(fileName, 0, sourceFile.length()))
            
            sourceFile.copyTo(destinationFile, overwrite = true)
            
            Logger.i("LocalSyncManager", "Archivo restaurado: ${destinationFile.absolutePath}")
            syncProgressCallback?.invoke(SyncProgress.DownloadComplete(fileName, destinationFile.length()))
            true
        } catch (e: Exception) {
            Logger.e("LocalSyncManager", "Error restaurando archivo", e)
            syncProgressCallback?.invoke(SyncProgress.Error("Restore failed: ${e.message}"))
            false
        }
    }

    /**
     * Lista archivos en carpeta local.
     */
    fun listLocalFiles(folderName: String = FOLDER_MODELS): List<LocalFile> {
        val folder = getLocalFolder(folderName)
        return folder.listFiles()?.map { file ->
            LocalFile(
                path = file.absolutePath,
                name = file.name,
                size = file.length(),
                modifiedTime = file.lastModified()
            )
        } ?: emptyList()
    }

    /**
     * Verifica si existe archivo local.
     */
    fun localFileExists(fileName: String, folderName: String = FOLDER_MODELS): Boolean {
        return File(getLocalFolder(folderName), fileName).exists()
    }

    /**
     * Elimina archivo local.
     */
    suspend fun deleteLocalFile(fileName: String, folderName: String = FOLDER_MODELS): Boolean = withContext(Dispatchers.IO) {
        return@withContext try {
            val file = File(getLocalFolder(folderName), fileName)
            if (file.exists()) {
                file.delete()
                Logger.i("LocalSyncManager", "Archivo eliminado: $fileName")
                true
            } else {
                false
            }
        } catch (e: Exception) {
            Logger.e("LocalSyncManager", "Error eliminando archivo", e)
            false
        }
    }

    /**
     * Limpia backups antiguos (más de 7 días).
     */
    suspend fun cleanupOldBackups(folderName: String = FOLDER_BACKUP, maxAgeDays: Int = 7): Int = withContext(Dispatchers.IO) {
        val folder = getLocalFolder(folderName)
        val cutoffTime = System.currentTimeMillis() - (maxAgeDays * 24 * 60 * 60 * 1000)
        var deletedCount = 0
        
        folder.listFiles()?.forEach { file ->
            if (file.lastModified() < cutoffTime) {
                file.delete()
                deletedCount++
            }
        }
        
        if (deletedCount > 0) {
            Logger.i("LocalSyncManager", "Limpieza completada: $deletedCount archivos antiguos eliminados")
        }
        deletedCount
    }

    /**
     * Obtiene fecha de último backup.
     */
    fun getLastBackupTime(): Long {
        return prefs.getLong(KEY_LAST_BACKUP, 0)
    }

    /**
     * Actualiza fecha de último backup.
     */
    fun updateLastBackupTime() {
        prefs.edit().putLong(KEY_LAST_BACKUP, System.currentTimeMillis()).apply()
    }

    /**
     * Obtiene espacio disponible en almacenamiento.
     */
    fun getAvailableSpace(): Long {
        return baseDir.usableSpace
    }

    /**
     * Obtiene tamaño total de backups.
     */
    fun getTotalBackupSize(): Long {
        return listOf(FOLDER_MODELS, FOLDER_CHECKPOINTS, FOLDER_DATA, FOLDER_SESSIONS, FOLDER_BACKUP)
            .sumOf { folderName ->
                getLocalFolder(folderName).listFiles()?.sumOf { it.length() } ?: 0L
            }
    }
}

/**
 * Representa un archivo local.
 */
data class LocalFile(
    val path: String,
    val name: String,
    val size: Long,
    val modifiedTime: Long
)

/**
 * Estados de progreso de sincronización local.
 */
sealed class SyncProgress {
    data class Uploading(val fileName: String, val bytesUploaded: Long, val totalBytes: Long) : SyncProgress()
    data class UploadComplete(val fileName: String, val filePath: String) : SyncProgress()
    data class Downloading(val fileName: String, val bytesDownloaded: Long, val totalBytes: Long) : SyncProgress()
    data class DownloadComplete(val fileName: String, val fileSize: Long) : SyncProgress()
    data class Error(val message: String) : SyncProgress()
    object SyncComplete : SyncProgress()
}

// Alias para compatibilidad - redirige a LocalSyncManager
@Deprecated("Usar LocalSyncManager directamente", ReplaceWith("LocalSyncManager"))
typealias DriveSyncManager = LocalSyncManager

@Deprecated("Usar LocalFile", ReplaceWith("LocalFile"))
typealias DriveFile = LocalFile
