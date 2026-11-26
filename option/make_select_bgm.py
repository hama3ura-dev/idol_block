"""ステージセレクト画面の BGM（SF っぽい短いフレーズのループ）を合成して MP3 で保存する。
使い方: python make_select_bgm.py <出力フォルダ>
必要なもの: Python 3、numpy、lameenc（pip install numpy lameenc）。make_bgm.py と同じフォルダに置く。

  select.mp3 … A マイナー / 120 BPM / 8 小節（1周 16.00 秒）
               16分音符のシンセ・アルペジオ＋パッド＋ベース＋軽いドラムのループ

・ステージ1〜3の曲と同じ作り方（ループ・音量 BGM_RMS_DB・3kHz より上を弱める）で作っています。
・ファイルの最後には、曲の頭 0.5 秒を余分に付けてあります（つなぎ目なしループ用）。
・テンポや小節数を変えたときは、index.html の CONFIG.selectBgm の bpm / bars も合わせて変えてください。
"""
import os
import sys

import numpy as np

from make_bgm import (SR, TAU, BGM_RMS_DB, KICK, SNARE, HAT, Track, additive_saw, env,
                      fft_filter, lowpass, highpass, mtof, save_mp3)

BPM = 120
# 1小節ごとのコード（ルートの MIDI 番号と、マイナーなら True）
PROG = [(57, True), (57, True), (53, False), (55, False),
        (57, True), (57, True), (53, False), (52, False)]   # Am Am F G Am Am F E


def arp_note(midi, dur):
    """キラキラしたシンセのアルペジオ（矩形波ぽい音を短く）"""
    f = mtof(midi)
    n = int((dur + 0.06) * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k in (1, 3, 5, 7):  # 奇数倍音 = 矩形波っぽい音
        if f * k < 4000:
            x += np.sin(TAU * f * k * t) / k
    return x * env(n, 0.002, 0.12, gate=dur, release=0.04)


def pad_chord(notes, dur):
    """ゆっくり立ち上がる宇宙っぽいパッド（少しずつずらしたノコギリ波）"""
    n = int((dur + 0.3) * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for m in notes:
        f = mtof(m)
        x += additive_saw(f, n, 1800, -0.004) + additive_saw(f, n, 1800, 0.004)
    trem = 1 + 0.15 * np.sin(TAU * 0.5 * t)  # ゆらゆら
    return x * trem * env(n, 0.6, 20.0, gate=dur, release=0.3)


def bass_note(midi, dur):
    f = mtof(midi)
    n = int((dur + 0.03) * SR)
    x = np.sin(TAU * f * np.arange(n) / SR) + additive_saw(f, n, 800) * 0.4
    return np.tanh(1.5 * x) * env(n, 0.003, 0.4, gate=dur, release=0.02)


def bell(midi, dur):
    """短いフレーズ用のベル（FM っぽい金属的な音）"""
    f = mtof(midi)
    n = int((dur + 0.6) * SR)
    t = np.arange(n) / SR
    mod = np.sin(TAU * f * 3.5 * t) * 1.2 * np.exp(-t / 0.3)
    return np.sin(TAU * f * t + mod) * env(n, 0.003, 0.5)


# ベルのフレーズ（4小節目と8小節目の後半で鳴る「ピロリン」）（拍の位置, MIDI, 長さ）
BELL_A = [(2.0, 76, 0.5), (2.5, 79, 0.5), (3.0, 81, 1.0)]
BELL_B = [(2.0, 81, 0.5), (2.5, 79, 0.5), (3.0, 76, 0.5), (3.5, 71, 0.5)]


def render():
    beat = 60 / BPM
    L = int(round(len(PROG) * 4 * beat * SR))
    to_s = lambda b: int(round(b * beat * SR))
    drums, bass, arp, pad, lead = Track(L), Track(L), Track(L), Track(L), Track(L)

    for bar, (root, minor) in enumerate(PROG):
        b0 = bar * 4
        third = 3 if minor else 4
        # アルペジオ：ルート・3度・5度・オクターブを16分音符で上下
        pattern = [0, third, 7, 12, 7, third, 0, 12 + third] * 2
        for i, iv in enumerate(pattern):
            arp.add(to_s(b0 + i * 0.25), arp_note(root + 12 + iv, 0.2 * beat), 0.9 if i % 4 == 0 else 0.6)
        # パッド：1小節ずっと
        pad.add(to_s(b0), pad_chord([root, root + third, root + 7], 4 * beat))
        # ベース：8分音符（オクターブ下）
        for i in range(8):
            bass.add(to_s(b0 + i * 0.5), bass_note(root - 12 + (12 if i == 7 else 0), 0.42 * beat))
        # ドラム：控えめ（ステージ中の曲より軽く）
        drums.add(to_s(b0), KICK, 0.9)
        drums.add(to_s(b0 + 2), KICK, 0.9)
        drums.add(to_s(b0 + 1), SNARE, 0.35)
        drums.add(to_s(b0 + 3), SNARE, 0.35)
        for i in range(16):
            drums.add(to_s(b0 + i * 0.25), HAT, 0.22 if i % 2 == 0 else 0.12)
        # ベル：4小節目・8小節目
        if bar % 4 == 3:
            for off, m, d in (BELL_A if bar == 3 else BELL_B):
                lead.add(to_s(b0 + off), bell(m, d * beat))

    # 音作り：アルペジオに付点8分のエコー＋フィルター
    d = int(0.75 * beat * SR)
    a = arp.buf + np.roll(arp.buf, d) * 0.4 + np.roll(arp.buf, 2 * d) * 0.16
    a = fft_filter(a, lambda f: lowpass(2600)(f) * highpass(200)(f))
    p = fft_filter(pad.buf, lambda f: lowpass(1200)(f) * highpass(120)(f))
    b = fft_filter(bass.buf, lowpass(700))
    ld = lead.buf + np.roll(lead.buf, d) * 0.3
    mix = drums.buf * 0.45 + b * 0.55 + a * 0.32 + p * 0.10 + ld * 0.22
    mix = fft_filter(mix, lambda f: lowpass(3200, 2)(f) * highpass(32, 2)(f))
    mix = mix / np.max(np.abs(mix))
    mix = np.tanh(1.6 * mix) / np.tanh(1.6)
    mix *= 10 ** (BGM_RMS_DB / 20) / np.sqrt(np.mean(mix ** 2))
    return np.concatenate([mix, mix[: SR // 2]])


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "bgm")
    os.makedirs(out_dir, exist_ok=True)
    save_mp3(render(), os.path.join(out_dir, "select.mp3"))


if __name__ == "__main__":
    main()
