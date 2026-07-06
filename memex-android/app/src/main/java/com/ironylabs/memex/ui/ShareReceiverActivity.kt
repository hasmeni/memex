package com.ironylabs.memex.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import com.ironylabs.memex.R
import com.ironylabs.memex.data.ApiClient
import com.ironylabs.memex.data.Prefs

class ShareReceiverActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_add_link)
        title = "Save to Memex"

        val prefs = Prefs(this)
        val api = ApiClient(prefs)

        if (!prefs.isConnected()) { Toast.makeText(this, "Open Memex and connect first", Toast.LENGTH_LONG).show(); finish(); return }

        val editTitle = findViewById<TextInputEditText>(R.id.editTitle)
        val editUrl = findViewById<TextInputEditText>(R.id.editUrl)
        val editCategory = findViewById<TextInputEditText>(R.id.editCategory)
        val editTags = findViewById<TextInputEditText>(R.id.editTags)
        val btnSave = findViewById<MaterialButton>(R.id.btnSave)

        if (intent?.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            val text = intent.getStringExtra(Intent.EXTRA_TEXT) ?: ""
            val subject = intent.getStringExtra(Intent.EXTRA_SUBJECT) ?: ""
            val urlRegex = Regex("https?://[^\\s]+")
            editUrl.setText(urlRegex.find(text)?.value ?: text)
            editTitle.setText(subject.ifBlank { "" })
        }

        btnSave.setOnClickListener {
            val t = editTitle.text.toString().trim()
            val u = editUrl.text.toString().trim()
            if (t.isEmpty() || u.isEmpty()) { Toast.makeText(this, "Title and URL required", Toast.LENGTH_SHORT).show(); return@setOnClickListener }
            btnSave.isEnabled = false
            api.createLink(t, u, editCategory.text.toString().trim(), editTags.text.toString().trim()) { success, msg ->
                runOnUiThread {
                    if (success) { Toast.makeText(this, "✓ Saved!", Toast.LENGTH_SHORT).show(); finish() }
                    else { btnSave.isEnabled = true; Toast.makeText(this, msg, Toast.LENGTH_LONG).show() }
                }
            }
        }
    }
}
