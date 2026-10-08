# Joomla → WordPress announcements migrator

Scripts for migrating the announcements of a Joomla site to WordPress **without admin access to Joomla**. Everything is collected from the public RSS feed of the announcements category, so no database dump or back-end login is needed.

Written for `https://vo.duth.gr/index.php/el/anakoinoseis`, but it should work with any Joomla site whose category feed is enabled.

## How it works

1. `scrape.py` pages through the Joomla RSS feed, collects every announcement (title, date, slug, HTML content) into `announcements.csv`, and lists all linked attachments and images in `files.txt`.
2. `download.py` downloads every file in `files.txt`, keeping the original folder structure.
3. `byyear.py` puts every attachment in a folder named after the year of the announcement that links to it, rewrites the links inside the announcements, and writes `announcements_new.csv` (the file to import into WordPress) together with the redirect rules.
4. `checklocal.py` checks the result locally, before anything is uploaded.
5. `redirectlist.py` writes the old → new URL lists, one text file per year, and can test the redirects on a server.
6. `wayback.py` and `casefix.py` are optional helpers for missing files and for file names that differ only in letter case.

## Repository layout

Scripts:

| Script | Description |
|---|---|
| `scrape.py` | Reads the feed; generates `announcements.csv` and `files.txt`. |
| `download.py` | Downloads the attachments into `downloads/`. Skips files that already exist, so it can be re-run. |
| `wayback.py` | Optional. Looks up files that returned 404 in the Internet Archive. |
| `casefix.py` | Optional. Finds URLs that differ only in letter case and downloads both variants into `downloads_case/1/` and `downloads_case/2/`. |
| `byyear.py` | Builds the year folders, `announcements_new.csv` and the redirect rules. `--verify` checks the files on a server. |
| `checklocal.py` | Local quality check of everything `byyear.py` produced. |
| `redirectlist.py` | Writes the redirect lists per year; `--test` checks the redirects on a server. |
| `rewrite.py`, `verify.py` | Legacy: an older, simpler version without year folders. `byyear.py` replaces both. |

Generated files (not committed):

| File / folder | Description |
|---|---|
| `announcements.csv` | One row per announcement, with the original links. |
| `files.txt` | One attachment URL per line. |
| `failed.txt` | Files that could not be downloaded (URL and error), usually 404s of deleted files. |
| `downloads/`, `downloads_case/` | Downloaded files, as they were on the old site. |
| `announcements_new.csv` | Announcements with rewritten links and a `year` column. **This is the file to import.** |
| `downloads_byyear/` | The files organised by year. **This is what you upload.** |
| `downloads_byyear_extra/` | Only if two names differ only in letter case within the same year (see below). Upload it to the same place. |
| `files_byyear.csv` | List of the new files with size and hash, used by `--verify`. |
| `redirects_nginx.conf`, `redirects_apache.htaccess` | One redirect rule per file, plus one for the announcement URLs. |
| `redirects_byyear/redirects_<year>.txt` | Old URL → new URL, one file per year. |
| `redirects_by_year.txt` | The same lists, all years in one file. |

## Requirements

- Python 3.9+
- `requests` and `beautifulsoup4`

```bash
pip install requests beautifulsoup4
```

On Windows, if `pip` is not recognised, use `python -m pip install requests beautifulsoup4`.

## Settings

There is no configuration file. The settings are constants at the top of the scripts:

| Script | Constant | Meaning |
|---|---|---|
| `scrape.py` | `FEED` | Joomla category page that lists the announcements (without `?format=feed`). |
| `byyear.py` | `SITE` | Address of the old site, no trailing slash. |
| `byyear.py` | `OLD_MEDIA` | Folder of the old site that holds attachments and images (`/images/`). |
| `byyear.py` | `NEW_BASE` | Folder of the new site where the year folders go (`/wp-content/uploads/vo-archive/`). |
| `byyear.py` | `OLD_POST_PATH`, `NEW_POST_PATH` | URL prefix of the announcements before and after the migration. |
| `byyear.py` | `BROKEN_NOTE` | Text added where a link to a missing file was removed. |

`NEW_BASE` is a path starting with `/`, so the links work unchanged on a staging site and on the live site.

## Usage

Run from the project folder, in this order.

### 1. Collect the announcements

```bash
python scrape.py
```

Progress is printed while the feed is paged through. At the end you get a summary such as `940 announcements, N files`.

### 2. Download the attachments

```bash
python download.py
```

Files are saved under `downloads/`, mirroring the paths used on the old site. Failed downloads are written to `failed.txt`. If new announcements appear later, run `scrape.py` and `download.py` again.

### 3. Optional helpers

```bash
python wayback.py     # is there an Internet Archive copy of the files that returned 404?
python casefix.py     # files whose names differ only in letter case
```

Windows treats `File.pdf` and `file.pdf` as the same file, while the old server and a Linux server do not. `casefix.py` downloads both variants, so that `byyear.py` can place both on the server under their exact names.

### 4. Organise by year and rewrite the links

```bash
python byyear.py
```

Every file goes into the folder of the **earliest** announcement that links to it:

```
downloads_byyear/2025/pdf/file.pdf      ->  /wp-content/uploads/vo-archive/2025/pdf/file.pdf
```

The sub-folder (`pdf`, `word`, …) of the old site is kept, so names never collide between folders. A file linked from announcements of several years stays in one folder, and all announcements point to it. Links to files that no longer exist are removed and replaced by the text in `BROKEN_NOTE`. `tel:` and `mailto:` links that the feed turned into site URLs are repaired. The script prints a report: files per year, files shared between years, missing files, and links to old pages outside the media folder (these need a manual fix after the import).

