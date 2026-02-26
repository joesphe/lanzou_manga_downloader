import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

fun String.asBuildConfigString(): String = "\"" + this.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
val privateCredentials: Properties by lazy {
    val p = Properties()
    val f = rootProject.file("private_credentials.properties")
    if (f.exists()) {
        f.inputStream().use { p.load(it) }
    }
    p
}
fun propOrEnv(project: org.gradle.api.Project, name: String, defaultValue: String = ""): String {
    val fromPrivate = privateCredentials.getProperty(name)
    return fromPrivate ?: (project.findProperty(name) as String?) ?: System.getenv(name) ?: defaultValue
}

android {
    namespace = "com.lanzou.manga.downloader"
    compileSdk = 36

    defaultConfig {
        val prodUrl = propOrEnv(project, "LANZOU_PROD_URL")
        val prodPassword = propOrEnv(project, "LANZOU_PROD_PASSWORD")

        applicationId = "com.lanzou.manga.downloader"
        minSdk = 26
        targetSdk = 36
        versionCode = 4
        versionName = "v1.2.1"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "DEFAULT_SHARE_URL", prodUrl.asBuildConfigString())
        buildConfigField("String", "DEFAULT_SHARE_PASSWORD", prodPassword.asBuildConfigString())
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2025.01.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")

    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    implementation("androidx.work:work-runtime-ktx:2.10.0")
    implementation("top.yukonga.miuix.kmp:miuix:0.8.4")
    implementation("top.yukonga.miuix.kmp:miuix-icons:0.8.4")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
