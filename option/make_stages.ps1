# ブロック崩し（スマホ版 3ステージ）の画像をまとめて作るスクリプト
#   block1a/b/c.png … ステージ1 農村（朝 → 夜）
#   block2a/b/c.png … ステージ2 街（朝 → 夜）
#   block3a/b/c.png … ステージ3 花（つぼみ → 開花）
#   a = 最初の絵 / b = ブロックを崩すと見える絵 / c = ステージセレクト用サムネイル（a の縮小版）
#   clear.png       … 3ステージすべてクリアしたときのご褒美画面（1206×2622）
#
# 画像ファイルではなく、図形をプログラムで描いて作っています。
# 何も指定しなければ、このスクリプトと同じフォルダ（option）に保存します。
# （ゲームで使っている画像は上書きしません。使うときは block フォルダへコピーしてください）
# 実行例: .\make_stages.ps1
#         .\make_stages.ps1 -OutDir C:\temp
param([string]$OutDir)
if (-not $OutDir) { $OutDir = $PSScriptRoot }
$OutDir = (Resolve-Path $OutDir).Path
Add-Type -AssemblyName System.Drawing

$BW = 374; $BH = 320   # ブロック領域の大きさ（設計上の座標）
$SC = 3                # 出力倍率（iPhone は3倍表示）→ 1122×960

# ---------- 共通の道具 ----------
function C([string]$hex, [int]$a = 255) {
  $c = [System.Drawing.ColorTranslator]::FromHtml($hex)
  return [System.Drawing.Color]::FromArgb($a, $c.R, $c.G, $c.B)
}
function Brush($hex, $a = 255) { New-Object System.Drawing.SolidBrush (C $hex $a) }
function Pts($arr) {
  $list = New-Object 'System.Collections.Generic.List[System.Drawing.PointF]'
  for ($i = 0; $i -lt $arr.Count; $i += 2) { $list.Add((New-Object System.Drawing.PointF ([float]$arr[$i]), ([float]$arr[$i+1]))) }
  return $list.ToArray()
}
function Sky($g, $top, $bot, $h) {
  $rect = New-Object System.Drawing.RectangleF 0, 0, $BW, $h
  $b = New-Object System.Drawing.Drawing2D.LinearGradientBrush $rect, (C $top), (C $bot), 90
  $g.FillRectangle($b, 0, 0, $BW, $BH)
}
function Stars($g, $rnd, $n, $maxY) {
  for ($i = 0; $i -lt $n; $i++) {
    $x = $rnd.NextDouble() * $BW; $y = $rnd.NextDouble() * $maxY; $s = $rnd.NextDouble() * 1.4 + 0.5
    $g.FillEllipse((Brush '#FFFFFF' ($rnd.Next(120, 255))), [float]$x, [float]$y, [float]$s, [float]$s)
  }
}
function Moon($g, $cx, $cy) {
  $cut = New-Object System.Drawing.Drawing2D.GraphicsPath
  $cut.AddEllipse([float]($cx - 9), [float]($cy - 29), 44, 44)
  $g.SetClip($cut, [System.Drawing.Drawing2D.CombineMode]::Exclude)
  for ($r = 44; $r -gt 22; $r -= 4) { $g.FillEllipse((Brush '#FFF5C0' 14), $cx - $r, $cy - $r, $r * 2, $r * 2) }
  $g.ResetClip()
  $mp = New-Object System.Drawing.Drawing2D.GraphicsPath
  $mp.AddEllipse([float]($cx - 22), [float]($cy - 22), 44, 44)
  $rg = New-Object System.Drawing.Region $mp
  $rg.Exclude($cut)
  $g.FillRegion((Brush '#FFF3B0'), $rg)
}
function Sun($g, $cx, $cy) {
  for ($r = 66; $r -gt 24; $r -= 6) { $g.FillEllipse((Brush '#FFF2C0' 30), $cx - $r, $cy - $r, $r * 2, $r * 2) }
  $g.FillEllipse((Brush '#FFD966'), $cx - 24, $cy - 24, 48, 48)
}
function Cloud($g, $cx, $cy) {
  $b = Brush '#FFFFFF' 220
  $g.FillEllipse($b, $cx, $cy, 60, 18); $g.FillEllipse($b, $cx + 18, $cy - 9, 42, 22); $g.FillEllipse($b, $cx + 40, $cy - 2, 50, 18)
}
# (cx,cy) を中心に angle 度回した楕円（中心から offset 離れた位置に置く）
function RotEllipse($g, $cx, $cy, $angle, $w, $h, $offset, $brush) {
  $st = $g.Save()
  $g.TranslateTransform([float]$cx, [float]$cy)
  $g.RotateTransform([float]$angle)
  $g.FillEllipse($brush, [float](-$w / 2), [float](-$offset - $h), [float]$w, [float]$h)
  $g.Restore($st)
}

