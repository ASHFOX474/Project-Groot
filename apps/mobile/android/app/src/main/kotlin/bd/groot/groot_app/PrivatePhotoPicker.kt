package bd.groot.groot_app

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import kotlin.math.max
import kotlin.math.roundToInt

/** No library permission, disk cache, filename, URI or EXIF returned to Flutter. */
object PrivatePhotoPicker {
    fun read(context: Context, uri: Uri): ByteArray {
        check(uri.scheme == "content") { "Selected content URI required" }
        val limit = 3 * 1024 * 1024
        val raw = context.contentResolver.openInputStream(uri)!!.use { stream ->
            val output = ByteArrayOutputStream()
            val buffer = ByteArray(8192)
            while (true) {
                val count = stream.read(buffer)
                if (count < 0) break
                check(output.size() + count <= limit) { "Photo too large" }
                output.write(buffer, 0, count)
            }
            output.toByteArray()
        }
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(raw, 0, raw.size, bounds)
        check(bounds.outMimeType in listOf("image/jpeg", "image/png")) { "JPEG/PNG only" }
        check(bounds.outWidth > 0 && bounds.outHeight > 0 &&
            bounds.outWidth.toLong() * bounds.outHeight <= 12000000) { "Photo dimensions too large" }
        val original = BitmapFactory.decodeByteArray(raw, 0, raw.size) ?: error("Invalid photo")
        try {
            @Suppress("DEPRECATION")
            val exif = ExifInterface(ByteArrayInputStream(raw))
            val matrix = Matrix()
            when (exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)) {
                ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.setScale(-1f, 1f)
                ExifInterface.ORIENTATION_ROTATE_180 -> matrix.setRotate(180f)
                ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.setScale(1f, -1f)
                ExifInterface.ORIENTATION_TRANSPOSE -> { matrix.setRotate(90f); matrix.postScale(-1f, 1f) }
                ExifInterface.ORIENTATION_ROTATE_90 -> matrix.setRotate(90f)
                ExifInterface.ORIENTATION_TRANSVERSE -> { matrix.setRotate(270f); matrix.postScale(-1f, 1f) }
                ExifInterface.ORIENTATION_ROTATE_270 -> matrix.setRotate(270f)
            }
            val oriented = Bitmap.createBitmap(original, 0, 0, original.width, original.height, matrix, true)
            try {
                val ratio = minOf(1.0, 1280.0 / max(oriented.width, oriented.height))
                val scaled = Bitmap.createScaledBitmap(oriented,
                    max(1, (oriented.width * ratio).roundToInt()),
                    max(1, (oriented.height * ratio).roundToInt()), true)
                try {
                    val output = ByteArrayOutputStream()
                    check(scaled.compress(Bitmap.CompressFormat.JPEG, 80, output))
                    return output.toByteArray().also { check(it.size <= 524288) }
                } finally { if (scaled !== oriented) scaled.recycle() }
            } finally { if (oriented !== original) oriented.recycle() }
        } finally { original.recycle() }
    }
}
