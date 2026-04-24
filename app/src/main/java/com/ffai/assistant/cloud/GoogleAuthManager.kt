package com.ffai.assistant.cloud

import android.app.Activity
import android.content.Context
import android.content.Intent
import com.ffai.assistant.utils.Logger

/**
 * IA 100% LOCAL - Stub de autenticación (sin Google Sign-In).
 * 
 * Este gestor está deshabilitado porque el sistema funciona 100% offline.
 * No requiere conexión a internet ni servicios de Google.
 * 
 * Para reactivar autenticación cloud, restaurar implementación original.
 */
class GoogleAuthManager(private val context: Context) {

    companion object {
        const val RC_SIGN_IN = 9001
        const val PREFS_NAME = "auth_prefs"
        const val KEY_DEVICE_ID = "device_id"
    }

    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    init {
        Logger.i("AuthManager", "Modo 100% local - Sin autenticación externa requerida")
    }

    /**
     * STUB: Sign-In deshabilitado (IA 100% local).
     */
    fun signIn(activity: Activity, callback: (Result<LocalAccount>) -> Unit) {
        Logger.w("AuthManager", "Sign-In deshabilitado - Sistema 100% offline")
        callback(Result.failure(Exception("Autenticación deshabilitada - modo offline")))
    }

    /**
     * STUB: No requiere manejo de resultados de Sign-In.
     */
    fun handleSignInResult(requestCode: Int, resultCode: Int, data: Intent?) {
        // No-op en modo offline
    }

    /**
     * STUB: Sign-Out deshabilitado.
     */
    fun signOut(callback: ((Boolean) -> Unit)? = null) {
        prefs.edit().clear().apply()
        Logger.i("AuthManager", "Sign-out local completado")
        callback?.invoke(true)
    }

    /**
     * STUB: Revoke deshabilitado.
     */
    fun revokeAccess(callback: ((Boolean) -> Unit)? = null) {
        prefs.edit().clear().apply()
        Logger.i("AuthManager", "Acceso local limpiado")
        callback?.invoke(true)
    }

    /**
     * En modo offline siempre retorna false.
     */
    fun isSignedIn(): Boolean = false

    /**
     * Retorna cuenta local genérica.
     */
    fun getCurrentAccount(): LocalAccount? {
        return LocalAccount(
            id = getDeviceId(),
            name = "Local Device",
            type = "offline"
        )
    }

    /**
     * Obtiene ID único del dispositivo para identificación local.
     */
    fun getDeviceId(): String {
        var deviceId = prefs.getString(KEY_DEVICE_ID, null)
        if (deviceId == null) {
            deviceId = java.util.UUID.randomUUID().toString()
            prefs.edit().putString(KEY_DEVICE_ID, deviceId).apply()
        }
        return deviceId
    }

    /**
     * STUB: No hay tokens en modo offline.
     */
    fun getIdToken(): String? = null

    /**
     * STUB: No hay auth codes en modo offline.
     */
    fun getServerAuthCode(): String? = null

    /**
     * STUB: Silent sign-in siempre falla en modo offline.
     */
    fun silentSignIn(callback: (Result<LocalAccount>) -> Unit) {
        callback(Result.failure(Exception("Silent sign-in no disponible en modo offline")))
    }

    /**
     * STUB: No hay tokens que refrescar.
     */
    suspend fun refreshAccessToken(): String? = null
}

/**
 * Datos de cuenta local (reemplaza GoogleAccount).
 */
data class LocalAccount(
    val id: String,
    val name: String,
    val type: String = "offline"
)

// Alias para compatibilidad
@Deprecated("Usar LocalAccount", ReplaceWith("LocalAccount"))
typealias GoogleAccount = LocalAccount
