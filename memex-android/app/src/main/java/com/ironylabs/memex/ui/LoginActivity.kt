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

class LoginActivity : AppCompatActivity() {
    private lateinit var prefs: Prefs
    private lateinit var api: ApiClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        prefs = Prefs(this)
        api = ApiClient(prefs)

        if (prefs.isConnected()) { goToMain(); return }

        val editUrl = findViewById<TextInputEditText>(R.id.editServerUrl)
        val editPass = findViewById<TextInputEditText>(R.id.editPassword)
        val btnLogin = findViewById<MaterialButton>(R.id.btnLogin)

        prefs.getServerUrl()?.let { editUrl.setText(it) }

        btnLogin.setOnClickListener {
            val url = editUrl.text.toString().trim()
            val pass = editPass.text.toString()
            if (url.isEmpty() || pass.isEmpty()) { Toast.makeText(this, "Fill in all fields", Toast.LENGTH_SHORT).show(); return@setOnClickListener }
            btnLogin.isEnabled = false
            api.login(url, pass) { success, msg ->
                runOnUiThread {
                    btnLogin.isEnabled = true
                    if (success) { Toast.makeText(this, "Connected!", Toast.LENGTH_SHORT).show(); goToMain() }
                    else Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun goToMain() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}
