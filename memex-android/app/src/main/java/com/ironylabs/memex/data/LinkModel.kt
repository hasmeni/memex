package com.ironylabs.memex.data

data class LinkItem(
    val id: Int = 0,
    val title: String = "",
    val url: String = "",
    val category: String = "General",
    val tags: String = "",
    val icon: String = "🔗",
    val favicon_url: String = "",
    val description: String = "",
    val notes: String = "",
    val active: Boolean = true,
    val featured: Boolean = false,
    val pinned: Boolean = false,
    @com.google.gson.annotations.SerializedName("private")
    val isPrivate: Boolean = false,
    val read_status: String = "none",
    val sort_order: Int = 0,
    val click_count: Int = 0,
    val upvotes: Int = 0,
    val created_at: String = ""
)
