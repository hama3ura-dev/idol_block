ブロック崩し 素材の作り直し（option フォルダ）
==========================================

このファイルは、ゲームの画像・効果音・BGM・アイコンを、付属のスクリプトで
作り直したい人向けの説明です。
ゲームの遊び方や、難易度の調整・画像の差し替えは、ひとつ上のフォルダの readme.txt を見てください。

※ ゲームを遊ぶだけなら、この option フォルダは必要ありません。


■ option フォルダの中身
  make_stages.ps1 … ステージの画像（block1a～block3c.png・clear.png）を作る（PowerShell）
  make_se.py      … 効果音（se フォルダの mp3）を作る（Python）
  make_bgm.py     … BGM（bgm フォルダの mp3）を作る（Python）
  make_favicon.py … ブラウザのタブに出るアイコン（favicon.ico）を作る（Python）
  make_ogp.html   … SNS 用のサムネイル画像（ogp.png）を組み立てるページ（Edge / Chrome で書き出す）
  readme2.txt     … このファイル

  どれも、画像や音のファイルを使わず、図形や波形をプログラムで計算して作っています。
  作った素材はすべてオリジナルです。


■ 準備
  ・make_stages.ps1 … Windows に入っている PowerShell で動きます。準備は不要です。
  ・make_favicon.py … Python 3 だけで動きます。
  ・make_se.py / make_bgm.py … Python 3 に加えて、次の2つのライブラリが必要です。
      numpy   … 計算を速くするライブラリ
      lameenc … mp3 を作るライブラリ
    コマンドプロンプトや PowerShell で次のように入れます。
      pip install numpy lameenc

  以下のコマンドは、すべて option フォルダで実行します。
  （エクスプローラーで option フォルダを開き、アドレス欄に powershell と入力して Enter で開けます）


■ ステージの画像を作り直す（make_stages.ps1）
  四角形・三角形・円などの図形を描いて、ステージの絵を作っています。

  実行方法
    .\make_stages.ps1

  ・option フォルダ（スクリプトと同じ場所）に block1a～block3c.png と clear.png の10枚が保存されます。
  ・ゲームで使っている image フォルダの画像は上書きしません。
    できた画像を使いたいときは、image フォルダへコピー（上書き）してください。
  ・保存先を変えたいときは -OutDir で指定します。
      例：.\make_stages.ps1 -OutDir ..\image    （image フォルダに直接上書き保存）
  ・保存先にある同じ名前の画像は、実行するたびに上書きされます。
  ・スクリプトを編集して保存するときは、文字コードを「UTF-8（BOM 付き）」にしてください。
    BOM なしで保存すると、Windows PowerShell 5.1 でエラーになります。
  ・「スクリプトの実行が無効」というエラーが出たときは、先に次を実行してください
    （今開いている PowerShell の中だけ、スクリプトの実行を許可します）。
      Set-ExecutionPolicy -Scope Process Bypass


■ 効果音を作り直す（make_se.py）
  金属的で SF っぽい音を、波形の計算で作っています。

  実行方法
    python make_se.py ..\se

  ・se フォルダの7つの mp3 が上書きされます。
      start.mp3（スタート） / brick.mp3（ブロック） / paddle.mp3（パドル） / wall.mp3（壁）
      miss.mp3（ミス） / clear.mp3（ステージクリア） / allclear.mp3（全ステージクリア）
  ・音を変えたいときは、スクリプトの中の make_brick / make_paddle などの関数の数字を変えます。
    例：make_brick の 2600 や 1700 を大きくすると、ブロックの音が高くなります。
  ・ジングル（start / clear / allclear）のメロディは、make_start / make_clear / make_allclear の
    中に音名（"C5" = ド、"E5" = ミ など）で書いてあります。


