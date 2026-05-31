[Console]::OutputEncoding = [Text.Encoding]::UTF8
$progress = Join-Path (Get-Location) "progress.md"
if (-not (Test-Path $progress)) { return }
$text = Get-Content $progress -Raw -Encoding UTF8
$matches = [regex]::Matches($text, '(?m)^##\s+(\d{4}-\d{2}-\d{2})\s*$')
if ($matches.Count -eq 0) { return }
$dates = @()
foreach ($m in $matches) { $dates += [datetime]::ParseExact($m.Groups[1].Value, 'yyyy-MM-dd', $null) }
$bad = $false
for ($i = 1; $i -lt $dates.Count; $i++) {
  if ($dates[$i] -gt $dates[$i-1]) { $bad = $true }
}
$warning = $null
if ($bad) {
  $warning = 'progress.md 日期标题不是倒序。必须修正为最新日期在最上方。'
} else {
  $warning = '更新 progress.md 时请确认：新记录必须插入到当天日期标题下方第一条，禁止追加到文件末尾。'
}
$json = @{ hookSpecificOutput = @{ hookEventName = 'ProgressOrderCheck'; additionalContext = "【过程文件顺序检查】$warning" } } | ConvertTo-Json -Compress
Write-Output $json
