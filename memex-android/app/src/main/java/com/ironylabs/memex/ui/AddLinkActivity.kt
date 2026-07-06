package com.ironylabs.memex.ui

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import com.ironylabs.memex.R
import com.ironylabs.memex.data.ApiClient
import com.ironylabs.memex.data.Prefs

class AddLinkActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_add_link)
        title = "Add Link"

        val prefs = Prefs(this)
        val api = ApiClient(prefs)

        val editTitle = findViewById<TextInputEditText>(R.id.editTitle)
        val editUrl = findViewById<TextInputEditText>(R.id.editUrl)
        val editCategory = findViewById<TextInputEditText>(R.id.editCategory)
        val editTags = findViewById<TextInputEditText>(R.id.editTags)
        val btnSave = findViewById<MaterialButton>(R.id.btnSave)

        btnSave.setOnClickListener {
            val t = editTitle.text.toString().trim()
            val u = editUrl.text.toString().trim()
            if (t.isEmpty() || u.isEmpty()) { Toast.makeText(this, "Title and URL required", Toast.LENGTH_SHORT).show(); return@setOnClickListener }
            btnSave.isEnabled = false
            api.createLink(t, u, editCategory.text.toString().trim(), editTags.text.toString().trim()) { success, msg ->
                runOnUiThread {
                    btnSave.isEnabled = true
                    if (success) { Toast.makeText(this, "✓ Saved!", Toast.LENGTH_SHORT).show(); finish() }
                    else Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
                }
            }
        }
    }
}
