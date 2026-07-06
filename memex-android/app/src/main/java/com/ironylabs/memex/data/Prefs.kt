package com.ironylabs.memex.data

import android.content.Context
import android.content.SharedPreferences

class Prefs(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences("memex_prefs", Context.MODE_PRIVATE)

    fun saveConnection(serverUrl: String, token: String) {
        prefs.edit().putString("server_url", serverUrl.trimEnd('/')).putString("token", token).apply()
    }
    fun getServerUrl(): String? = prefs.getString("server_url", null)
    fun getToken(): String? = prefs.getString("token", null)
    fun isConnected(): Boolean = !getToken().isNullOrEmpty()
    fun clear() { prefs.edit().clear().apply() }
}
