$base = 'https://web-production-3e775.up.railway.app'
try {
  $h = (Invoke-WebRequest -Uri "$base/health" -UseBasicParsing).Content
  Write-Output "HEALTH: $h"
} catch { Write-Output ("HEALTH ERR: " + $_.Exception.Message) }

try {
  Invoke-WebRequest -Uri "$base/ghl/webhook" -Method POST -Body '{}' -ContentType 'application/json' -UseBasicParsing | Out-Null
  Write-Output "WEBHOOK: unexpected 200 (should be 401)"
} catch {
  Write-Output ("WEBHOOK unsigned -> HTTP " + $_.Exception.Response.StatusCode.value__ + " (expect 401)")
}

try {
  $s = (Invoke-WebRequest -Uri "$base/setup?locationId=RcXvnhZX2KTG0jxRASqD" -UseBasicParsing).Content
  Write-Output ("SETUP page bytes: " + $s.Length + " | hasCopy=" + ($s -match 'Copy') + " | hasHero=" + ($s -match 'Connect Bulkgate SMS'))
} catch { Write-Output ("SETUP ERR: " + $_.Exception.Message) }
