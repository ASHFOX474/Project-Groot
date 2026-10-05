package bd.groot.groot_app

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.speech.RecognizerIntent
import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.app.KeyguardManager
import android.view.WindowManager
import android.net.Uri
import android.provider.MediaStore
import java.util.concurrent.Executors

class MainActivity : FlutterActivity() {
    private val photoRequest = 4706
    private var pendingPhoto: MethodChannel.Result? = null
    private val photoIO = Executors.newSingleThreadExecutor()
    private var pendingVoice: MethodChannel.Result? = null
    private val voiceRequest = 4701
    private var pendingReminder: MethodChannel.Result? = null
    private var reminderHour = 8
    private var reminderMinute = 0
    private val reminderPermissionRequest = 4704
    private val offlineRequest = 4705
    private var pendingOffline: MethodChannel.Result? = null
    private val offlineIO = Executors.newSingleThreadExecutor()
    private val offlineGate = Any()
    private var offlineUnlocked = false
    private var offlineGeneration = 0
    private val offlineVault by lazy { OfflineCareVault(this) }

    private fun lockOffline() {
        synchronized(offlineGate) { offlineUnlocked = false; offlineGeneration++ }
        pendingOffline?.error("locked", "Offline notebook locked", null)
        pendingOffline = null
    }

    private fun offlineWork(result: MethodChannel.Result, action: () -> Any?) {
        val generation = synchronized(offlineGate) { offlineGeneration }
        offlineIO.execute {
            try {
                val value = synchronized(offlineGate) {
                    check(offlineUnlocked && generation == offlineGeneration) { "Offline notebook locked" }
                    action()
                }
                runOnUiThread {
                    if (synchronized(offlineGate) { offlineUnlocked && generation == offlineGeneration }) result.success(value)
                    else result.error("locked", "Offline notebook locked", null)
                }
            } catch (_: Exception) {
                runOnUiThread { result.error("vault", "Unlock again. Device lock/key/storage unavailable; existing notebook was not overwritten.", null) }
            }
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        // Private offline pages must not appear in screenshots/recents thumbnails.
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "bd.groot/photos")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "expert" -> {
                        try {
                            startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:16123")))
                            result.success(null)
                        } catch (_: Exception) { result.error("dialer", "Dial16123 manually", null) }
                    }
                    "pick" -> {
                        if (pendingPhoto != null) result.error("busy", "Photo picker already active", null)
                        else {
                            val intent = if (Build.VERSION.SDK_INT >= 33) Intent(MediaStore.ACTION_PICK_IMAGES).apply {
                                type = "image/*"
                            } else Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                                addCategory(Intent.CATEGORY_OPENABLE)
                                type = "image/*"
                                putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("image/jpeg", "image/png"))
                            }
                            try {
                                pendingPhoto = result
                                startActivityForResult(intent, photoRequest)
                            } catch (_: Exception) {
                                pendingPhoto = null
                                result.error("picker", "Photo picker unavailable", null)
                            }
                        }
                    }
                    else -> result.notImplemented()
                }
            }
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "bd.groot/offline_care")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "lock" -> { lockOffline(); result.success(null) }
                    "secure" -> result.success(getSystemService(KeyguardManager::class.java).isDeviceSecure)
                    "unlock" -> {
                        if (pendingOffline != null) result.error("busy", "Unlock already active", null)
                        else {
                            val manager = getSystemService(KeyguardManager::class.java)
                            @Suppress("DEPRECATION")
                            val intent = if (manager.isDeviceSecure) manager.createConfirmDeviceCredentialIntent("Groot offline care", "Unlock your private device notebook") else null
                            if (intent == null) result.error("device_lock", "Set an Android screen-lock PIN/password before using offline care", null)
                            else {
                                pendingOffline = result
                                try {
                                    @Suppress("DEPRECATION")
                                    startActivityForResult(intent, offlineRequest)
                                } catch (_: Exception) {
                                    pendingOffline = null
                                    result.error("unavailable", "Device unlock unavailable", null)
                                }
                            }
                        }
                    }
                    "write" -> {
                        val data = call.arguments as? String
                        if (data == null) result.error("data", "Notebook data required", null)
                        else offlineWork(result) { offlineVault.write(data); null }
                    }
                    "clear" -> offlineWork(result) { offlineVault.clear(); null }
                    else -> result.notImplemented()
                }
            }
        // A new engine has no memory-only login. Remove any reminder from the old session.
        CareReminder.cancel(this)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "bd.groot/care_reminders")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "status" -> result.success(CareReminder.enabled(this))
                    "cancel" -> {
                        // A late OS permission result must not reschedule after sign-out.
                        pendingReminder?.success(false); pendingReminder = null
                        CareReminder.cancel(this); result.success(null)
                    }
                    "enable" -> {
                        val hour = call.argument<Int>("hour")
                        val minute = call.argument<Int>("minute")
                        if (hour == null || minute == null || hour !in 0..23 || minute !in 0..59) {
                            result.error("time", "Choose a valid local time", null)
                        } else if (pendingReminder != null) {
                            result.error("busy", "Permission request already active", null)
                        } else if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                            pendingReminder = result; reminderHour = hour; reminderMinute = minute
                            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), reminderPermissionRequest)
                        } else { result.success(CareReminder.schedule(this, hour, minute)) }
                    }
                    else -> result.notImplemented()
                }
            }
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "bd.groot/goal_voice")
            .setMethodCallHandler { call, result ->
                if (call.method != "recognize") {
                    result.notImplemented()
                } else if (pendingVoice != null) {
                    result.error("busy", "Recognition already active", null)
                } else {
                    val language = call.argument<String>("language")
                    if (language != "bn" && language != "en") {
                        result.error("language", "Unsupported language", null)
                    } else {
                        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                            putExtra(RecognizerIntent.EXTRA_LANGUAGE, if (language == "bn") "bn-BD" else "en-US")
                            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                            // A preference, NOT a promise that a provider keeps audio offline.
                            putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
                        }
                        pendingVoice = result
                        try {
                            @Suppress("DEPRECATION")
                            startActivityForResult(intent, voiceRequest)
                        } catch (_: ActivityNotFoundException) {
                            pendingVoice = null
                            result.error("unavailable", "No speech provider", null)
                        } catch (_: SecurityException) {
                            pendingVoice = null
                            result.error("unavailable", "Speech provider denied access", null)
                        }
                    }
                }
            }
    }

    @Deprecated("Activity callback required by FlutterActivity speech-intent bridge")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == photoRequest) {
            val result = pendingPhoto
            pendingPhoto = null
            val uri = data?.data
            if (result != null) {
                if (resultCode != Activity.RESULT_OK || uri == null) result.success(null)
                else photoIO.execute {
                    try {
                        val bytes = PrivatePhotoPicker.read(this, uri)
                        runOnUiThread {
                            if (isDestroyed) result.error("closed", "Photo picker closed", null)
                            else result.success(bytes)
                        }
                    } catch (_: Exception) {
                        runOnUiThread { result.error("photo", "Use a single JPEG/PNG up to3MiB/12MP", null) }
                    }
                }
            }
        }
        if (requestCode == voiceRequest) {
            val result = pendingVoice
            pendingVoice = null
            val text = if (resultCode == Activity.RESULT_OK)
                data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull() else null
            result?.success(text)
        }
        if (requestCode == offlineRequest) {
            val result = pendingOffline
            pendingOffline = null
            if (result != null) {
                if (resultCode == Activity.RESULT_OK) {
                    synchronized(offlineGate) { offlineUnlocked = true }
                    offlineWork(result) { offlineVault.read() }
                } else result.error("cancelled", "Device unlock cancelled", null)
            }
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == reminderPermissionRequest) {
            val result = pendingReminder
            pendingReminder = null
            val granted = grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED
            result?.success(granted && CareReminder.schedule(this, reminderHour, reminderMinute))
        }
    }

    override fun onDestroy() {
        pendingPhoto?.success(null)
        pendingPhoto = null
        photoIO.shutdown()
        lockOffline()
        offlineIO.shutdown()
        pendingReminder?.success(false)
        pendingReminder = null
        pendingVoice?.success(null)
        pendingVoice = null
        super.onDestroy()
    }

    override fun onStop() {
        // Do not cancel the in-progress system credential confirmation itself.
        if (pendingOffline == null) lockOffline()
        super.onStop()
    }
}