# ---------- ステージ1：農村 ----------
function Draw-House($g, $hx, $hy, $s, $wall, $roof, $win, $night) {
  $bw = 60 * $s; $bh = 26 * $s
  $g.FillRectangle((Brush $wall), [float]$hx, [float]($hy - $bh), [float]$bw, [float]$bh)
  $g.FillPolygon((Brush $roof), (Pts @(($hx - 8*$s), ($hy - $bh), ($hx + $bw/2), ($hy - $bh - 28*$s), ($hx + $bw + 8*$s), ($hy - $bh))))
  $wx = $hx + 10 * $s; $wy = $hy - $bh + 8 * $s
  foreach ($dx in @(0, 26)) {
    if ($night) { $g.FillEllipse((Brush $win 50), [float]($wx + $dx*$s - 6*$s), [float]($wy - 6*$s), [float](24*$s), [float](22*$s)) }
    $g.FillRectangle((Brush $win), [float]($wx + $dx*$s), [float]$wy, [float](12*$s), [float](10*$s))
  }
  $g.FillRectangle((Brush $roof), [float]($hx + $bw - 14*$s), [float]($hy - 16*$s), [float](8*$s), [float](16*$s))
}
function Draw-Tree($g, $tx, $ty, $s, $trunk, $leaf, $leaf2) {
  $g.FillRectangle((Brush $trunk), [float]($tx - 2*$s), [float]($ty - 8*$s), [float](4*$s), [float](12*$s))
  $g.FillEllipse((Brush $leaf), [float]($tx - 12*$s), [float]($ty - 30*$s), [float](24*$s), [float](26*$s))
  $g.FillEllipse((Brush $leaf2), [float]($tx - 8*$s), [float]($ty - 28*$s), [float](14*$s), [float](14*$s))
}
function Draw-Farm($g, [bool]$night) {
  if ($night) {
    $skyTop='#0A1230'; $skyBot='#2B3D72'; $farMt='#1C2648'; $midMt='#16233A'
    $hill='#14301F'; $field1='#1D3B26'; $field2='#244630'; $water='#3A4F80'
    $path_='#3A3530'; $wall='#4A4038'; $roof='#2A2218'; $win='#FFD45A'
    $trunk='#2A1E16'; $leaf='#123020'; $leaf2='#183A26'
  } else {
    $skyTop='#7EC0EE'; $skyBot='#FFE6B8'; $farMt='#9DB4D0'; $midMt='#7E9FB8'
    $hill='#6BAA4C'; $field1='#8CC152'; $field2='#A8D46F'; $water='#CFE8F5'
    $path_='#D9C08A'; $wall='#E8DCC0'; $roof='#8A6A3A'; $win='#5A4632'
    $trunk='#6B4A2E'; $leaf='#3E8E3A'; $leaf2='#56A84A'
  }
  Sky $g $skyTop $skyBot 200
  $rnd = New-Object System.Random 11
  if ($night) { Stars $g $rnd 110 140; Moon $g 280 60 }
  else { Sun $g 280 70; Cloud $g 30 40; Cloud $g 140 22; Cloud $g 120 95 }

  $g.FillPolygon((Brush $farMt), (Pts @(0,150, 50,118, 110,140, 180,100, 250,138, 320,112, 374,130, 374,320, 0,320)))
  $g.FillPolygon((Brush $midMt), (Pts @(0,168, 70,145, 140,165, 210,140, 290,166, 374,150, 374,320, 0,320)))
  if (-not $night) { $g.FillRectangle((Brush '#FFFFFF' 60), 0, 158, $BW, 18) }
  $g.FillPolygon((Brush $hill), (Pts @(0,186, 120,176, 250,182, 374,176, 374,320, 0,320)))

  $bands = @(@(190,200), @(200,213), @(213,230), @(230,252), @(252,280), @(280,320))
  $k = 0
  foreach ($bd in $bands) {
    $col = if ($k % 2 -eq 0) { $field1 } else { $field2 }
    $g.FillRectangle((Brush $col), 0, $bd[0], $BW, $bd[1] - $bd[0])
    $wa = if ($night) { 70 } else { 110 }
    $len = 18 + $k * 8; $gap = 50 + $k * 14
    for ($x = ($k * 23) % $gap; $x -lt $BW; $x += $gap) {
      $g.FillRectangle((Brush $water $wa), $x, $bd[0] + 2 + $k, $len, 1.5 + $k * 0.4)
    }
    $g.FillRectangle((Brush $path_ 180), 0, $bd[0], $BW, 1)
    $k++
  }
  $g.FillPolygon((Brush $path_), (Pts @(150,320, 175,280, 190,240, 196,200, 199,186, 204,186, 204,200, 206,240, 214,280, 230,320)))

  foreach ($t in @(@(25,186,0.8), @(60,190,0.9), @(330,184,0.8), @(356,188,0.7))) { Draw-Tree $g $t[0] $t[1] $t[2] $trunk $leaf $leaf2 }
  Draw-House $g 88 188 0.85 $wall $roof $win $night
  Draw-House $g 250 184 0.6 $wall $roof $win $night
  Draw-House $g 262 262 1.25 $wall $roof $win $night
  Draw-Tree $g 40 286 1.5 $trunk $leaf $leaf2
  Draw-Tree $g 92 300 1.2 $trunk $leaf $leaf2

  if ($night) {
    for ($i = 0; $i -lt 45; $i++) {
      $x = $rnd.NextDouble() * $BW; $y = 195 + $rnd.NextDouble() * 120
      $g.FillEllipse((Brush '#E8FF7A' 60), [float]($x - 3), [float]($y - 3), 7, 7)
      $g.FillEllipse((Brush '#F4FFB0'), [float]$x, [float]$y, 2, 2)
    }
  }
}

