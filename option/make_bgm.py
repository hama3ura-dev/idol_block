"""ブロック崩し用 BGM（ベースの効いたロック調・ループ）を3曲合成して MP3 で保存する。
使い方: python make_bgm.py <出力フォルダ>
必要なもの: Python 3、numpy、lameenc（pip install numpy lameenc）

  stage1.mp3 … E マイナー / 120 BPM / ミドルテンポのロック
  stage2.mp3 … A マイナー / 140 BPM / ギャロップするベースのハードロック
  stage3.mp3 … D マイナー / 170 BPM / 一番速い疾走ロック
  stage1b.mp3 / stage2b.mp3 / stage3b.mp3
             … 上の3曲のアップテンポ版（テンポ FAST_TEMPO_RATE 倍、音程はそのまま）
               stage1b 138 BPM / stage2b 161 BPM / stage3b 195 BPM

・各曲 16 小節（Aメロ8小節＋Bメロ8小節）で、最後が最初につながる「ループ」になっています。
  曲の終わりで鳴り続けている音は曲の頭に回り込ませているので、つなぎ目でも音が途切れません。
・ファイルの最後には、曲の頭 0.5 秒を余分に付けてあります（つなぎ目なしループ用）。
  1周の長さ = 64拍 × 60 ÷ BPM 秒（stage1 32.00秒 / stage2 27.43秒 / stage3 22.59秒）。
・効果音（高い金属音）とぶつからないよう、3kHz より上は弱めてあります。
"""
import os
import sys

import lameenc
import numpy as np

SR = 44100
TAU = 2 * np.pi
# BGM の平均音量（dB）。効果音は約 -10〜-13 dB なので、それより 7〜10 dB 小さくしている。
# もっと小さくしたいときは -23 など、大きくしたいときは -17 などに変える。
BGM_RMS_DB = -20.0
# アップテンポ版（stage1b.mp3 など）のテンポの倍率。1.15 = 15% 速い（音程は変わらない）
FAST_TEMPO_RATE = 1.15
RNG = np.random.default_rng(12345)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ---------------------------------------------------------------- 音色
def additive_saw(f, n, max_freq, detune=0.0):
    """倍音を max_freq までに抑えたノコギリ波（にごりのない、こもり気味の音）"""
    t = np.arange(n) / SR
    out = np.zeros(n)
    k = 1
    while f * k < max_freq and k < 60:
        out += np.sin(TAU * f * k * (1 + detune) * t) / k
        k += 1
    return out


def env(n, attack, tau, gate=None, release=0.01):
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(attack, 1e-4)) * np.exp(-t / tau)
    if gate is not None:  # 指定した長さで音を切る（リリースを付けて）
        g = int(gate * SR)
        r = max(1, int(release * SR))
        if g < n:
            fade = np.clip(1 - (np.arange(n) - g) / r, 0, 1)
            e *= np.where(np.arange(n) < g, 1.0, fade)
    return e


def bass_note(midi, dur):
    f = mtof(midi)
    n = int((dur + 0.03) * SR)
    x = additive_saw(f, n, 1400) * 0.7 + np.sin(TAU * f * np.arange(n) / SR) * 0.6  # 芯のある低音
    x = np.tanh(1.8 * x) / np.tanh(1.8)
    return x * env(n, 0.003, 0.6, gate=dur, release=0.02)


def power_chord(midi, dur, muted):
    """パワーコード（ルート・5度・オクターブ）をひずませたギター"""
    n = int((dur + (0.02 if muted else 0.1)) * SR)
    x = np.zeros(n)
    for iv in (0, 7, 12):
        f = mtof(midi + iv)
        x += additive_saw(f, n, 3000, -0.002) + additive_saw(f, n, 3000, 0.002)
    x = np.tanh(3.5 * x / 3) / np.tanh(3.5)
    if muted:
        e = env(n, 0.002, 0.06, gate=dur, release=0.015)
    else:
        e = env(n, 0.003, 1.2, gate=dur, release=0.08)
    return x * e


