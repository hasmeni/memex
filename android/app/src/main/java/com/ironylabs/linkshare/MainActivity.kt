package com.ironylabs.linkshare

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import android.widget.TextView

class MainActivity : AppCompatActivity() {

    private lateinit var prefs: AppPrefs
    private lateinit var api: ApiClient
    private lateinit var queue: LinkQueue

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        prefs = AppPrefs(this)
        api = ApiClient(prefs)
        queue = LinkQueue(this)

        val editUrl = findViewById<TextInputEditText>(R.id.editServerUrl)
        val editPass = findViewById<TextInputEditText>(R.id.editPassword)
        val btnConnect = findViewById<MaterialButton>(R.id.btnConnect)
        val txtStatus = findViewById<TextView>(R.id.txtStatus)

        // Load saved server URL
        prefs.getServerUrl()?.let { editUrl.setText(it) }

        // Show current status
        updateStatus(txtStatus)

        btnConnect.setOnClickListener {
            val serverUrl = editUrl.text.toString().trim()
            val password = editPass.text.toString()

            if (serverUrl.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Fill in server URL and password", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            btnConnect.isEnabled = false
            txtStatus.text = "Connecting..."

            api.login(serverUrl, password) { success, message ->
                runOnUiThread {
                    btnConnect.isEnabled = true
                    if (success) {
                        txtStatus.text = "✓ Connected to $serverUrl"
                        txtStatus.setTextColor(0xFF34D399.toInt())
                        Toast.makeText(this, "Connected! You can now share links.", Toast.LENGTH_LONG).show()
                        // Auto-sync queue after successful login
                        syncQueue(txtStatus)
                    } else {
                        txtStatus.text = "✗ $message"
                        txtStatus.setTextColor(0xFFF87171.toInt())
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        val txtStatus = findViewById<TextView>(R.id.txtStatus)
        updateStatus(txtStatus)
        // Try to sync queue whenever app is opened
        if (prefs.isConnected() && queue.count() > 0) {
            syncQueue(txtStatus)
        }
    }

    private fun updateStatus(txtStatus: TextView) {
        val queueCount = queue.count()
        if (prefs.isConnected()) {
            val url = prefs.getServerUrl() ?: ""
            val queueText = if (queueCount > 0) " | $queueCount queued" else ""
            txtStatus.text = "✓ Connected to $url$queueText"
            txtStatus.setTextColor(if (queueCount > 0) 0xFFFBBF24.toInt() else 0xFF34D399.toInt())
        } else {
            txtStatus.text = "Not connected" + if (queueCount > 0) " | $queueCount queued offline" else ""
            txtStatus.setTextColor(0xFF888888.toInt())
        }
    }

    private fun syncQueue(txtStatus: TextView) {
        val pending = queue.getAll()
        if (pending.isEmpty()) return

        txtStatus.text = "Syncing ${pending.size} queued links..."
        txtStatus.setTextColor(0xFFFBBF24.toInt())

        var synced = 0
        var failed = 0
        val total = pending.size

        // Sync from newest to oldest (reverse so index removal is safe)
        for (i in pending.indices.reversed()) {
            val link = pending[i]
            api.saveLink(link.title, link.url, link.category) { success, _ ->
                if (success) {
                    queue.remove(i)
                    synced++
                } else {
                    failed++
                }
                // Update UI when all done
                if (synced + failed == total) {
                    runOnUiThread {
                        if (synced > 0) {
                            Toast.makeText(this, "✓ Synced $synced queued links", Toast.LENGTH_SHORT).show()
                        }
                        updateStatus(txtStatus)
                    }
                }
            }
        }
    }
}
