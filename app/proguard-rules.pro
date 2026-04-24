# ProGuard rules
# Keep class names for debugging
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile

# TensorFlow Lite
-keep class org.tensorflow.lite.** { *; }
-keep class org.tensorflow.lite.gpu.** { *; }

# OpenCV
-keep class org.bytedeco.opencv.** { *; }
-keep class org.bytedeco.javacpp.** { *; }

# SocketIO
-keep class io.socket.** { *; }
-keep class io.socket.engineio.** { *; }
-keep class io.socket.client.** { *; }
-keepattributes *Annotation*
-keepattributes Signature
-keepattributes Exceptions
-dontwarn io.socket.**

# OkHttp (SocketIO dependency)
-keep class okhttp3.** { *; }
-keep interface okhttp3.** { *; }
-dontwarn okhttp3.**
-dontwarn okio.**

# Sistema 100% Local - Cloud classes (mantener nombres para compatibilidad)
-keep class com.ffai.assistant.cloud.LocalSyncManager { *; }
-keep class com.ffai.assistant.cloud.GoogleAuthManager { *; }
-keep class com.ffai.assistant.cloud.ModelDownloader { *; }
-keep class com.ffai.assistant.cloud.BackupWorker { *; }
-keep class com.ffai.assistant.cloud.LocalAccount { *; }

# WorkManager
-keep class androidx.work.** { *; }

# Kotlin Serialization
-keepattributes *Annotation*
-keep class kotlinx.serialization.** { *; }
-dontwarn kotlinx.serialization.**

# Remove logging calls in release builds
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
    public static *** i(...);
    public static *** w(...);
    public static *** e(...);
}
