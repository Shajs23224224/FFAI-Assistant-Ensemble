package com.ffai.assistant.cloud

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.ffai.assistant.config.Constants
import com.ffai.assistant.utils.Logger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.util.concurrent.TimeUnit
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * Worker de backup local (sin Google Drive).
 * Maneja backup de modelos, checkpoints y datos de aprendizaje en almacenamiento local.
 * IA 100% local - sin conexión a internet requerida.
 */
class BackupWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    companion object {
        const val WORK_NAME = "ffai_backup_worker"
        const val ONE_TIME_WORK_NAME = "ffai_backup_one_time"
        
        // Input data keys
        const val KEY_SYNC_MODELS = "sync_models"
        const val KEY_SYNC_DATA = "sync_data"
        const val KEY_FORCE_SYNC = "force_sync"
        
        // Output data keys
        const val KEY_RESULT_SUCCESS = "result_success"
        const val KEY_RESULT_MESSAGE = "result_message"
        const val KEY_FILES_BACKED_UP = "files_backed_up"
    }

    private lateinit var localSyncManager: LocalSyncManager
    private val context = applicationContext

    override suspend fun doWork(): Result {
        Logger.i("BackupWorker", "Iniciando backup local")
        
        val syncModels = inputData.getBoolean(KEY_SYNC_MODELS, true)
        val syncData = inputData.getBoolean(KEY_SYNC_DATA, true)
        
        return try {
            localSyncManager = LocalSyncManager(context)
            
            var filesBackedUp = 0
            
            // Backup de modelos
            if (syncModels) {
                filesBackedUp += backupModels()
            }
            
            // Backup de datos de aprendizaje
            if (syncData) {
                filesBackedUp += backupLearningData()
            }
            
            // Limpiar backups antiguos
            localSyncManager.cleanupOldBackups()
            
            // Actualizar timestamp de último backup
            localSyncManager.updateLastBackupTime()
            
            val message = "Backup local completado: $filesBackedUp archivos respaldados"
            Logger.i("BackupWorker", message)
            
            Result.success(workDataOf(
                KEY_RESULT_SUCCESS to true,
                KEY_RESULT_MESSAGE to message,
                KEY_FILES_BACKED_UP to filesBackedUp
            ))
            
        } catch (e: Exception) {
            Logger.e("BackupWorker", "Error en backup local", e)
            Result.retry()
        }
    }

    /**
     * Backup de modelos locales.
     * @return Número de archivos respaldados
     */
    private suspend fun backupModels(): Int = withContext(Dispatchers.IO) {
        var backedUp = 0
        
        try {
            val modelDir = File(context.getExternalFilesDir(null), Constants.MODEL_DIR)
            
            // Backup modelo actual si existe
            val currentModel = File(modelDir, Constants.MODEL_CURRENT)
            if (currentModel.exists()) {
                localSyncManager.backupFile(currentModel, LocalSyncManager.FOLDER_MODELS)
                backedUp++
                
                // También backup con timestamp
                val timestamp = System.currentTimeMillis()
                val backupName = "model_backup_${timestamp}.tflite"
                localSyncManager.backupFile(currentModel, LocalSyncManager.FOLDER_BACKUP, backupName)
                backedUp++
            }
            
        } catch (e: Exception) {
            Logger.e("BackupWorker", "Error en backup de modelos", e)
        }
        
        backedUp
    }

    /**
     * Backup de datos de aprendizaje locales.
     * @return Número de archivos respaldados
     */
    private suspend fun backupLearningData(): Int = withContext(Dispatchers.IO) {
        var backedUp = 0
        
        try {
            // Comprimir base de datos SQLite
            val dbFile = context.getDatabasePath(Constants.DB_NAME)
            if (dbFile.exists()) {
                val zipFile = File(context.cacheDir, "experiences_backup.zip")
                compressFile(dbFile, zipFile)
                
                // Backup local
                localSyncManager.backupFile(zipFile, LocalSyncManager.FOLDER_DATA, "experiences_backup.zip")
                backedUp++
                
                zipFile.delete()
            }
            
        } catch (e: Exception) {
            Logger.e("BackupWorker", "Error en backup de datos", e)
        }
        
        backedUp
    }

    /**
     * Comprime un archivo en ZIP.
     */
    private fun compressFile(sourceFile: File, zipFile: File) {
        ZipOutputStream(zipFile.outputStream()).use { zos ->
            val entry = ZipEntry(sourceFile.name)
            zos.putNextEntry(entry)
            sourceFile.inputStream().use { input ->
                input.copyTo(zos)
            }
            zos.closeEntry()
        }
    }

    /**
     * Descomprime un archivo ZIP.
     */
    private fun decompressFile(zipFile: File, destinationDir: File) {
        destinationDir.mkdirs()
        java.util.zip.ZipInputStream(zipFile.inputStream()).use { zis ->
            var entry = zis.nextEntry
            while (entry != null) {
                val newFile = File(destinationDir, entry.name)
                if (entry.isDirectory) {
                    newFile.mkdirs()
                } else {
                    newFile.parentFile?.mkdirs()
                    newFile.outputStream().use { output ->
                        zis.copyTo(output)
                    }
                }
                zis.closeEntry()
                entry = zis.nextEntry
            }
        }
    }

    /**
     * Configura observador de progreso.
     */
    private fun setupProgressCallback() {
        driveSyncManager.syncProgressCallback = { progress ->
            when (progress) {
                is SyncProgress.Uploading -> {
                    val percent = if (progress.totalBytes > 0) {
                        ((progress.bytesUploaded * 100) / progress.totalBytes).toInt()
                    } else 0
                    setProgressAsync(workDataOf(
                        "progress_type" to "uploading",
                        "file_name" to progress.fileName,
                        "percent" to percent
                    ))
                }
                is SyncProgress.Downloading -> {
                    val percent = if (progress.totalBytes > 0) {
                        ((progress.bytesDownloaded * 100) / progress.totalBytes).toInt()
                    } else 0
                    setProgressAsync(workDataOf(
                        "progress_type" to "downloading",
                        "file_id" to progress.fileId,
                        "percent" to percent
                    ))
                }
                else -> {}
            }
        }
    }
}

