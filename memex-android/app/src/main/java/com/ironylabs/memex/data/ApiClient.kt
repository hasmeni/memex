package com.ironylabs.memex.data

import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException

class ApiClient(private val prefs: Prefs) {
    private val client = OkHttpClient()
    private val gson = Gson()
    private val JSON = "application/json; charset=utf-8".toMediaType()

    private fun baseUrl() = prefs.getServerUrl() ?: ""
    private fun authHeader() = "Bearer ${prefs.getToken() ?: ""}"

    fun login(serverUrl: String, password: String, callback: (Boolean, String) -> Unit) {
        val body = FormBody.Builder().add("username", "admin").add("password", password).build()
        val req = Request.Builder().url("${serverUrl.trimEnd('/')}/api/auth/token").post(body).build()
        client.newCall(req).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) { callback(false, "Connection failed: ${e.message}") }
            override fun onResponse(call: Call, response: Response) {
                response.use {
                    if (it.isSuccessful) {
                        val json = gson.fromJson(it.body?.string(), Map::class.java)
                        val token = json["access_token"] as? String ?: ""
                        if (token.isNotEmpty()) { prefs.saveConnection(serverUrl, token); callback(true, "Connected!") }
                        else callback(false, "No token")
                    } else callback(false, "Login failed (${it.code})")
                }
            }
        })
    }

    fun getLinks(callback: (Boolean, List<LinkItem>) -> Unit) {
        val req = Request.Builder().url("${baseUrl()}/api/admin/links").addHeader("Authorization", authHeader()).build()
        client.newCall(req).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) { callback(false, emptyList()) }
            override fun onResponse(call: Call, response: Response) {
                response.use {
                    if (it.isSuccessful) {
                        val type = object : TypeToken<List<LinkItem>>() {}.type
                        val links: List<LinkItem> = gson.fromJson(it.body?.string(), type)
                        callback(true, links)
                    } else callback(false, emptyList())
                }
            }
        })
    }

    fun createLink(title: String, url: String, category: String, tags: String, callback: (Boolean, String) -> Unit) {
        val json = gson.toJson(mapOf("title" to title, "url" to url, "category" to category.ifBlank { "General" }, "tags" to tags, "icon" to "🔗"))
        val req = Request.Builder().url("${baseUrl()}/api/admin/links").addHeader("Authorization", authHeader())
            .post(json.toRequestBody(JSON)).build()
        client.newCall(req).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) { callback(false, e.message ?: "Failed") }
            override fun onResponse(call: Call, response: Response) {
                response.use {
                    if (it.isSuccessful) callback(true, "Saved!")
                    else if (it.code == 409) callback(false, "Duplicate URL")
                    else if (it.code == 401) callback(false, "Session expired")
                    else callback(false, "Error ${it.code}")
                }
            }
        })
    }

    fun deleteLink(id: Int, callback: (Boolean) -> Unit) {
        val req = Request.Builder().url("${baseUrl()}/api/admin/links/$id").addHeader("Authorization", authHeader()).delete().build()
        client.newCall(req).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) { callback(false) }
            override fun onResponse(call: Call, response: Response) { response.use { callback(it.isSuccessful) } }
        })
    }

    fun getStats(callback: (Boolean, Map<String, Any>?) -> Unit) {
        val req = Request.Builder().url("${baseUrl()}/api/admin/stats").addHeader("Authorization", authHeader()).build()
        client.newCall(req).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) { callback(false, null) }
            override fun onResponse(call: Call, response: Response) {
                response.use {
                    if (it.isSuccessful) {
                        val data = gson.fromJson(it.body?.string(), Map::class.java) as Map<String, Any>
                        callback(true, data)
                    } else callback(false, null)
                }
            }
        })
    }
}