### 5. Check everything locally

```bash
python checklocal.py
```

It checks the CSV (row counts, dates, years, duplicate slugs), that every link points to an existing file (with exact letter case), that no old links remain, the file types (no `.php`, `.html`, executables), empty files, the manifest, and the redirect files. It prints `OK`, `WARN` and `ERROR` lines; fix all errors before uploading. Expected warnings: links to old pages of the site, files with Greek names (see the upload notes), and the `downloads_byyear_extra` reminder.

### 6. Redirect lists

```bash
python redirectlist.py
```

Writes `redirects_byyear/redirects_<year>.txt` (and `redirects_by_year.txt`). Each line is `old URL<TAB>new URL`; lines starting with `#` are comments.

## CSV format

| Column | Meaning |
|---|---|
| `title` | Announcement title. |
| `old_slug` | Original Joomla slug, kept for the redirects. |
| `slug` | Slug for WordPress, truncated to 200 characters (the WordPress limit). |
| `date` | Original publication date, `YYYY-MM-DD HH:MM:SS`, in the server's local time. |
| `content` | Cleaned HTML body. |
| `year` | Year of the date (only in `announcements_new.csv`), used for categories. |

The files are UTF-8 with BOM, so Greek text opens correctly in Excel.

## Uploading the files

- **Do not upload a zip made on Windows** if any file name contains non-ASCII (e.g. Greek) characters: `Compress-Archive` stores such names with an encoding that many Linux servers and hosting panels cannot read, which leaves broken names and 404s. Upload the folders over SFTP (FileZilla, WinSCP) or with `scp`.
- Upload the **contents** of `downloads_byyear/` (and `downloads_byyear_extra/`, if it exists) to the folder given by `NEW_BASE`, so that you get `wp-content/uploads/vo-archive/2022/`, `.../2023/`, and so on.
- Check the upload:

```bash
python byyear.py --verify https://NEW-SITE
```

It requests every file and compares status and size with `files_byyear.csv`. The result should be `all OK`.

## Testing on a staging site (optional)

A throw-away WordPress on a NAS or any machine with Docker (WordPress and MariaDB containers) is a convenient staging site.

```bash
scp -O -r downloads_byyear user@NAS:~/staging-files/
docker cp ~/staging-files/downloads_byyear/. CONTAINER:/var/www/html/wp-content/uploads/vo-archive/
docker exec CONTAINER chown -R www-data:www-data /var/www/html/wp-content/uploads/vo-archive
```

Notes:

- Newer OpenSSH versions use the SFTP protocol for `scp`. NAS systems without an SFTP subsystem fail with `subsystem request failed`; the `-O` flag selects the classic protocol.
- Keep the staging site private (firewall, no search engine indexing) and do not commit a `docker-compose.yml` that contains real passwords.

## Importing into WordPress

Before the import: set the timezone to the site's local time (Settings → General), otherwise dates and years shift. Set the permalink structure to `/anakoinoseis/%postname%/` (it must match `NEW_POST_PATH`).

Import `announcements_new.csv` with a plugin such as **WP All Import**:

- `title` → Title, `content` → Content, `slug` → Post Slug, `date` → Date
- Categories: a fixed "Announcements" category and a second one from `{year}` (one category per year)
- Unique identifier: `{old_slug}` (prevents duplicates if the import is run again)

Afterwards check the number of posts, the categories per year, and some announcements from different years, including their file links. Replace the links to old Joomla pages reported by `byyear.py` with their new equivalents.

## Redirects (same domain)

When the new site replaces Joomla on the same domain, old links (bookmarks, other sites, e-mails already sent) must keep working. Two kinds of URLs are redirected:

1. **Attachments**: `/images/...` → `/wp-content/uploads/vo-archive/<year>/...`. The year differs per file, so there is one rule per file.
2. **Announcements**: `/index.php/el/anakoinoseis/<old_slug>` → `/anakoinoseis/<old_slug>/`.

`byyear.py` generates both sets of rules:

- **Plesk with nginx in front of Apache (recommended):** paste `redirects_nginx.conf` into *Websites & Domains → the domain → Apache & nginx Settings → Additional nginx directives*. Static files such as PDFs and images are often served by nginx directly and never reach Apache, so `.htaccess` rules would not apply to them.
- **Plain Apache (also the official WordPress Docker image):** paste `redirects_apache.htaccess` into `.htaccess`, above the `# BEGIN WordPress` block.

Test the redirects with a sample, or with all URLs:

```bash
python redirectlist.py --test https://NEW-SITE --sample 100
python redirectlist.py --test https://NEW-SITE
```

Each old URL must answer `301` with the expected new address. A single URL can be checked by hand:

```powershell
curl.exe -I https://NEW-SITE/images/some-file.pdf
```

## Notes and limitations

- The feed returns 15–16 items per request. The scraper advances by the number of items received and stops at the first empty page.
- Links are collected from `href` and `src` attributes that point to the old media folder. Files hosted elsewhere (Google Forms, e-learning platforms, other websites) are left unchanged.
- WordPress may change a slug (for example by adding `-2` to a duplicate). If `--test` reports such a case, fix the redirect for that URL.
- Only one category is covered per run. Other categories have their own feed URLs.
- The scripts wait between requests to be polite to the server.
- Some old attachments may no longer exist on the server. Check `failed.txt` after downloading.
- Downloaded files, generated CSVs and redirect lists are not committed to Git (see `.gitignore`).