/**
 * Helper para programar trabajos de sincronización.
 */
object BackupScheduler {
    
    /**
     * Programa sincronización periódica.
     * Por defecto: cada 6 horas, solo WiFi, solo cuando carga.
     */
    fun schedulePeriodicSync(
        context: Context,
        repeatInterval: Long = 6,
        timeUnit: TimeUnit = TimeUnit.HOURS,
        requireWifi: Boolean = true,
        requireCharging: Boolean = true
    ) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(if (requireWifi) NetworkType.UNMETERED else NetworkType.CONNECTED)
            .setRequiresCharging(requireCharging)
            .build()
        
        val workRequest = PeriodicWorkRequestBuilder<BackupWorker>(
            repeatInterval, timeUnit
        )
            .setConstraints(constraints)
            .addTag(BackupWorker.WORK_NAME)
            .build()
        
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            BackupWorker.WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            workRequest
        )
        
        Logger.i("BackupScheduler", "Backup local periódico programado cada $repeatInterval $timeUnit")
    }
    
    /**
     * Ejecuta backup local único inmediato.
     */
    fun runOneTimeBackup(
        context: Context,
        syncModels: Boolean = true,
        syncData: Boolean = true,
        forceSync: Boolean = false
    ) {
        val inputData = workDataOf(
            BackupWorker.KEY_SYNC_MODELS to syncModels,
            BackupWorker.KEY_SYNC_DATA to syncData,
            BackupWorker.KEY_FORCE_SYNC to forceSync
        )
        
        val workRequest = OneTimeWorkRequestBuilder<BackupWorker>()
            .setInputData(inputData)
            .addTag(BackupWorker.ONE_TIME_WORK_NAME)
            .build()
        
        WorkManager.getInstance(context).enqueue(workRequest)
        
        Logger.i("BackupScheduler", "Backup local one-time programado")
    }
    
    /**
     * Cancela todas las sincronizaciones.
     */
    fun cancelAllSync(context: Context) {
        WorkManager.getInstance(context).cancelAllWorkByTag(BackupWorker.WORK_NAME)
        WorkManager.getInstance(context).cancelAllWorkByTag(BackupWorker.ONE_TIME_WORK_NAME)
        Logger.i("BackupScheduler", "Todos los backups cancelados")
    }
    
    /**
     * Verifica si hay sincronización en progreso.
     */
    suspend fun isSyncInProgress(context: Context): Boolean {
        val workManager = WorkManager.getInstance(context)
        val workInfos = workManager.getWorkInfosByTag(BackupWorker.ONE_TIME_WORK_NAME)
        
        return workInfos.any { 
            it.state == WorkInfo.State.RUNNING || it.state == WorkInfo.State.ENQUEUED 
        }
    }
    
    /**
     * Obtiene información de última sincronización.
     */
    suspend fun getLastSyncInfo(context: Context): SyncInfo? {
        val workManager = WorkManager.getInstance(context)
        val workInfos = workManager.getWorkInfosByTag(BackupWorker.WORK_NAME)
        
        return workInfos.lastOrNull()?.let { workInfo ->
            SyncInfo(
                state = workInfo.state.name,
                lastSyncTime = workInfo.runAttemptCount,
                outputData = workInfo.outputData
            )
        }
    }
}

/**
 * Información de sincronización.
 */
data class SyncInfo(
    val state: String,
    val lastSyncTime: Int,
    val outputData: androidx.work.Data
)
