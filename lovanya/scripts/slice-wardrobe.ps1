# Slices the capsule-wardrobe reference grid into individual, auto-trimmed,
# square PNG assets and emits a manifest (category + sampled colors) used to
# generate the seed closet. One-time asset tool.
param(
  [string]$In  = "C:\Users\SpecialXz\Downloads\f070d813-3234-4691-b193-c1db76524172.png",
  [string]$Out = "C:\Users\SpecialXz\Documents\Claude bestie API\lovanya\public\wardrobe",
  [string]$Manifest = "C:\Users\SpecialXz\Documents\Claude bestie API\lovanya\scripts\wardrobe.manifest.json"
)

Add-Type -AssemblyName System.Drawing
$src = New-Object System.Drawing.Bitmap $In
$bgR = 254; $bgG = 254; $bgB = 254
function IsContent($p){ ([math]::Abs($p.R-$bgR)+[math]::Abs($p.G-$bgG)+[math]::Abs($p.B-$bgB)) -gt 22 }

# col: L => x0=10 colW=136.4 ; R => x0=710 colW=136.8
$panels = @(
  @{ key="top";         cat="top";       col="L"; a=@(64,168);  b=@(196,316) },
  @{ key="dress";       cat="dress";     col="R"; a=@(64,192);  b=@(204,340) },
  @{ key="bottom";      cat="bottom";    col="L"; a=@(388,528); b=@(536,648) },
  @{ key="outerwear";   cat="outerwear"; col="R"; a=@(388,518); b=@(518,648) },
  @{ key="shoes";       cat="shoes";     col="L"; a=@(692,772); b=@(796,880) },
  @{ key="bag";         cat="bag";       col="R"; a=@(684,784); b=@(788,888) },
  @{ key="extras";      cat="accessory"; col="L"; a=@(932,1016);b=@(1032,1104) },
  @{ key="accessories"; cat="accessory"; col="R"; a=@(944,1032);b=@(1044,1104) }
)

function ToHex($r,$g,$b){ "#{0:x2}{1:x2}{2:x2}" -f [int]$r,[int]$g,[int]$b }

$records = @()
foreach ($panel in $panels) {
  $dir = Join-Path $Out $panel.key
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  if ($panel.col -eq "L") { $x0 = 10.0; $colW = 136.4 } else { $x0 = 710.0; $colW = 136.8 }

  $rows = @($panel.a, $panel.b)
  for ($r = 0; $r -lt 2; $r++) {
    $rowTop = $rows[$r][0]; $rowBot = $rows[$r][1]
    for ($c = 0; $c -lt 5; $c++) {
      $num = $r * 5 + $c + 1
      $cellX = [int]($x0 + $c * $colW)
      $cellW = [int]$colW
      $cellY = [int]$rowTop
      $cellH = [int]($rowBot - $rowTop)

      # bounding box of content within the cell (sample step 2)
      $minX = 99999; $minY = 99999; $maxX = -1; $maxY = -1
      $sumR = 0.0; $sumG = 0.0; $sumB = 0.0; $n = 0
      $darks = @()
      for ($y = $cellY; $y -lt ($cellY + $cellH); $y += 2) {
        for ($x = $cellX + 3; $x -lt ($cellX + $cellW - 3); $x += 2) {
          if ($x -lt 0 -or $y -lt 0 -or $x -ge $src.Width -or $y -ge $src.Height) { continue }
          $p = $src.GetPixel($x, $y)
          if (IsContent $p) {
            if ($x -lt $minX) { $minX = $x }; if ($x -gt $maxX) { $maxX = $x }
            if ($y -lt $minY) { $minY = $y }; if ($y -gt $maxY) { $maxY = $y }
            $sumR += $p.R; $sumG += $p.G; $sumB += $p.B; $n++
            $lum = 0.299*$p.R + 0.587*$p.G + 0.114*$p.B
            $darks += [pscustomobject]@{ l=$lum; r=$p.R; g=$p.G; b=$p.B }
          }
        }
      }
      if ($n -lt 30 -or $maxX -lt 0) { continue } # empty cell

      # primary = mean content color
      $primary = ToHex ($sumR/$n) ($sumG/$n) ($sumB/$n)
      # secondary = mean of darkest third (captures the garment's deeper tone)
      $sorted = $darks | Sort-Object l
      $third = [math]::Max(1, [int]($darks.Count/3))
      $dr=0.0;$dg=0.0;$db=0.0
      for ($i=0; $i -lt $third; $i++){ $dr+=$sorted[$i].r; $dg+=$sorted[$i].g; $db+=$sorted[$i].b }
      $secondary = ToHex ($dr/$third) ($dg/$third) ($db/$third)

      # pad bbox, clamp, crop, square-pad on white, resize 320
      $pad = 8
      $bx = [math]::Max(0, $minX - $pad); $by = [math]::Max(0, $minY - $pad)
      $bw = [math]::Min($src.Width - $bx, ($maxX - $minX) + 2*$pad)
      $bh = [math]::Min($src.Height - $by, ($maxY - $minY) + 2*$pad)
      $side = [math]::Max($bw, $bh)
      $offX = [int](($side - $bw) / 2); $offY = [int](($side - $bh) / 2)

      $sq = New-Object System.Drawing.Bitmap 320, 320
      $g = [System.Drawing.Graphics]::FromImage($sq)
      $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
      $g.Clear([System.Drawing.Color]::FromArgb(255, 255, 252, 250))
      $scale = 320.0 / $side
      $destX = [int]($offX * $scale); $destY = [int]($offY * $scale)
      $destW = [int]($bw * $scale); $destH = [int]($bh * $scale)
      $destRect = New-Object System.Drawing.Rectangle $destX, $destY, $destW, $destH
      $g.DrawImage($src, $destRect, $bx, $by, $bw, $bh, [System.Drawing.GraphicsUnit]::Pixel)
      $file = Join-Path $dir "$num.png"
      $sq.Save($file, [System.Drawing.Imaging.ImageFormat]::Png)
      $g.Dispose(); $sq.Dispose()

      $records += [pscustomobject]@{
        key = $panel.key; cat = $panel.cat; num = $num
        path = "/wardrobe/$($panel.key)/$num.png"
        primary = $primary; secondary = $secondary
      }
    }
  }
}
$src.Dispose()
$records | ConvertTo-Json -Depth 4 | Set-Content -Path $Manifest -Encoding utf8
"Sliced $($records.Count) items -> $Out"