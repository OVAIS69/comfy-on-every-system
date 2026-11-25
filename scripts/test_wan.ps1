param(
    [int]$Width = 704,
    [int]$Height = 480,
    [int]$Length = 81,
    [int]$Steps = 4,
    [string]$Prompt = "A cinematic shot of a red fox walking through a snowy pine forest at sunrise, soft golden light, shallow depth of field, photorealistic.",
    [int]$Seed = 42
)

$server = "http://127.0.0.1:8188"

$neg = "Oversaturated colours, overexposed, static frame, blurry details, subtitles, watermark, artwork, painting, cartoon, low quality, worst quality, jpeg artifacts, ugly, deformed, extra fingers, poorly drawn hands, poorly drawn face, malformed limbs, fused fingers, motionless scene, cluttered background"

$body = @{
    prompt = @{
        "37" = @{ class_type = "UnetLoaderGGUF"; inputs = @{ unet_name = "Wan22-Turbo-Q4_K_M.gguf" } }
        "38" = @{ class_type = "CLIPLoaderGGUF"; inputs = @{ clip_name = "umt5-xxl-encoder-Q4_K_M.gguf"; type = "wan" } }
        "39" = @{ class_type = "VAELoader"; inputs = @{ vae_name = "wan2.2_vae.safetensors" } }
        "48" = @{ class_type = "ModelSamplingSD3"; inputs = @{ model = @("37", 0); shift = 8.0 } }
        "6"  = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $Prompt; clip = @("38", 0) } }
        "55" = @{ class_type = "Wan22ImageToVideoLatent"; inputs = @{ vae = @("39", 0); width = $Width; height = $Height; length = $Length; batch_size = 1 } }
        "3"  = @{ class_type = "KSampler"; inputs = @{ model = @("48", 0); positive = @("6", 0); negative = @("6", 0); latent_image = @("55", 0); seed = $Seed; steps = $Steps; cfg = 1.0; sampler_name = "euler"; scheduler = "simple"; denoise = 1.0 } }
        "8"  = @{ class_type = "VAEDecode"; inputs = @{ samples = @("3", 0); vae = @("39", 0) } }
        "57" = @{ class_type = "CreateVideo"; inputs = @{ images = @("8", 0); fps = 24.0 } }
        "58" = @{ class_type = "SaveVideo"; inputs = @{ video = @("57", 0); filename_prefix = "video/wan22_test"; format = "auto"; codec = "auto" } }
    }
} | ConvertTo-Json -Depth 20

try {
    $resp = Invoke-RestMethod -Uri "$server/prompt" -Method Post -Body $body -ContentType "application/json"
} catch {
    Write-Host "SUBMIT FAILED:" -ForegroundColor Red
    $_.ErrorDetails.Message
    exit 1
}

if ($resp.node_errors -and $resp.node_errors.PSObject.Properties.Count -gt 0) {
    Write-Host "NODE ERRORS:" -ForegroundColor Red
    $resp.node_errors | ConvertTo-Json -Depth 10
    exit 1
}

$id = $resp.prompt_id
Write-Host "Queued prompt: $id" -ForegroundColor Green

$start = Get-Date
while ($true) {
    Start-Sleep -Seconds 5
    $h = Invoke-RestMethod -Uri "$server/history/$id"
    $entry = $h.$id
    if ($entry) {
        $elapsed = [math]::Round(((Get-Date) - $start).TotalSeconds, 1)
        if ($entry.status.status_str -eq "success") {
            Write-Host "SUCCESS in ${elapsed}s" -ForegroundColor Green
            $entry.outputs.PSObject.Properties | ForEach-Object {
                Write-Host ("node " + $_.Name + ": " + ($_.Value | ConvertTo-Json -Depth 6 -Compress))
            }
            break
        } elseif ($entry.status.status_str -eq "error") {
            Write-Host "EXECUTION ERROR after ${elapsed}s" -ForegroundColor Red
            $entry.status | ConvertTo-Json -Depth 10
            break
        }
    }
    $q = Invoke-RestMethod -Uri "$server/queue"
    $running = $q.queue_running.Count
    $pending = $q.queue_pending.Count
    Write-Host ("[{0}] elapsed={1}s running={2} pending={3}" -f (Get-Date -Format HH:mm:ss), [math]::Round(((Get-Date)-$start).TotalSeconds), $running, $pending)
    if (((Get-Date) - $start).TotalMinutes -gt 45) {
        Write-Host "TIMEOUT" -ForegroundColor Yellow
        break
    }
}