# ---------- ステージ2：街 ----------
function Draw-Building($g, $x, $w, $h, $body, $winOff, $winOn, $night, $rnd, $ground) {
  $top = $ground - $h
  $g.FillRectangle((Brush $body), [float]$x, [float]$top, [float]$w, [float]$h)
  # 屋上の縁
  $g.FillRectangle((Brush '#000000' 40), [float]$x, [float]$top, [float]$w, 3)
  # 窓（朝・夜で同じ並び。夜は乱数で明かりの点いた窓を決める）
  for ($wy = $top + 8; $wy -lt $ground - 10; $wy += 12) {
    for ($wx = $x + 5; $wx -lt $x + $w - 8; $wx += 10) {
      $lit = $rnd.NextDouble() -lt 0.55
      if ($night) {
        $col = if ($lit) { $winOn } else { $winOff }
        if ($lit) { $g.FillRectangle((Brush $winOn 40), [float]($wx - 2), [float]($wy - 2), 10, 11) }
      } else {
        $col = if ($lit) { $winOff } else { $winOn }
      }
      $g.FillRectangle((Brush $col), [float]$wx, [float]$wy, 6, 7)
    }
  }
}
function Draw-City($g, [bool]$night) {
  if ($night) {
    $skyTop='#0A1230'; $skyBot='#33407A'; $far='#1A2448'
    $bodies=@('#2B3150','#33304A','#262E44','#30364F')
    $winOff='#1A1F33'; $winOn='#FFD45A'
    $walk='#3A3D4A'; $road='#22242B'; $line='#8A8030'; $tree='#123020'; $pole='#555A66'
  } else {
    $skyTop='#8FCBF2'; $skyBot='#FFEACB'; $far='#B5C5D8'
    $bodies=@('#E7D7C1','#C9D6E3','#F0C9A0','#B8C4CF')
    $winOff='#6F9CC8'; $winOn='#A9CBEA'
    $walk='#D3D0CA'; $road='#6B6F78'; $line='#F2F2F2'; $tree='#3E8E3A'; $pole='#7A808C'
  }
  Sky $g $skyTop $skyBot 230
  $rnd = New-Object System.Random 21
  if ($night) { Stars $g $rnd 90 110; Moon $g 300 52 }
  else {
    Sun $g 300 60; Cloud $g 20 30; Cloud $g 150 50
    # 鳥
    $pen = New-Object System.Drawing.Pen (C '#3A4A5A'), 1.4
    foreach ($bd in @(@(110,30), @(125,38), @(95,40))) {
      $g.DrawLines($pen, (Pts @($bd[0],$bd[1], ($bd[0]+5),($bd[1]+3), ($bd[0]+10),$bd[1])))
    }
  }

  $ground = 250
  # 遠くのビル（シルエット）
  $rf = New-Object System.Random 5
  $x = -5
  while ($x -lt $BW) {
    $w = 18 + $rf.Next(0, 18); $h = 90 + $rf.Next(0, 70)
    $g.FillRectangle((Brush $far), [float]$x, [float]($ground - $h), [float]$w, [float]$h)
    $x += $w + 2
  }
  # ビルのすき間から空が見えないよう、下の方を遠くのビルの色で埋める
  $g.FillRectangle((Brush $far), 0, ($ground - 60), $BW, 60)
  # 電波塔
  $g.FillPolygon((Brush $far), (Pts @(205,$ground, 213,60, 217,60, 225,$ground)))
  $g.FillRectangle((Brush $far), 211, 100, 8, 6)
  if ($night) { $g.FillEllipse((Brush '#FF5A5A'), 212, 55, 6, 6) }

  # 手前のビル（朝夜で同じ乱数の並び）
  $rb = New-Object System.Random 9
  $rw = New-Object System.Random 13
  $x = -4; $i = 0
  while ($x -lt $BW) {
    $w = 40 + $rb.Next(0, 30); $h = 60 + $rb.Next(0, 90)
    Draw-Building $g $x $w $h $bodies[$i % 4] $winOff $winOn $night $rw $ground
    $x += $w + 3; $i++
  }

  # 歩道と道路
  $g.FillRectangle((Brush $walk), 0, $ground, $BW, 14)
  $g.FillRectangle((Brush $road), 0, $ground + 14, $BW, $BH - $ground - 14)
  for ($lx = 0; $lx -lt $BW; $lx += 40) { $g.FillRectangle((Brush $line), [float]$lx, 291, 22, 3) }

  # 街路樹と街灯
  foreach ($tx in @(30, 130, 250, 350)) {
    $g.FillRectangle((Brush '#5A3E2B'), [float]($tx - 2), [float]($ground - 6), 4, 14)
    $g.FillEllipse((Brush $tree), [float]($tx - 11), [float]($ground - 26), 22, 22)
  }
  foreach ($px in @(80, 190, 300)) {
    $g.FillRectangle((Brush $pole), [float]($px - 1.5), [float]($ground - 50), 3, 60)
    $g.FillRectangle((Brush $pole), [float]($px - 1.5), [float]($ground - 50), 12, 3)
    if ($night) {
      $g.FillPolygon((Brush '#FFE08A' 45), (Pts @(($px + 6),($ground - 46), ($px - 22),($ground + 70), ($px + 40),($ground + 70))))
      $g.FillEllipse((Brush '#FFE08A' 90), [float]($px + 1), [float]($ground - 51), 12, 10)
      $g.FillEllipse((Brush '#FFF6C8'), [float]($px + 4), [float]($ground - 48), 6, 5)
    } else {
      $g.FillEllipse((Brush '#EDEDED'), [float]($px + 4), [float]($ground - 48), 6, 5)
    }
  }

  # 車
  foreach ($car in @(@(40,272,'#E53935',1), @(220,298,'#1E88E5',-1))) {
    $cx = $car[0]; $cy = $car[1]; $dir = $car[3]
    $body = if ($night) { '#3A3A44' } else { $car[2] }
    $g.FillRectangle((Brush $body), [float]$cx, [float]$cy, 50, 12)
    $g.FillRectangle((Brush $body), [float]($cx + 10), [float]($cy - 8), 28, 9)
    $glassA = if ($night) { 60 } else { 255 }
    $g.FillRectangle((Brush '#BFE3F7' $glassA), [float]($cx + 13), [float]($cy - 6), 10, 6)
    $g.FillRectangle((Brush '#BFE3F7' $glassA), [float]($cx + 25), [float]($cy - 6), 10, 6)
    $g.FillEllipse((Brush '#111111'), [float]($cx + 6), [float]($cy + 8), 9, 9)
    $g.FillEllipse((Brush '#111111'), [float]($cx + 35), [float]($cy + 8), 9, 9)
    if ($night) {
      $fx = if ($dir -gt 0) { $cx + 50 } else { $cx }
      $bx = if ($dir -gt 0) { $cx - 2 } else { $cx + 48 }
      $tip = if ($dir -gt 0) { $fx + 60 } else { $fx - 60 }
      $g.FillPolygon((Brush '#FFF3B0' 60), (Pts @($fx,($cy + 2), $tip,($cy - 8), $tip,($cy + 18))))
      $g.FillEllipse((Brush '#FFF3B0'), [float]($fx - 3), [float]($cy + 2), 6, 5)
      $g.FillEllipse((Brush '#FF3B3B'), [float]($bx), [float]($cy + 2), 4, 5)
    }
  }
}

