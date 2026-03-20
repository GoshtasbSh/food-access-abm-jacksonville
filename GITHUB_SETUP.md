# GitHub Setup Guide — GeoMesa Food Access

This guide walks you through creating a private GitHub repository and pushing this project. The setup is designed so you can later make the repo public for your journal paper.

---

## Recommended Repository Name

**`GeoMesa-Food-Access`**

- Professional and suitable for journal citations
- Clear: Geo (spatial) + Mesa (ABM framework) + Food Access
- URL example: `https://github.com/YOUR_USERNAME/GeoMesa-Food-Access`

---

## Step 1: Connect Cursor to GitHub

1. In Cursor, go to **Settings** (gear icon) → **General** → **Account**
2. Under **Integrations**, find **GitHub** and click **Connect**
3. Authorize Cursor in the browser
4. Optionally: [Cursor Integrations](https://cursor.com/docs/integrations/github) for more details

This lets Cursor work with your GitHub repos. For pushing, you still need Git configured (Step 2).

---

## Step 2: Configure Git (if not already done)

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@ufl.edu"
```

---

## Step 3: Create the Repository on GitHub

### Option A: Using GitHub Website (simplest)

1. Go to [github.com/new](https://github.com/new)
2. **Repository name:** `GeoMesa-Food-Access`
3. **Description:** `Agent-based model for evaluating food access interventions in Health Zone 1, Jacksonville, FL`
4. **Visibility:** Private
5. Do **not** initialize with README, .gitignore, or license (we already have them)
6. Click **Create repository**

### Option B: Using GitHub CLI (if you install it)

```bash
brew install gh
gh auth login
gh repo create GeoMesa-Food-Access --private --source=. --remote=origin --push
```

---

## Step 4: Push the Code

From the project directory:

```bash
cd /Users/goshtasbshahriari/Desktop/Code/GeoMesa_Food_Access

# Initialize git (already done if you ran the setup)
git init
git add .
git status   # Review what will be committed
git commit -m "Initial commit: GeoMesa Food Access ABM for dissertation and journal"

# Add your GitHub repo as remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/GeoMesa-Food-Access.git

# Push (you may be prompted for GitHub credentials)
git branch -M main
git push -u origin main
```

### Authentication

- **HTTPS:** Use a [Personal Access Token](https://github.com/settings/tokens) instead of a password
- **SSH:** Use `git@github.com:YOUR_USERNAME/GeoMesa-Food-Access.git` as the remote URL if you have SSH keys set up

---

## Step 5: Before Making Public (for journal)

1. Update `CITATION.cff` with your name, email, and the final repo URL
2. Update `LICENSE` with your name in the copyright line
3. Add a `DOI` badge if you get one (e.g., from Zenodo)
4. In GitHub: **Settings** → **General** → **Danger Zone** → **Change visibility** → **Public**

---

## Quick Reference

| Item | Value |
|------|-------|
| Repo name | `GeoMesa-Food-Access` |
| Clone URL | `https://github.com/YOUR_USERNAME/GeoMesa-Food-Access.git` |
| Default branch | `main` |
