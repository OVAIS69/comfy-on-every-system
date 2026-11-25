param(
    [int]$Width = 864,
    [int]$Height = 480,
    [int]$Length = 81,
    [int]$Steps = 4,
    [string]$Prompt = "A cinematic shot of a red fox walking through a snowy pine forest at sunrise, soft golden light, shallow depth of field, photorealistic.",
    [string]$Upscaler = "4x-UltraSharp.safetensors",
    [int]$OutWidth = 1920,
    [int]$OutHeight = 1080,
    [int]$Seed = 42
)

$server = "http://127.0.0.1:8188"

$body = @{
    prompt = @{
        "1"  = @{ class_type = "UnetLoaderGGUF"; inputs = @{ unet_name = "Wan22-Turbo-Q4_K_M.gguf" } }
        "2"  = @{ class_type = "CLIPLoaderGGUF"; inputs = @{ clip_name = "umt5-xxl-encoder-Q4_K_M.gguf"; type = "wan" } }
        "3"  = @{ class_type = "VAELoader"; inputs = @{ vae_name = "wan2.2_vae.safetensors" } }
        "4"  = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $Prompt; clip = @("2", 0) } }
        "5"  = @{ class_type = "Wan22ImageToVideoLatent"; inputs = @{ vae = @("3", 0); width = $Width; height = $Height; length = $Length; batch_size = 1 } }
        "6"  = @{ class_type = "ModelSamplingSD3"; inputs = @{ model = @("1", 0); shift = 8.0 } }
        "7"  = @{ class_type = "KSampler"; inputs = @{ model = @("6", 0); positive = @("4", 0); negative = @("4", 0); latent_image = @("5", 0); seed = $Seed; steps = $Steps; cfg = 1.0; sampler_name = "euler"; scheduler = "simple"; denoise = 1.0 } }
        "8"  = @{ class_type = "VAEDecode"; inputs = @{ samples = @("7", 0); vae = @("3", 0) } }
        "9"  = @{ class_type = "UpscaleModelLoader"; inputs = @{ model_name = $Upscaler } }
        "10" = @{ class_type = "ImageUpscaleWithModel"; inputs = @{ upscale_model = @("9", 0); image = @("8", 0) } }
        "11" = @{ class_type = "ImageScale"; inputs = @{ image = @("10", 0); upscale_method = "lanczos"; width = $OutWidth; height = $OutHeight; crop = "center" } }
        "12" = @{ class_type = "CreateVideo"; inputs = @{ images = @("11", 0); fps = 24.0 } }
        "13" = @{ class_type = "SaveVideo"; inputs = @{ video = @("12", 0); filename_prefix = "video/wan22_1080p"; format = "auto"; codec = "auto" } }
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
    Write-Host ("[{0}] elapsed={1}s running={2} pending={3}" -f (Get-Date -Format HH:mm:ss), [math]::Round(((Get-Date)-$start).TotalSeconds), $q.queue_running.Count, $q.queue_pending.Count)
    if (((Get-Date) - $start).TotalMinutes -gt 45) {
        Write-Host "TIMEOUT" -ForegroundColor Yellow
        break
    }
}