# ---------- ステージ3：花 ----------
$FLOWERS = @(
  # x, 花の高さ(y), 大きさ, 花びらの色, 中心の色
  @(55, 150, 1.0, '#F48FB1', '#FFD54F'),
  @(125, 105, 1.2, '#FFD54F', '#8D5524'),
  @(200, 80, 1.35, '#EF5350', '#FFEB3B'),
  @(275, 115, 1.15, '#B39DDB', '#FFF176'),
  @(335, 160, 1.0, '#FFB74D', '#8D5524'),
  @(90, 215, 0.8, '#FFFFFF', '#FFC107'),
  @(240, 205, 0.85, '#F06292', '#FFF59D'),
  @(310, 235, 0.75, '#81D4FA', '#FFF59D')
)
function Draw-Flowers($g, [bool]$bloom) {
  if ($bloom) { Sky $g '#9ED8FF' '#FFF3D6' 220 } else { Sky $g '#C9E4F5' '#F3EEDD' 220 }
  $rnd = New-Object System.Random 31
  if ($bloom) {
    Sun $g 320 50
    # 光の筋
    for ($a = 0; $a -lt 360; $a += 30) { RotEllipse $g 320 50 $a 10 60 26 (Brush '#FFF2C0' 50) }
  } else {
    $g.FillEllipse((Brush '#FFF8E0' 160), 296, 30, 40, 40)   # 朝のうすい太陽
    Cloud $g 40 40; Cloud $g 170 60
  }
  # 遠くの丘
  $hillCol = if ($bloom) { '#A5D6A7' } else { '#B7D3B8' }
  $g.FillPolygon((Brush $hillCol), (Pts @(0,200, 90,175, 190,195, 290,170, 374,190, 374,320, 0,320)))
  # 草地
  $grass = if ($bloom) { '#7CC36A' } else { '#93BF84' }
  $g.FillRectangle((Brush $grass), 0, 215, $BW, 105)
  $g.FillPolygon((Brush $grass), (Pts @(0,215, 120,205, 260,212, 374,204, 374,220, 0,220)))
  # 草の葉
  $pen = New-Object System.Drawing.Pen (C '#4E9A4A'), 1.2
  for ($i = 0; $i -lt 120; $i++) {
    $x = $rnd.NextDouble() * $BW; $y = 222 + $rnd.NextDouble() * 98
    $g.DrawLine($pen, [float]$x, [float]$y, [float]($x + $rnd.NextDouble() * 4 - 2), [float]($y - 5))
  }

  foreach ($f in $FLOWERS) {
    $fx = $f[0]; $fy = $f[1]; $s = $f[2]; $petal = $f[3]; $center = $f[4]
    # 茎
    $stem = New-Object System.Drawing.Pen (C '#3F8F3A'), ([float](3.2 * $s))
    $g.DrawBezier($stem, [float]$fx, 322, [float]($fx - 10), [float](($fy + 322) / 2 + 30), [float]($fx + 8), [float](($fy + 322) / 2 - 20), [float]$fx, [float]$fy)
    # 葉
    $ly = $fy + (322 - $fy) * 0.55
    RotEllipse $g $fx $ly -55 (10 * $s) (24 * $s) 0 (Brush '#4CAF50')
    RotEllipse $g $fx ($ly + 18 * $s) 55 (9 * $s) (22 * $s) 0 (Brush '#43A047')

    if ($bloom) {
      # 開いた花：花びら8枚 + 中心
      for ($a = 0; $a -lt 360; $a += 45) { RotEllipse $g $fx $fy $a (12 * $s) (22 * $s) (4 * $s) (Brush $petal) }
      for ($a = 22.5; $a -lt 360; $a += 45) { RotEllipse $g $fx $fy $a (8 * $s) (14 * $s) (4 * $s) (Brush '#FFFFFF' 70) }
      $r = 8 * $s
      $g.FillEllipse((Brush $center), [float]($fx - $r), [float]($fy - $r), [float]($r * 2), [float]($r * 2))
      $g.FillEllipse((Brush '#000000' 30), [float]($fx - $r * 0.5), [float]($fy - $r * 0.2), [float]$r, [float]$r)
    } else {
      # つぼみ：ふくらんだ花びら + がく
      $budW = 13 * $s; $bh = 24 * $s   # ※ $bw は $BW（画像の幅）と同じ変数になるので使わない
      $g.FillEllipse((Brush $petal), [float]($fx - $budW / 2), [float]($fy - $bh * 0.8), [float]$budW, [float]$bh)
      $g.FillEllipse((Brush '#FFFFFF' 60), [float]($fx - $budW * 0.3), [float]($fy - $bh * 0.7), [float]($budW * 0.3), [float]($bh * 0.5))
      RotEllipse $g $fx ($fy + $bh * 0.2) -25 (7 * $s) (16 * $s) 0 (Brush '#558B2F')
      RotEllipse $g $fx ($fy + $bh * 0.2) 25 (7 * $s) (16 * $s) 0 (Brush '#558B2F')
      RotEllipse $g $fx ($fy + $bh * 0.2) 0 (6 * $s) (12 * $s) 0 (Brush '#689F38')
    }
  }

  if ($bloom) {
    # ちょうちょ
    foreach ($bf in @(@(160, 150, '#FFB300'), @(300, 200, '#E1BEE7'), @(30, 220, '#80DEEA'))) {
      $bx = $bf[0]; $by = $bf[1]
      RotEllipse $g $bx $by -40 8 12 0 (Brush $bf[2])
      RotEllipse $g $bx $by 40 8 12 0 (Brush $bf[2])
      RotEllipse $g $bx $by -140 6 8 0 (Brush $bf[2])
      RotEllipse $g $bx $by 140 6 8 0 (Brush $bf[2])
      $g.FillRectangle((Brush '#3E2723'), [float]($bx - 1), [float]($by - 6), 2, 12)
    }
  } else {
    # 朝つゆ
    for ($i = 0; $i -lt 30; $i++) {
      $x = $rnd.NextDouble() * $BW; $y = 225 + $rnd.NextDouble() * 90
      $g.FillEllipse((Brush '#FFFFFF' 150), [float]$x, [float]$y, 2.2, 2.2)
    }
  }
}

