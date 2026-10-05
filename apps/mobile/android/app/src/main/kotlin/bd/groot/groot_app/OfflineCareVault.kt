package bd.groot.groot_app

import android.app.KeyguardManager
import android.content.Context
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import java.io.File
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** App-private, no-backup, authenticated AES-GCM blob. Never stores credentials.
 * Call only on the Activity's serial IO executor. No plaintext fallback/recovery erase.
 */
class OfflineCareVault(private val context: Context) {
    private val alias = "groot-offline-care-v1"
    private val file = AtomicFile(File(context.noBackupFilesDir, "offline-care-v1.bin"))
    private val maxBytes = 2 * 1024 * 1024

    private fun key(create: Boolean): SecretKey {
        val manager = context.getSystemService(KeyguardManager::class.java)
        check(manager.isDeviceSecure && !manager.isDeviceLocked) { "Device lock required" }
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = store.getKey(alias, null) as? SecretKey
        if (existing != null) return existing
        check(create && !file.baseFile.exists()) { "Offline key unavailable; preserve notebook for recovery" }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        val spec = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .setUserAuthenticationRequired(true)
        if (Build.VERSION.SDK_INT >= 30) {
            spec.setUserAuthenticationParameters(300, KeyProperties.AUTH_DEVICE_CREDENTIAL)
        } else {
            @Suppress("DEPRECATION")
            spec.setUserAuthenticationValidityDurationSeconds(300)
        }
        generator.init(spec.build())
        return generator.generateKey()
    }

    fun read(): String? {
        if (!file.baseFile.exists() && !File(file.baseFile.path + ".bak").exists()) return null
        val bytes = file.openRead().use { stream ->
            check(stream.available() <= maxBytes + 64) { "Offline notebook too large" }
            stream.readBytes()
        }
        check(bytes.size in 29..(maxBytes + 64)) { "Invalid notebook" }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key(false), GCMParameterSpec(128, bytes.copyOfRange(0, 12)))
        cipher.updateAAD(alias.toByteArray(Charsets.UTF_8))
        return String(cipher.doFinal(bytes.copyOfRange(12, bytes.size)), Charsets.UTF_8)
    }

    fun write(value: String) {
        val raw = value.toByteArray(Charsets.UTF_8)
        check(raw.size <= maxBytes) { "Offline notebook too large" }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key(true))
        cipher.updateAAD(alias.toByteArray(Charsets.UTF_8))
        val encrypted = cipher.iv + cipher.doFinal(raw)
        val stream = file.startWrite()
        try {
            stream.write(encrypted)
            file.finishWrite(stream)
        } catch (error: Exception) {
            file.failWrite(stream)
            throw error
        }
    }

    fun clear() {
        file.delete()
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        store.deleteEntry(alias)
    }
}