■ BGM を作り直す（make_bgm.py）
  ベースの効いたロック調の曲を、ドラム・ベース・ギター・メロディを計算して作っています。

  実行方法
    python make_bgm.py ..\bgm

  ・bgm フォルダの6つの mp3 が上書きされます（1曲あたり数秒かかります）。
      stage1.mp3 / stage2.mp3 / stage3.mp3       … ふだんの曲（120 / 140 / 170 BPM）
      stage1b.mp3 / stage2b.mp3 / stage3b.mp3    … アップテンポ版（138 / 161 / 195 BPM）

  スクリプトの先頭で変えられる設定
    BGM_RMS_DB      … BGM の音量（初期値 -20）。効果音とのバランスで決めています。
                      小さくするなら -23、大きくするなら -17 など。
    FAST_TEMPO_RATE … アップテンポ版の速さ（初期値 1.15 = 15% 速い。音程は変わりません）

  曲の中身（SONGS）
    bpm    … テンポ
    prog   … 16小節のコード進行（"E" = ミ、"A#" = ラ# など。ベースとギターのルート音）
    kick   … バスドラムを鳴らす拍
    bass   … ベースのリズム
    gtr    … ギターのリズム（前半8小節・後半8小節）
    lead   … 後半8小節のメロディ（MIDI 番号：60 = ド、62 = レ、64 = ミ …、None = 休み）

  ・つなぎ目なしでループさせるため、ファイルの最後に曲の頭を 0.5 秒付けています。
  ・テンポや小節数、FAST_TEMPO_RATE を変えたときは、index.html の CONFIG.bgm の
    bpm / fastBpm / bars も同じ値に合わせてください。合っていないとループがずれます。
    アップテンポ版のテンポは「元のテンポ × FAST_TEMPO_RATE を四捨五入した値」です。


■ アイコンを作り直す（make_favicon.py）
  紺色の角丸の四角に、ブロック・ボール・パドルを描いたアイコンを作ります。

  実行方法
    python make_favicon.py ..\favicon.ico

  ・16 / 32 / 48 / 256 ピクセルの4サイズを1つの favicon.ico にまとめます。
  ・色はスクリプトの先頭の BG（背景）、BORDER（ふち）、ROW_COLORS（ブロックの色）で変えられます。
  ・ブラウザは古いアイコンを覚えていることがあるので、差し替えた後は
    ページを再読み込み（PC なら Ctrl + F5）してください。


■ SNS 用のサムネイル画像を作り直す（make_ogp.html）
  赤いロゴ「BLOCK ATTACK」を少し斜めに大きく置き、その下に本物のゲーム画面3つ
  （ステージ1を真ん中、2と3を左右）を少し角度を付けて並べた、1200×630 の画像です。
  ゲーム画面は index.html をそのまま中に表示しているので、ゲームの画像を差し替えると
  サムネイルの中の絵も変わります。

  作り方（Web サーバー経由で開く必要があります。ファイルを直接開くとゲーム画面が出ません）
    1. block_attack の1つ上のフォルダで、簡単な Web サーバーを起動します（Python が必要）。
         python -m http.server 8765
    2. 別の PowerShell で、Edge を画面なしで動かして画像として保存します（1行で入力）。
         & "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --hide-scrollbars --mute-audio --force-device-scale-factor=1 --window-size=1200,630 --virtual-time-budget=8000 --screenshot="$PWD\..\ogp.png" "http://localhost:8765/block_attack/option/make_ogp.html"
       （option フォルダで実行すると、block_attack フォルダの ogp.png が上書きされます）
    3. 終わったら、1 の PowerShell で Ctrl + C を押して Web サーバーを止めます。

  ・見た目を確かめるだけなら、ブラウザで http://localhost:8765/block_attack/option/make_ogp.html
    を開き、ウインドウを 1200×630 くらいにして見てください。
  ・変えられるところ（make_ogp.html の中）
      ロゴの文字   … <div class="logo"> の中の「BLOCK<br>ATTACK」（4か所とも同じにする）
      ロゴの傾き   … .logo の transform: rotate(-7deg) skewX(-8deg)
      ロゴの色     … .logo .front の linear-gradient（上から下への赤のグラデーション）
      画面の角度   … .main / .left / .right の transform（rotateX・rotateY・rotateZ）
      崩れた形     … HOLES（崩しておくブロックの 段, 列 の一覧。段は 0～9、列は 0～5）
      スコアなど   … setupFrame の中の score / speedBoost / ball の位置
  ・Chrome を使う場合は、2 の msedge.exe の部分を
    "C:\Program Files\Google\Chrome\Application\chrome.exe" に変えます。