# ---------- 出力 ----------
function New-StageBitmap([int]$stage, [bool]$after) {
  $bmp = New-Object System.Drawing.Bitmap ($BW * $SC), ($BH * $SC)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode = 'AntiAlias'
  $g.ScaleTransform($SC, $SC)
  switch ($stage) {
    1 { Draw-Farm $g $after }
    2 { Draw-City $g $after }
    3 { Draw-Flowers $g $after }
  }
  $g.Dispose()
  return $bmp
}
function Save-Thumb($src, [string]$path) {
  # サムネイル（a の縮小版）561×480
  $tw = [int]($BW * 1.5); $th = [int]($BH * 1.5)
  $t = New-Object System.Drawing.Bitmap $tw, $th
  $g = [System.Drawing.Graphics]::FromImage($t)
  $g.InterpolationMode = 'HighQualityBicubic'
  $g.DrawImage($src, 0, 0, $tw, $th)
  $g.Dispose()
  $t.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $t.Dispose()
}

$afterImages = @()
foreach ($n in 1..3) {
  $a = New-StageBitmap $n $false
  $a.Save((Join-Path $OutDir "block${n}a.png"), [System.Drawing.Imaging.ImageFormat]::Png)
  Save-Thumb $a (Join-Path $OutDir "block${n}c.png")
  $a.Dispose()
  $b = New-StageBitmap $n $true
  $b.Save((Join-Path $OutDir "block${n}b.png"), [System.Drawing.Imaging.ImageFormat]::Png)
  $afterImages += $b
}

