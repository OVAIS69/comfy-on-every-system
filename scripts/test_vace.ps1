param(
    [int]$Width = 704,
    [int]$Height = 480,
    [int]$Length = 33,
    [int]$Steps = 20,
    [double]$Cfg = 6.0,
    [string]$Image = "example.png",
    [string]$Prompt = "The person from the reference image stands in a neon-lit alley at night, cinematic lighting, shallow depth of field, slow camera dolly, detailed face.",
    [int]$Seed = 42
)

$server = "http://127.0.0.1:8188"

$neg = "Oversaturated colours, overexposed, static frame, blurry details, subtitles, watermark, artwork, painting, cartoon, low quality, worst quality, jpeg artifacts, ugly, deformed, extra fingers, poorly drawn hands, poorly drawn face, malformed limbs, fused fingers, motionless scene, cluttered background"

$body = @{
    prompt = @{
        "1"  = @{ class_type = "UnetLoaderGGUF"; inputs = @{ unet_name = "Wan21-VACE-1.3B-Q8_0.gguf" } }
        "2"  = @{ class_type = "CLIPLoaderGGUF"; inputs = @{ clip_name = "umt5-xxl-encoder-Q4_K_M.gguf"; type = "wan" } }
        "3"  = @{ class_type = "VAELoader"; inputs = @{ vae_name = "wan_2.1_vae.safetensors" } }
        "4"  = @{ class_type = "LoadImage"; inputs = @{ image = $Image } }
        "5"  = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $Prompt; clip = @("2", 0) } }
        "6"  = @{ class_type = "CLIPTextEncode"; inputs = @{ text = $neg; clip = @("2", 0) } }
        "7"  = @{ class_type = "WanVaceToVideo"; inputs = @{ positive = @("5", 0); negative = @("6", 0); vae = @("3", 0); reference_image = @("4", 0); width = $Width; height = $Height; length = $Length; batch_size = 1; strength = 1.0 } }
        "8"  = @{ class_type = "ModelSamplingSD3"; inputs = @{ model = @("1", 0); shift = 8.0 } }
        "9"  = @{ class_type = "KSampler"; inputs = @{ model = @("8", 0); positive = @("7", 0); negative = @("7", 1); latent_image = @("7", 2); seed = $Seed; steps = $Steps; cfg = $Cfg; sampler_name = "uni_pc"; scheduler = "simple"; denoise = 1.0 } }
        "10" = @{ class_type = "TrimVideoLatent"; inputs = @{ samples = @("9", 0); trim_amount = @("7", 3) } }
        "11" = @{ class_type = "VAEDecode"; inputs = @{ samples = @("10", 0); vae = @("3", 0) } }
        "12" = @{ class_type = "CreateVideo"; inputs = @{ images = @("11", 0); fps = 16.0 } }
        "13" = @{ class_type = "SaveVideo"; inputs = @{ video = @("12", 0); filename_prefix = "video/vace_test"; format = "auto"; codec = "auto" } }
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
