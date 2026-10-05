package bd.groot.groot_app

import android.app.AlarmManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import java.util.Calendar

/** Generic device-wide reminder. Stores one boolean, never credentials or care data. */
object CareReminder {
    private const val requestId = 4702
    private const val notificationId = 4703
    private const val channelId = "groot_care_reminder"
    private fun preferences(context: Context) =
        context.getSharedPreferences("groot_generic_reminder", Context.MODE_PRIVATE)
    fun enabled(context: Context) = preferences(context).getBoolean("enabled", false)
    private fun alarm(context: Context) = context.getSystemService(AlarmManager::class.java)
    private fun pending(context: Context): PendingIntent = PendingIntent.getBroadcast(
        context, requestId, Intent(context, CareReminderReceiver::class.java),
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)

    fun schedule(context: Context, hour: Int, minute: Int): Boolean {
        val manager = context.getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= 26) {
            manager.createNotificationChannel(NotificationChannel(
                channelId, "Care check reminder", NotificationManager.IMPORTANCE_DEFAULT))
            if (manager.getNotificationChannel(channelId).importance == NotificationManager.IMPORTANCE_NONE) return false
        }
        if (!manager.areNotificationsEnabled()) return false
        val next = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, hour); set(Calendar.MINUTE, minute)
            set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
            if (timeInMillis <= System.currentTimeMillis()) add(Calendar.DAY_OF_YEAR, 1)
        }
        // No exact-alarm permission. Android battery/Doze policies may defer delivery.
        alarm(context).setInexactRepeating(AlarmManager.RTC_WAKEUP,
            next.timeInMillis, AlarmManager.INTERVAL_DAY, pending(context))
        preferences(context).edit().putBoolean("enabled", true).apply()
        return true
    }

    fun cancel(context: Context) {
        preferences(context).edit().putBoolean("enabled", false).apply()
        alarm(context).cancel(pending(context))
        context.getSystemService(NotificationManager::class.java).cancel(notificationId)
    }

    fun notify(context: Context) {
        if (!enabled(context)) return
        val manager = context.getSystemService(NotificationManager::class.java)
        if (!manager.areNotificationsEnabled()) { cancel(context); return }
        val open = PendingIntent.getActivity(context, requestId,
            Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        @Suppress("DEPRECATION")
        val builder = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(context, channelId) else Notification.Builder(context)
        val notification = builder.setSmallIcon(android.R.drawable.ic_menu_today)
            .setContentTitle("Groot · যত্নের কথা")
            .setContentText("Open Groot to recheck current care tasks · বর্তমান কাজ দেখুন")
            .setVisibility(Notification.VISIBILITY_PRIVATE)
            .setContentIntent(open).setAutoCancel(true).build()
        try { manager.notify(notificationId, notification) } catch (_: SecurityException) { cancel(context) }
    }
}

class CareReminderReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) { CareReminder.notify(context) }
}
