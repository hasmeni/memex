package com.ironylabs.linkshare

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject

/**
 * Offline queue for links that couldn't be saved (server unreachable, token expired, etc).
 * Stored in SharedPreferences as a JSON array. Survives app close and phone restart.
 */
class LinkQueue(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("ironylabs_queue", Context.MODE_PRIVATE)

    data class QueuedLink(
        val title: String,
        val url: String,
        val category: String,
        val timestamp: Long = System.currentTimeMillis()
    )

    fun add(link: QueuedLink) {
        val queue = getAll().toMutableList()
        queue.add(link)
        save(queue)
    }

    fun getAll(): List<QueuedLink> {
        val json = prefs.getString("queue", "[]") ?: "[]"
        val array = JSONArray(json)
        val list = mutableListOf<QueuedLink>()
        for (i in 0 until array.length()) {
            val obj = array.getJSONObject(i)
            list.add(
                QueuedLink(
                    title = obj.getString("title"),
                    url = obj.getString("url"),
                    category = obj.optString("category", "General"),
                    timestamp = obj.optLong("timestamp", 0)
                )
            )
        }
        return list
    }

    fun remove(index: Int) {
        val queue = getAll().toMutableList()
        if (index in queue.indices) {
            queue.removeAt(index)
            save(queue)
        }
    }

    fun clear() {
        prefs.edit().putString("queue", "[]").apply()
    }

    fun count(): Int = getAll().size

    private fun save(queue: List<QueuedLink>) {
        val array = JSONArray()
        queue.forEach { link ->
            array.put(JSONObject().apply {
                put("title", link.title)
                put("url", link.url)
                put("category", link.category)
                put("timestamp", link.timestamp)
            })
        }
        prefs.edit().putString("queue", array.toString()).apply()
    }
}
