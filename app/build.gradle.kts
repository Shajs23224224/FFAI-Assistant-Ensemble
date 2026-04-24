import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.serialization")
// FASE 1: CLOUD FEATURES DISABLED
// id("com.google.gms.google-services")
}

val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("keystore.properties")

if (keystorePropertiesFile.exists()) {
    keystorePropertiesFile.inputStream().use(keystoreProperties::load)
}

fun signingValue(propertyName: String, envName: String): String? {
    val propertyValue = keystoreProperties.getProperty(propertyName)
    if (!propertyValue.isNullOrBlank()) {
        return propertyValue
    }

    val envValue = System.getenv(envName)
    return envValue?.takeIf { it.isNotBlank() }
}

val releaseStoreFile = signingValue("storeFile", "ANDROID_KEYSTORE_PATH")
val releaseStorePassword = signingValue("storePassword", "ANDROID_KEYSTORE_PASSWORD")
val releaseKeyAlias = signingValue("keyAlias", "ANDROID_KEY_ALIAS")
val releaseKeyPassword = signingValue("keyPassword", "ANDROID_KEY_PASSWORD")

android {
    namespace = "com.ffai.assistant"
    compileSdk = 33
    buildToolsVersion = "33.0.2"

    defaultConfig {
        applicationId = "com.ffai.assistant"
        minSdk = 24
        targetSdk = 33
        
        // Optimización para ensemble 120MB en A21S
        multiDexEnabled = true
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (
            !releaseStoreFile.isNullOrBlank() &&
            !releaseStorePassword.isNullOrBlank() &&
            !releaseKeyAlias.isNullOrBlank() &&
            !releaseKeyPassword.isNullOrBlank()
        ) {
            create("release") {
                storeFile = file(requireNotNull(releaseStoreFile))
                storePassword = requireNotNull(releaseStorePassword)
                keyAlias = requireNotNull(releaseKeyAlias)
                keyPassword = requireNotNull(releaseKeyPassword)
            }
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.findByName("release")
            isMinifyEnabled = true
            isShrinkResources = true
            isDebuggable = false
            // Optimizaciones para release
            isZipAlignEnabled = true
            isPseudoLocalesEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            // Configuraciones adicionales de release
            ndk {
                debugSymbolLevel "FULL"
            }
        }
        debug {
            isMinifyEnabled = false
            isShrinkResources = false
            isDebuggable = true
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
        }
    }
    
    // Splits de ABI para reducir tamaño del APK en cada arquitectura
    splits {
        abi {
            isEnable = true
            reset()
            include("armeabi-v7a", "arm64-v8a") // Samsung A21S = arm64-v8a
            isUniversalApk = false // No generar APK universal, solo específicos
        }
        density {
            isEnable = true
            reset()
            include("hdpi", "xhdpi") // A21S = 720x1600 (hdpi/xhdpi)
        }
    }
    
    // Packaging options optimizado
    packaging {
        resources {
            excludes += setOf(
                "META-INF/DEPENDENCIES",
                "META-INF/LICENSE",
                "META-INF/LICENSE.txt",
                "META-INF/NOTICE",
                "META-INF/NOTICE.txt",
                "META-INF/ASL2.0",
                "META-INF/*.kotlin_module",
                "META-INF/INDEX.LIST",
                "META-INF/io.netty.versions.properties"
            )
        }
        jniLibs {
            useLegacyPackaging = false
        }
    }
    
    // Lint checks
    lint {
        disable += "ObsoleteLintCustomCheck"
        abortOnError = false
        checkReleaseBuilds = false
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        viewBinding = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.cardview:cardview:1.0.0")
    implementation("androidx.lifecycle:lifecycle-service:2.6.2")
    
    // TensorFlow Lite - IA Ensemble +120MB
    implementation("org.tensorflow:tensorflow-lite:2.14.0")
    implementation("org.tensorflow:tensorflow-lite-support:0.4.4")
    implementation("org.tensorflow:tensorflow-lite-gpu:2.14.0") // GPU Delegate para velocidad
    implementation("org.tensorflow:tensorflow-lite-gpu-api:2.14.0")
    implementation("org.tensorflow:tensorflow-lite-select-tf-ops:2.14.0") // Ops adicionales para DQN
    
    // OpenCV (JavaCV)
    implementation("org.bytedeco:javacv:1.5.9")
    implementation("org.bytedeco:javacpp:1.5.9")
    
    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    
    // SocketIO Client (reemplaza Ktor WebSocket)
    implementation("io.socket:socket.io-client:2.1.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    
    // Compresión para binary streaming
    implementation("com.github.luben:zstd-jni:1.5.5-5")
    
    // JSON parsing para SocketIO
    implementation("org.json:json:20231013")
    
    // Ktor - solo para HTTP REST (sin WebSocket)
    implementation("io.ktor:ktor-client-okhttp:2.3.7")
    implementation("io.ktor:ktor-client-content-negotiation:2.3.7")
    implementation("io.ktor:ktor-serialization-kotlinx-json:2.3.7")
    
    // JSON Serialization
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.2")
    
    // Background sync (requerido para BackupWorker)
    implementation("androidx.work:work-runtime-ktx:2.9.0")
    
    /* FASE 1: CLOUD FEATURES DISABLED - IA 100% LOCAL
    // Google Sign-In & Drive API
    implementation("com.google.android.gms:play-services-auth:21.0.0")
    implementation("com.google.http-client:google-http-client-gson:1.43.3")
    implementation("com.google.apis:google-api-services-drive:v3-rev20240123-2.0.0")
    implementation("com.google.api-client:google-api-client-android:2.2.0")
    */
    
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
}
