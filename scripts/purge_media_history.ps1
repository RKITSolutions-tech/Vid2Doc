<#
purge_media_history.ps1
Removes media files from git history (all branches & tags) using git-filter-repo.
Usage:
  Set-Location 'C:\GitHub\VideoDcumentation-clean2'
  powershell -ExecutionPolicy Bypass -File .\purge_media_history.ps1
#>

Write-Output "=== purge_media_history.ps1 starting ==="
$repo = (Get-Location).Path
Write-Output "Repository: $repo"

# Make a timestamped mirror backup (safe rollback)
$stamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
$backupDir = Join-Path (Split-Path $repo -Parent) ("VideoDcumentation-backup-$stamp.git")
Write-Output "Creating bare mirror backup at: $backupDir"
git clone --mirror $repo $backupDir
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create bare mirror backup. Aborting."; exit 1 }

# Find media file paths in history
Write-Output "Scanning history for media file paths..."
# pattern: common media extensions
$regex = '\.(mp4|mov|avi|mkv|wav|mp3|flac|ogg|png|jpe?g)$'
$pathsFile = Join-Path $repo 'media_paths_to_remove.txt'

git rev-list --objects --all | Select-String -Pattern $regex | ForEach-Object {
    # each line is "<sha> <path>" - extract path
    $parts = $_.Line -split ' ',2
    if ($parts.Length -ge 2) { $parts[1].Trim() }
} | Sort-Object -Unique | Out-File -FilePath $pathsFile -Encoding utf8

if ((Get-Item $pathsFile).Length -eq 0) {
    Write-Output "No historical media paths found. File $pathsFile is empty. Nothing to remove."
    Remove-Item -LiteralPath $pathsFile -ErrorAction SilentlyContinue
    Write-Output "=== Completed (no media found) ==="
    exit 0
}

Write-Output "Found the following media paths (saved to $pathsFile):"
Get-Content $pathsFile | ForEach-Object { Write-Output " - $_" }

# Confirm before destructive rewrite
$confirm = Read-Host "Proceed to permanently remove these paths from history? Type 'yes' to continue"
if ($confirm -ne 'yes') {
    Write-Output "Aborted by user. No changes made."
    exit 0
}

# Run git-filter-repo using paths-from-file
Write-Output "Running git-filter-repo to purge media files from history..."
if (Get-Command git-filter-repo -ErrorAction SilentlyContinue) {
    git-filter-repo --invert-paths --paths-from-file $pathsFile --force
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python -m git_filter_repo --invert-paths --paths-from-file $pathsFile --force
} else {
    Write-Error "git-filter-repo not found and python not found. Install git-filter-repo (pip install git-filter-repo) and retry."
    exit 1
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "git-filter-repo failed. Check output and do not push changes upstream. You can restore from the bare mirror at $backupDir."
    exit 2
}

Write-Output "git-filter-repo finished. Running git maintenance..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

Write-Output "--- Verification checks ---"
Write-Output "Working-tree search for media literal paths (should be none):"
git rev-list --objects --all | Select-String -Pattern $regex | ForEach-Object { $_.Line } | ForEach-Object { Write-Output "HIT: $_" }

Write-Output "List top 25 largest blobs (for manual review):"
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' 2>$null | Select-String '^blob' | ForEach-Object { $_.Line } | Sort-Object {[int]($_ -split '\s+')[2]} -Descending | Select-Object -First 25 | ForEach-Object { Write-Output $_ }

Write-Output "=== purge_media_history.ps1 completed ==="