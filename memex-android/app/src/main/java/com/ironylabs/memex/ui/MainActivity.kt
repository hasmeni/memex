package com.ironylabs.memex.ui

import android.content.Intent
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.chip.Chip
import com.google.android.material.chip.ChipGroup
import com.google.android.material.floatingactionbutton.FloatingActionButton
import com.ironylabs.memex.R
import com.ironylabs.memex.data.ApiClient
import com.ironylabs.memex.data.LinkItem
import com.ironylabs.memex.data.Prefs

class MainActivity : AppCompatActivity() {
    private lateinit var prefs: Prefs
    private lateinit var api: ApiClient
    private lateinit var recyclerView: RecyclerView
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var emptyText: TextView
    private lateinit var statsView: View
    private lateinit var linksView: View
    private lateinit var searchInput: EditText
    private lateinit var tagGroup: ChipGroup
    private var allLinks: List<LinkItem> = emptyList()
    private var searchQuery: String = ""
    private var activeTag: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        setSupportActionBar(findViewById(R.id.toolbar))

        prefs = Prefs(this)
        api = ApiClient(prefs)

        recyclerView = findViewById(R.id.recyclerLinks)
        swipeRefresh = findViewById(R.id.swipeRefresh)
        emptyText = findViewById(R.id.emptyText)
        statsView = findViewById(R.id.statsView)
        linksView = findViewById(R.id.linksView)
        searchInput = findViewById(R.id.searchInput)
        tagGroup = findViewById(R.id.tagGroup)

        recyclerView.layoutManager = LinearLayoutManager(this)

        swipeRefresh.setColorSchemeColors(0xFFFF7A29.toInt())
        swipeRefresh.setOnRefreshListener { loadLinks() }

        findViewById<FloatingActionButton>(R.id.fabAdd).setOnClickListener {
            startActivity(Intent(this, AddLinkActivity::class.java))
        }

        val bottomNav = findViewById<BottomNavigationView>(R.id.bottomNav)
        bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_links -> { showLinks(); true }
                R.id.nav_stats -> { showStats(); true }
                else -> false
            }
        }

        // Search
        searchInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                searchQuery = s.toString().lowercase().trim()
                renderFilteredLinks()
            }
        })

        loadLinks()
    }

    override fun onResume() { super.onResume(); loadLinks() }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menu.add(0, 1, 0, "Logout")
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId == 1) { prefs.clear(); startActivity(Intent(this, LoginActivity::class.java)); finish(); return true }
        return super.onOptionsItemSelected(item)
    }

    private fun loadLinks() {
        api.getLinks { success, links ->
            runOnUiThread {
                swipeRefresh.isRefreshing = false
                if (success) {
                    allLinks = links
                    buildTagChips()
                    renderFilteredLinks()
                    title = "Memex (${links.size})"
                } else Toast.makeText(this, "Failed to load links", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun buildTagChips() {
        tagGroup.removeAllViews()
        val allTags = mutableSetOf<String>()
        allLinks.forEach { link ->
            link.tags.split(",").map { it.trim() }.filter { it.isNotEmpty() }.forEach { allTags.add(it) }
        }
        // Add "All" chip
        val allChip = Chip(this).apply {
            text = "All"
            isCheckable = true
            isChecked = activeTag == null
            setOnClickListener { activeTag = null; buildTagChips(); renderFilteredLinks() }
        }
        tagGroup.addView(allChip)
        // Add tag chips
        allTags.sorted().forEach { tag ->
            val chip = Chip(this).apply {
                text = tag
                isCheckable = true
                isChecked = activeTag == tag
                setOnClickListener { activeTag = tag; buildTagChips(); renderFilteredLinks() }
            }
            tagGroup.addView(chip)
        }
    }

    private fun renderFilteredLinks() {
        var filtered = allLinks

        // Filter by tag
        if (activeTag != null) {
            filtered = filtered.filter { it.tags.split(",").map { t -> t.trim() }.contains(activeTag) }
        }

        // Filter by search
        if (searchQuery.isNotEmpty()) {
            filtered = filtered.filter {
                it.title.lowercase().contains(searchQuery) ||
                it.category.lowercase().contains(searchQuery) ||
                it.url.lowercase().contains(searchQuery) ||
                it.tags.lowercase().contains(searchQuery)
            }
        }

        if (filtered.isEmpty()) { emptyText.visibility = View.VISIBLE; recyclerView.visibility = View.GONE }
        else { emptyText.visibility = View.GONE; recyclerView.visibility = View.VISIBLE }
        recyclerView.adapter = LinkAdapter(filtered) { link -> deleteLink(link) }
    }

    private fun deleteLink(link: LinkItem) {
        api.deleteLink(link.id) { success ->
            runOnUiThread {
                if (success) { Toast.makeText(this, "Deleted", Toast.LENGTH_SHORT).show(); loadLinks() }
                else Toast.makeText(this, "Delete failed", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun showLinks() { linksView.visibility = View.VISIBLE; statsView.visibility = View.GONE }
    private fun showStats() {
        linksView.visibility = View.GONE; statsView.visibility = View.VISIBLE
        api.getStats { success, data ->
            runOnUiThread {
                if (success && data != null) {
                    findViewById<TextView>(R.id.statLinks).text = "Links: ${(data["total_links"] as? Double)?.toInt() ?: 0}"
                    findViewById<TextView>(R.id.statClicks).text = "Clicks: ${(data["total_clicks"] as? Double)?.toInt() ?: 0}"
                }
            }
        }
    }
}
