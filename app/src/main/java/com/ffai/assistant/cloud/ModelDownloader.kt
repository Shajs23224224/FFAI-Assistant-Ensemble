package com.ffai.assistant.cloud

import android.content.Context
import com.ffai.assistant.config.Constants
import com.ffai.assistant.utils.Logger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.withContext
import java.io.File
import java.util.zip.ZipInputStream

/**
 * IA 100% LOCAL - Gestor de modelos local.
 * 
 * En modo offline, los modelos se gestionan localmente mediante:
 * - LocalSyncManager para backup/restore
 * - Modelos empaquetados en assets (para distribución)
 * - Sin descargas externas requeridas
 */
class ModelDownloader(private val context: Context) {

    companion object {
        const val BUFFER_SIZE = 8192
        const val MIN_VALID_MODEL_SIZE = 1024 * 1024 // 1MB
    }

    private val modelDir = File(context.getExternalFilesDir(null), Constants.MODEL_DIR).apply { mkdirs() }
    private val tempDir = File(context.cacheDir, "model_downloads").apply { mkdirs() }

    /**
     * STUB: Descarga desde Drive deshabilitada (modo 100% local).
     * 
     * En modo offline, los modelos deben estar:
     * 1. Incluidos en assets/ del APK
     * 2. Copiados localmente via LocalSyncManager
     * 
     * @param fileId Ignorado en modo local
     * @param fileName Nombre del modelo a verificar
     * @return Flow indicando error (descargas no disponibles)
     */
    fun downloadModel(
        fileId: String,
        fileName: String,
        authToken: String? = null
    ): Flow<DownloadProgress> = flow {
        emit(DownloadProgress.Error("Descargas deshabilitadas - Sistema 100% offline. Use modelos locales."))
    }.flowOn(Dispatchers.IO)

    /**
     * Verifica si un modelo existe localmente.
     */
    fun isModelAvailableLocally(fileName: String): Boolean {
        return File(modelDir, fileName).exists()
    }

    /**
     * Copia modelo desde assets si está disponible.
     */
    suspend fun copyModelFromAssets(assetName: String, destFileName: String): Boolean = withContext(Dispatchers.IO) {
        return@withContext try {
            val destFile = File(modelDir, destFileName)
            context.assets.open(assetName).use { input ->
                destFile.outputStream().use { output ->
                    input.copyTo(output)
                }
            }
            Logger.i("ModelDownloader", "Modelo copiado desde assets: $destFileName")
            true
        } catch (e: Exception) {
            Logger.e("ModelDownloader", "Error copiando modelo desde assets", e)
            false
        }
    }

    /**
     * Lista modelos disponibles localmente.
     */
    fun listLocalModels(): List<LocalModelInfo> {
        return modelDir.listFiles { file ->
            file.extension == "tflite" || file.extension == "lite"
        }?.map { file ->
            LocalModelInfo(
                name = file.name,
                path = file.absolutePath,
                size = file.length(),
                lastModified = file.lastModified()
            )
        } ?: emptyList()
    }

    /**
     * Verifica integridad de archivo de modelo.
     */
    fun isValidModelFile(file: File): Boolean {
        return file.exists() && 
               file.length() >= MIN_VALID_MODEL_SIZE &&
               (file.name.endsWith(".tflite") || file.name.endsWith(".pt") || file.name.endsWith(".pth"))
    }

    /**
     * Descomprime un modelo ZIP.
     */
    suspend fun unzipModel(zipFile: File, destinationDir: File = modelDir): File? = withContext(Dispatchers.IO) {
        return@withContext try {
            var extractedFile: File? = null
            
            ZipInputStream(zipFile.inputStream()).use { zis ->
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
                        
                        if (entry.name.endsWith(".tflite")) {
                            extractedFile = newFile
                        }
                    }
                    
                    zis.closeEntry()
                    entry = zis.nextEntry
                }
            }
            
            zipFile.delete()
            extractedFile
        } catch (e: Exception) {
            Logger.e("ModelDownloader", "Error descomprimiendo", e)
            null
        }
    }

    /**
     * Limpia archivos temporales.
     */
    fun cleanupTempFiles() {
        tempDir.listFiles()?.forEach { it.delete() }
    }
}

/**
 * Información de modelo local.
 */
data class LocalModelInfo(
    val name: String,
    val path: String,
    val size: Long,
    val lastModified: Long
)

/**
 * Estados de progreso.
 */
sealed class DownloadProgress {
    data class Starting(val fileName: String) : DownloadProgress()
    data class Downloading(val fileName: String, val bytesDownloaded: Long, val totalBytes: Long) : DownloadProgress()
    data class Success(val file: File, val fileSize: Long) : DownloadProgress()
    data class Error(val message: String) : DownloadProgress()
    
    /**
     * Porcentaje de progreso (0-100).
     */
    val percent: Int
        get() = when (this) {
            is Downloading -> {
                if (totalBytes > 0) {
                    ((bytesDownloaded * 100) / totalBytes).toInt()
                } else 0
            }
            is Success -> 100
            else -> 0
        }
}

/**
 * Resultado de operación.
 */
sealed class DownloadResult {
    data class Success(val file: File, val fileSize: Long) : DownloadResult()
    data class Error(val message: String) : DownloadResult()
}
