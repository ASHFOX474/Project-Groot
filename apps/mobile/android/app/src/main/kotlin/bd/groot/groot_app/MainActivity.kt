package bd.groot.groot_app

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.speech.RecognizerIntent

class MainActivity : FlutterActivity() {
    private var pendingVoice: MethodChannel.Result? = null
    private val voiceRequest = 4701

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
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
        if (requestCode == voiceRequest) {
            val result = pendingVoice
            pendingVoice = null
            val text = if (resultCode == Activity.RESULT_OK)
                data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull() else null
            result?.success(text)
        }
    }

    override fun onDestroy() {
        pendingVoice?.success(null)
        pendingVoice = null
        super.onDestroy()
    }
}
