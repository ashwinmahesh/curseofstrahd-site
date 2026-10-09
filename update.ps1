# Updates Curse of Strahd (an unofficial fan game) on this PC to the newest version.
#
#   irm https://curseofstrahd.app/update.ps1 | iex
#
# Run it in PowerShell from the folder you unzipped the game into (the one with CurseOfStrahd.exe), or it asks for
# that folder. It reads the newest version from https://downloads.curseofstrahd.app/latest.json. When the game you
# have is the full download that version builds on, it fetches only a patch (the files that changed) into the game's
# folder beside your saves; otherwise it downloads the whole game and replaces CurseOfStrahd.exe and
# CurseOfStrahd.pck. Your saves and settings (%APPDATA%\Curse of Strahd Fan Game) aren't touched.
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # Invoke-WebRequest is many times slower with its progress bar
$downloads = "https://downloads.curseofstrahd.app"
$patches = Join-Path $env:APPDATA "Curse of Strahd Fan Game\patches"

$folder = (Get-Location).Path
if (-not (Test-Path (Join-Path $folder "CurseOfStrahd.exe"))) {
	$folder = (Read-Host "Folder that holds CurseOfStrahd.exe").Trim('"')
	if (-not (Test-Path (Join-Path $folder "CurseOfStrahd.exe"))) { throw "No CurseOfStrahd.exe in $folder" }
}
if (Get-Process -Name "CurseOfStrahd" -ErrorAction SilentlyContinue) {
	throw "Curse of Strahd is running. Quit it first, then run this again."
}

$latest = Invoke-RestMethod "$downloads/latest.json?$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
$url = [string]$latest.windows
if (-not $url.StartsWith("$downloads/") -or -not $url.EndsWith(".zip")) {
	throw "Unexpected download address in latest.json: $url"
}
# The full download's version, from the .exe's file details (1.0.3.0 for 1.0.3).
$installed = ((Get-Item (Join-Path $folder "CurseOfStrahd.exe")).VersionInfo.ProductVersion -replace '\.0$', '')
$current = $installed
$patchInfo = Join-Path $patches "patch.json"
if (Test-Path $patchInfo) {
	$have = Get-Content $patchInfo -Raw | ConvertFrom-Json
	if ($have.base -eq $installed) { $current = [string]$have.version }
}
if ($current -eq $latest.version) {
	Write-Host "Curse of Strahd is already on $($latest.version)."
	return
}

$work = Join-Path ([IO.Path]::GetTempPath()) ("curseofstrahd-update-" + [Guid]::NewGuid())
New-Item -ItemType Directory -Path $work | Out-Null
try {
	if ($installed -eq $latest.base -and $latest.patch -and $latest.version -ne $latest.base) {
		Write-Host ("Updating Curse of Strahd from $current to $($latest.version) with a patch of {0} MB..." -f [math]::Round($latest.patch.size / 1MB))
		$pck = Join-Path $work "patch.pck"
		Invoke-WebRequest -Uri "$downloads/$($latest.version)/$($latest.patch.file)" -OutFile $pck
		if ((Get-FileHash $pck -Algorithm SHA256).Hash.ToLower() -ne $latest.patch.sha256) {
			throw "The patch didn't download intact. Run this again."
		}
		New-Item -ItemType Directory -Force -Path $patches | Out-Null
		Move-Item -Force $pck (Join-Path $patches "patch.pck")
		@{ base = $latest.base; version = $latest.version } | ConvertTo-Json | Set-Content -Encoding UTF8 $patchInfo
		Write-Host "Done: Curse of Strahd is on $($latest.version). Your saves and settings carry over."
		return
	}
	Write-Host "Updating Curse of Strahd from $current to $($latest.version) (a full download of about 3 GB)..."
	$zip = Join-Path $work "game.zip"
	Invoke-WebRequest -Uri $url -OutFile $zip
	# Windows 10 and 11 ship tar, which reads zips with files over 4 GB.
	tar -xf $zip -C $work
	if ($LASTEXITCODE -ne 0) { throw "Couldn't unpack the download" }
	foreach ($name in "CurseOfStrahd.exe", "CurseOfStrahd.pck") {
		Move-Item -Force (Join-Path $work $name) (Join-Path $folder $name)
	}
	# An old patch builds on the old download; the game would ignore it, so it goes.
	Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $patches "patch.pck"), $patchInfo
	Write-Host "Done: Curse of Strahd $($latest.version) is in $folder. Your saves and settings carry over."
}
finally {
	Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}
