package com.ironylabs.memex.ui

import android.content.Intent
import android.net.Uri
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.recyclerview.widget.RecyclerView
import com.ironylabs.memex.R
import com.ironylabs.memex.data.LinkItem

class LinkAdapter(
    private val links: List<LinkItem>,
    private val onDelete: (LinkItem) -> Unit
) : RecyclerView.Adapter<LinkAdapter.ViewHolder>() {

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val icon: TextView = view.findViewById(R.id.linkIcon)
        val title: TextView = view.findViewById(R.id.linkTitle)
        val category: TextView = view.findViewById(R.id.linkCategory)
        val url: TextView = view.findViewById(R.id.linkUrl)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_link, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val link = links[position]
        holder.icon.text = link.icon
        holder.title.text = link.title
        holder.category.text = "${link.category} · ${link.click_count} clicks"
        holder.url.text = link.url.removePrefix("https://").removePrefix("http://").take(40)

        holder.itemView.setOnClickListener {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(link.url))
            holder.itemView.context.startActivity(intent)
        }

        holder.itemView.setOnLongClickListener {
            AlertDialog.Builder(holder.itemView.context)
                .setTitle("Delete \"${link.title}\"?")
                .setPositiveButton("Delete") { _, _ -> onDelete(link) }
                .setNegativeButton("Cancel", null)
                .show()
            true
        }
    }

    override fun getItemCount() = links.size
}