def lead_note(midi, dur):
    """やわらかいシンセのリード（奇数倍音少なめ＋ビブラート）"""
    f = mtof(midi)
    n = int((dur + 0.05) * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.006 * np.sin(TAU * 5.5 * t) * np.clip((t - 0.15) / 0.2, 0, 1)
    ph = np.cumsum(f * vib) / SR
    x = np.sin(TAU * ph) + np.sin(TAU * 3 * ph) / 6 + np.sin(TAU * 2 * ph) / 8
    return x * env(n, 0.01, 2.0, gate=dur * 0.95, release=0.04)


def fft_filter(x, fn):
    """周期的（ループ）な信号用の FFT フィルター。fn(周波数配列) が倍率を返す"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X * fn(f), len(x))


def lowpass(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order))


def highpass(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def kick():
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t / 0.025)
    x = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.13)
    x[: int(0.003 * SR)] += RNG.uniform(-0.4, 0.4, int(0.003 * SR))
    return np.tanh(1.5 * x)


def snare():
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    tone = np.sin(TAU * 185 * t) * np.exp(-t / 0.04) * 0.6
    nz = fft_filter(RNG.uniform(-1, 1, n), lambda f: highpass(700)(f) * lowpass(5000)(f)) * np.exp(-t / 0.07)
    return tone + nz * 1.4


def hat():
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    return fft_filter(RNG.uniform(-1, 1, n), highpass(6000, 3)) * np.exp(-t / 0.012)


def crash():
    n = int(1.5 * SR)
    t = np.arange(n) / SR
    return fft_filter(RNG.uniform(-1, 1, n), highpass(3500, 2)) * np.exp(-t / 0.5)


KICK, SNARE, HAT, CRASH = kick(), snare(), hat(), crash()


# ---------------------------------------------------------------- 配置（ループ）
class Track:
    def __init__(self, length):
        self.buf = np.zeros(length)

    def add(self, pos, sig, vol=1.0):
        """pos サンプル目から sig を足す。はみ出た分は曲の頭に回り込む（ループ用）"""
        L = len(self.buf)
        pos %= L
        sig = sig * vol
        while len(sig):
            m = min(len(sig), L - pos)
            self.buf[pos:pos + m] += sig[:m]
            sig = sig[m:]
            pos = 0


ROOT = {"A": 33, "A#": 34, "B": 35, "C": 36, "C#": 37, "D": 38, "D#": 39,
        "E": 40, "F": 41, "F#": 42, "G": 43, "G#": 44}


def render(song):
    bpm = song["bpm"]
    beat = 60 / bpm
    bars = len(song["prog"])
    L = int(round(bars * 4 * beat * SR))
    to_s = lambda b: int(round(b * beat * SR))

    drums, bass, gtr, lead = Track(L), Track(L), Track(L), Track(L)

    for bar, chord in enumerate(song["prog"]):
        b0 = bar * 4
        sec = bar // 8           # 0 = Aメロ, 1 = Bメロ
        fill = bar % 8 == 7      # 8小節目はフィルイン
        root = ROOT[chord]

        # --- ドラム
        if bar % 8 == 0:
            drums.add(to_s(b0), CRASH, 0.35)
        for k in song["kick"]:
            if fill and k >= 2:
                continue
            drums.add(to_s(b0 + k), KICK, 1.0)
        for s in (1, 3):
            if fill and s >= 2:
                continue
            drums.add(to_s(b0 + s), SNARE, 0.55)
        for i in range(8):
            if fill and i >= 4:
                continue
            drums.add(to_s(b0 + i * 0.5), HAT, 0.35 if i % 2 == 0 else 0.22)
        if fill:
            step = song["fill_step"]
            hits = int(2 / step)
            for i in range(hits):
                drums.add(to_s(b0 + 2 + i * step), SNARE, 0.3 + 0.35 * i / hits)
            drums.add(to_s(b0 + 2), KICK, 1.0)
            drums.add(to_s(b0 + 3), KICK, 1.0)

        # --- ベース
        for off, dur, iv in song["bass"]:
            bass.add(to_s(b0 + off), bass_note(root + iv, dur * beat))

        # --- ギター
        for off, dur, muted in song["gtr"][sec]:
            gtr.add(to_s(b0 + off), power_chord(root + 12, dur * beat, muted), 1.0 if not muted else 0.8)

        # --- リード（Bメロだけ）
        if sec == 1:
            t = 0.0
            for m, d in song["lead"][bar - 8]:
                if m is not None:
                    lead.add(to_s(b0 + t), lead_note(m, d * beat))
                t += d

    # 楽器ごとの音作り
    g = fft_filter(gtr.buf, lambda f: lowpass(2200)(f) * highpass(110)(f))
    b = fft_filter(bass.buf, lowpass(900))
    ld = lead.buf
    d = int(0.75 * beat * SR)  # リードに付点8分のエコー
    ld = ld + np.roll(ld, d) * 0.35 + np.roll(ld, 2 * d) * 0.12
    ld = fft_filter(ld, lowpass(2500))

    mix = drums.buf * 0.55 + b * 0.62 + g * 0.30 + ld * 0.16
    # 効果音の邪魔をしないように高い音を弱め、極低音もカット
    mix = fft_filter(mix, lambda f: lowpass(3200, 2)(f) * highpass(32, 2)(f))
    mix = mix / np.max(np.abs(mix))
    mix = np.tanh(1.6 * mix) / np.tanh(1.6)  # 軽くコンプレッションしてロックらしい音圧に
    # 音量は効果音より控えめに：3曲とも平均音量（RMS）を BGM_RMS_DB にそろえる
    mix *= 10 ** (BGM_RMS_DB / 20) / np.sqrt(np.mean(mix ** 2))
    # 曲の頭 0.5 秒を最後にも付け足す。MP3 は先頭に無音のすき間が入るので、
    # ゲーム側は「1周ずらすと同じ音になる位置」を探してつなぎ目なしでループさせる。
    return np.concatenate([mix, mix[: SR // 2]])


# ---------------------------------------------------------------- 曲データ
# リードの音（MIDI番号）: 60=ド(C4) 62=レ 64=ミ 65=ファ 67=ソ 69=ラ 71=シ 72=ド(C5)
SONGS = {
    "stage1": {
        "bpm": 120,
        "prog": ["E", "C", "D", "E", "E", "C", "D", "B",
                 "C", "D", "E", "E", "C", "D", "B", "B"],
        "kick": [0, 2, 2.5],
        "fill_step": 0.5,
        "bass": [(i * 0.5, 0.45, 12 if i == 7 else 0) for i in range(8)],
        "gtr": [
            [(i * 0.5, 0.45, True) for i in range(8)],            # Aメロ: ブリッジミュートで刻む
            [(0, 2.5, False), (2.5, 1.5, False)],                 # Bメロ: 伸ばす
        ],
        "lead": [
            [(67, 1), (64, 0.5), (67, 0.5), (71, 1), (69, 1)],
            [(66, 1.5), (62, 0.5), (66, 1), (69, 1)],
            [(67, 1), (71, 1), (76, 1.5), (74, 0.5)],
            [(71, 3), (None, 1)],
            [(72, 1), (71, 0.5), (69, 0.5), (67, 1), (64, 1)],
            [(66, 1), (69, 1), (74, 1), (72, 0.5), (69, 0.5)],
            [(71, 2), (66, 1), (63, 1)],
            [(66, 2), (None, 2)],
        ],
    },
    "stage2": {
        "bpm": 140,
        "prog": ["A", "F", "G", "E", "A", "F", "G", "E",
                 "F", "G", "A", "A", "F", "G", "E", "E"],
        "kick": [0, 1.5, 2, 3.5],
        "fill_step": 0.25,
        # ギャロップ（タッ・タタ）
        "bass": [(b + o, d, 12 if (b == 3 and o > 0) else 0)
                 for b in range(4) for o, d in ((0, 0.45), (0.5, 0.22), (0.75, 0.22))],
        "gtr": [
            [(0, 1.5, False)] + [(1.5 + i * 0.5, 0.45, True) for i in range(5)],
            [(0, 2.5, False), (2.5, 1.5, False)],
        ],
        "lead": [
            [(69, 0.5), (72, 0.5), (77, 1), (76, 0.5), (72, 0.5), (74, 1)],
            [(74, 1), (71, 0.5), (67, 0.5), (71, 1), (74, 1)],
            [(76, 1.5), (72, 0.5), (69, 1), (72, 1)],
            [(69, 3), (None, 1)],
            [(72, 0.5), (77, 0.5), (81, 1), (79, 0.5), (77, 0.5), (76, 1)],
            [(74, 1), (79, 1), (74, 0.5), (71, 0.5), (67, 1)],
            [(68, 1), (71, 1), (76, 1), (74, 1)],
            [(76, 2), (None, 2)],
        ],
    },
    "stage3": {
        "bpm": 170,
        "prog": ["D", "A#", "C", "D", "D", "A#", "C", "A",
                 "A#", "C", "D", "D", "A#", "C", "A", "A"],
        "kick": [0, 0.5, 1.5, 2, 2.5, 3.5],
        "fill_step": 0.25,
        "bass": [(i * 0.5, 0.4, iv) for i, iv in enumerate([0, 0, 12, 0, 0, 12, 0, 7])],
        "gtr": [
            [(i * 0.5, 0.42, True) for i in range(8)],
            [(0, 1.0, False)] + [(1 + i * 0.5, 0.42, True) for i in range(6)],
        ],
        "lead": [
            [(70, 0.5), (74, 0.5), (77, 1), (74, 0.5), (70, 0.5), (72, 1)],
            [(72, 1), (76, 0.5), (79, 0.5), (76, 1), (72, 1)],
            [(74, 0.5), (77, 0.5), (81, 1), (79, 0.5), (77, 0.5), (74, 1)],
            [(74, 3), (None, 1)],
            [(77, 1), (74, 0.5), (70, 0.5), (74, 1), (77, 1)],
            [(79, 1), (76, 0.5), (72, 0.5), (76, 1), (79, 1)],
            [(76, 1), (73, 1), (69, 1), (73, 1)],
            [(69, 2), (None, 2)],
        ],
    },
}


def save_mp3(x, path):
    pcm = (np.clip(x, -1, 1) * 32000).astype("<i2").tobytes()
    enc = lameenc.Encoder()
    enc.set_bit_rate(160)
    enc.set_in_sample_rate(SR)
    enc.set_channels(1)
    enc.set_quality(2)
    data = enc.encode(pcm) + enc.flush()
    with open(path, "wb") as f:
        f.write(data)
    print(f"{os.path.basename(path)}: {len(x) / SR:.2f}s ({len(x)} samples), {len(data) // 1024} KB")


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "bgm")
    os.makedirs(out_dir, exist_ok=True)
    for name, song in SONGS.items():
        save_mp3(render(song), os.path.join(out_dir, name + ".mp3"))
        # アップテンポ版（stage1b.mp3 など）：同じ曲を音程はそのままでテンポだけ上げる
        fast = dict(song, bpm=round(song["bpm"] * FAST_TEMPO_RATE))
        print(f"  {name}b: {song['bpm']} -> {fast['bpm']} BPM")
        save_mp3(render(fast), os.path.join(out_dir, name + "b.mp3"))


if __name__ == "__main__":
    main()
