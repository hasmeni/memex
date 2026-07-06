package com.ironylabs.linkshare

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText

class ShareReceiverActivity : AppCompatActivity() {

    private lateinit var prefs: AppPrefs
    private lateinit var api: ApiClient
    private lateinit var queue: LinkQueue

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_share)

        prefs = AppPrefs(this)
        api = ApiClient(prefs)
        queue = LinkQueue(this)

        val editTitle = findViewById<TextInputEditText>(R.id.editTitle)
        val editUrl = findViewById<TextInputEditText>(R.id.editUrl)
        val editCategory = findViewById<TextInputEditText>(R.id.editCategory)
        val btnSave = findViewById<MaterialButton>(R.id.btnSave)
        val btnCancel = findViewById<MaterialButton>(R.id.btnCancel)

        // Check if connected
        if (!prefs.isConnected()) {
            Toast.makeText(this, "Open Memex Share app and connect first", Toast.LENGTH_LONG).show()
            finish()
            return
        }

        // Extract shared content
        if (intent?.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            val sharedText = intent.getStringExtra(Intent.EXTRA_TEXT) ?: ""
            val sharedSubject = intent.getStringExtra(Intent.EXTRA_SUBJECT) ?: ""

            // Try to extract URL from shared text
            val urlRegex = Regex("https?://[^\\s]+")
            val foundUrl = urlRegex.find(sharedText)?.value ?: sharedText

            editUrl.setText(foundUrl)
            editTitle.setText(sharedSubject.ifBlank { extractTitleFromUrl(foundUrl) })
        }

        btnSave.setOnClickListener {
            val title = editTitle.text.toString().trim()
            val url = editUrl.text.toString().trim()
            val category = editCategory.text.toString().trim()

            if (title.isEmpty() || url.isEmpty()) {
                Toast.makeText(this, "Title and URL required", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            btnSave.isEnabled = false
            btnSave.text = "Saving..."

            api.saveLink(title, url, category) { success, message ->
                runOnUiThread {
                    if (success) {
                        Toast.makeText(this, "✓ $message", Toast.LENGTH_SHORT).show()
                        finish()
                    } else {
                        // Queue the link for later sync
                        queue.add(LinkQueue.QueuedLink(title, url, category))
                        Toast.makeText(this, "⏳ Queued offline (${queue.count()} pending)", Toast.LENGTH_LONG).show()
                        finish()
                    }
                }
            }
        }

        btnCancel.setOnClickListener { finish() }
    }

    private fun extractTitleFromUrl(url: String): String {
        return try {
            val host = java.net.URI(url).host ?: url
            host.removePrefix("www.")
        } catch (e: Exception) {
            url.take(60)
        }
    }
}