# ---------- clear.png（402×874 の3倍 = 1206×2622） ----------
$CW = 402; $CH = 874
$bmp = New-Object System.Drawing.Bitmap ($CW * $SC), ($CH * $SC)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = 'AntiAlias'
$g.TextRenderingHint = 'AntiAlias'
$g.InterpolationMode = 'HighQualityBicubic'
$g.ScaleTransform($SC, $SC)

$rect = New-Object System.Drawing.RectangleF 0, 0, $CW, $CH
$bg = New-Object System.Drawing.Drawing2D.LinearGradientBrush $rect, (C '#14103A'), (C '#4A2366'), 90
$g.FillRectangle($bg, 0, 0, $CW, $CH)

$rnd = New-Object System.Random 77
# 星
for ($i = 0; $i -lt 150; $i++) {
  $x = $rnd.NextDouble() * $CW; $y = $rnd.NextDouble() * $CH; $s = $rnd.NextDouble() * 1.5 + 0.4
  $g.FillEllipse((Brush '#FFFFFF' ($rnd.Next(80, 220))), [float]$x, [float]$y, [float]$s, [float]$s)
}
# 花火
$fwColors = @('#FFD54F', '#FF6F91', '#7FDBFF', '#B9F18C', '#FFFFFF', '#FFA94D')
foreach ($fw in @(@(70, 70, 46), @(330, 60, 52), @(200, 30, 30), @(40, 400, 34), @(365, 430, 38), @(60, 760, 30), @(350, 770, 34))) {
  $cx = $fw[0]; $cy = $fw[1]; $r = $fw[2]
  $col = $fwColors[$rnd.Next(0, $fwColors.Count)]
  $pen = New-Object System.Drawing.Pen (C $col 170), 1.3
  for ($a = 0; $a -lt 360; $a += 15) {
    $rad = $a * [Math]::PI / 180
    $x1 = $cx + [Math]::Cos($rad) * $r * 0.3; $y1 = $cy + [Math]::Sin($rad) * $r * 0.3
    $x2 = $cx + [Math]::Cos($rad) * $r;       $y2 = $cy + [Math]::Sin($rad) * $r
    $g.DrawLine($pen, [float]$x1, [float]$y1, [float]$x2, [float]$y2)
    $g.FillEllipse((Brush $col), [float]($x2 - 1.5), [float]($y2 - 1.5), 3, 3)
  }
}
# 紙吹雪
$cfColors = @('#FFD54F', '#FF6F91', '#7FDBFF', '#B9F18C', '#FFA94D', '#C792EA')
for ($i = 0; $i -lt 90; $i++) {
  $x = $rnd.NextDouble() * $CW; $y = $rnd.NextDouble() * $CH
  $st = $g.Save()
  $g.TranslateTransform([float]$x, [float]$y)
  $g.RotateTransform([float]($rnd.NextDouble() * 360))
  $g.FillRectangle((Brush $cfColors[$rnd.Next(0, $cfColors.Count)] 220), -3, -1.5, 6, 3)
  $g.Restore($st)
}

