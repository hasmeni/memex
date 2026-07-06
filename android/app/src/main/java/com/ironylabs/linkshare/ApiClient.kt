package com.ironylabs.linkshare

import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

class ApiClient(private val prefs: AppPrefs) {

    private val client = OkHttpClient()
    private val JSON_TYPE = "application/json; charset=utf-8".toMediaType()

    fun login(serverUrl: String, password: String, callback: (Boolean, String) -> Unit) {
        val url = "${serverUrl.trimEnd('/')}/api/auth/token"
        val body = FormBody.Builder()
            .add("username", "admin")
            .add("password", password)
            .build()

        val request = Request.Builder().url(url).post(body).build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback(false, "Connection failed: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    if (it.isSuccessful) {
                        val json = JSONObject(it.body?.string() ?: "{}")
                        val token = json.optString("access_token", "")
                        if (token.isNotEmpty()) {
                            prefs.saveConnection(serverUrl, token)
                            callback(true, "Connected!")
                        } else {
                            callback(false, "No token received")
                        }
                    } else {
                        callback(false, "Login failed (${it.code})")
                    }
                }
            }
        })
    }

    fun saveLink(title: String, url: String, category: String, callback: (Boolean, String) -> Unit) {
        val serverUrl = prefs.getServerUrl() ?: return callback(false, "Not connected")
        val token = prefs.getToken() ?: return callback(false, "Not authenticated")

        val json = JSONObject().apply {
            put("title", title)
            put("url", url)
            put("category", category.ifBlank { "General" })
            put("icon", "🔗")
        }

        val requestBody = json.toString().toRequestBody(JSON_TYPE)
        val request = Request.Builder()
            .url("${serverUrl.trimEnd('/')}/api/admin/links")
            .addHeader("Authorization", "Bearer $token")
            .post(requestBody)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback(false, "Failed: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    if (it.isSuccessful) {
                        val resp = JSONObject(it.body?.string() ?: "{}")
                        callback(true, "Saved: ${resp.optString("title", title)}")
                    } else if (it.code == 401) {
                        callback(false, "Session expired — reconnect in app")
                    } else {
                        callback(false, "Error (${it.code})")
                    }
                }
            }
        })
    }
}