# タイトル文字
$sf = New-Object System.Drawing.StringFormat
$sf.Alignment = 'Center'; $sf.LineAlignment = 'Center'
$font = New-Object System.Drawing.Font 'Meiryo', 40, ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
$font2 = New-Object System.Drawing.Font 'Meiryo', 16, ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
$g.DrawString('おめでとう！', $font, (Brush '#000000' 120), (New-Object System.Drawing.RectangleF 3, 63, $CW, 60), $sf)
$g.DrawString('おめでとう！', $font, (Brush '#FFD54F'), (New-Object System.Drawing.RectangleF 0, 60, $CW, 60), $sf)
$g.DrawString('ALL STAGE CLEAR', $font2, (Brush '#FFFFFF'), (New-Object System.Drawing.RectangleF 0, 112, $CW, 24), $sf)

# 3つの「崩した後の絵」を写真のように並べる
$pw = 250; $ph = [int]($pw * $BH / $BW)   # 250×214
$photos = @(@(60, 150, -4), @(92, 380, 3), @(60, 610, -3))
for ($i = 0; $i -lt 3; $i++) {
  $px = $photos[$i][0]; $py = $photos[$i][1]; $rot = $photos[$i][2]
  $st = $g.Save()
  $g.TranslateTransform([float]($px + $pw / 2), [float]($py + $ph / 2))
  $g.RotateTransform([float]$rot)
  $g.FillRectangle((Brush '#000000' 90), [float](-$pw / 2 - 4), [float](-$ph / 2 - 2), [float]($pw + 14), [float]($ph + 14))
  $g.FillRectangle((Brush '#FFFFFF'), [float](-$pw / 2 - 7), [float](-$ph / 2 - 7), [float]($pw + 14), [float]($ph + 14))
  $g.DrawImage($afterImages[$i], [float](-$pw / 2), [float](-$ph / 2), [float]$pw, [float]$ph)
  $g.Restore($st)
}
# 下部はゲーム側で最終スコアを表示するので空けておく（y 840 付近〜）

$g.Dispose()
$bmp.Save((Join-Path $OutDir 'clear.png'), [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
foreach ($b in $afterImages) { $b.Dispose() }

Write-Host "画像を作成しました: $OutDir"
