"""ブロック崩し用の効果音（金属的・SF風）を合成して MP3 で保存する。
使い方: python make_se.py <出力フォルダ>
必要なもの: Python 3 と lameenc（pip install lameenc）

作る音:
  brick.mp3  … ブロックに当たった
  paddle.mp3 … パドルに当たった
  wall.mp3   … 壁に当たった
  miss.mp3   … ミス
  start.mp3  … スタート時の短いフレーズ
  clear.mp3  … ステージクリアのジングル（ステージ1・2・3共通）
  allclear.mp3 … 3ステージすべてクリアしたときの、さらにハッピーなジングル
"""
import math
import os
import random
import struct
import sys

import lameenc

SR = 44100
TAU = 2 * math.pi


# ---------------------------------------------------------------- 基本部品
def env_ad(i, n, attack, decay_pow):
    """アタック → 減衰のエンベロープ (0..1)"""
    a = min(1.0, i / max(1, SR * attack))
    return a * (1.0 - i / n) ** decay_pow


def fm_tone(dur, fc0, fc1, ratio, index0, index1, vol=0.5, attack=0.002, decay_pow=2.0):
    """FM 合成。ratio を非整数にすると金属的な響きになる。
    fc0→fc1 で音程、index0→index1 で金属っぽさ（倍音の量）が変化する。"""
    n = int(SR * dur)
    out = []
    pc = pm = 0.0
    for i in range(n):
        t = i / n
        fc = fc0 * (fc1 / fc0) ** t
        idx = index0 + (index1 - index0) * t
        pc += fc / SR
        pm += fc * ratio / SR
        s = math.sin(TAU * pc + idx * math.sin(TAU * pm))
        out.append(s * env_ad(i, n, attack, decay_pow) * vol)
    return out


def bell(dur, f, partials, vol=0.5, decay_pow=2.0):
    """非整数倍音を重ねた金属片の響き。partials = [(倍率, 音量, 減衰の速さ), ...]"""
    n = int(SR * dur)
    out = [0.0] * n
    for ratio, amp, dp in partials:
        for i in range(n):
            out[i] += math.sin(TAU * f * ratio * i / SR) * amp * (1 - i / n) ** (decay_pow * dp)
    a = int(SR * 0.0015)
    return [s * vol * min(1.0, i / max(1, a)) for i, s in enumerate(out)]


def pulse(dur, f0, f1, duty=0.25, vol=0.3, attack=0.003, decay_pow=1.0, vib_depth=0.0, vib_rate=7.0):
    """パルス波（ファミコン的な電子音）。周波数スイープとビブラート付き"""
    n = int(SR * dur)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / n
        f = f0 * (f1 / f0) ** t
        if vib_depth:
            f *= 1 + vib_depth * math.sin(TAU * vib_rate * i / SR)
        ph += f / SR
        s = 1.0 if (ph % 1.0) < duty else -1.0
        out.append(s * env_ad(i, n, attack, decay_pow) * vol)
    return out


def noise(dur, vol=0.3, decay_pow=2.0, cutoff0=6000, cutoff1=300, seed=0):
    """減衰ノイズ（ローパスのカットオフが下がっていく爆発音っぽいもの）"""
    rnd = random.Random(seed)
    n = int(SR * dur)
    out = []
    y = 0.0
    for i in range(n):
        t = i / n
        fc = cutoff0 * (cutoff1 / cutoff0) ** t
        k = 1 - math.exp(-TAU * fc / SR)
        y += k * ((rnd.random() * 2 - 1) - y)
        out.append(y * vol * (1 - t) ** decay_pow)
    return out


def mix(*tracks):
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, s in enumerate(t):
            out[i] += s
    return out


def place(total_dur, items):
    """(開始秒, 音) のリストを1本のトラックに配置する"""
    out = [0.0] * int(SR * total_dur)
    for start, snd in items:
        o = int(SR * start)
        for i, s in enumerate(snd):
            if o + i < len(out):
                out[o + i] += s
    return out


def echo(x, delay, feedback, times=4):
    d = int(SR * delay)
    out = x + [0.0] * (d * times)
    for i in range(d, len(out)):
        out[i] += out[i - d] * feedback
    return out


def ring_mod(dur, f0, f1, mod_ratio, vol=0.5, attack=0.001, decay_pow=2.0):
    """リングモジュレーション。2つの非整数比の正弦波を掛け合わせた、ロボット的・金属的な音"""
    n = int(SR * dur)
    out = []
    p1 = p2 = 0.0
    for i in range(n):
        t = i / n
        f = f0 * (f1 / f0) ** t
        p1 += f / SR
        p2 += f * mod_ratio / SR
        out.append(math.sin(TAU * p1) * math.sin(TAU * p2) * env_ad(i, n, attack, decay_pow) * vol)
    return out


def comb(x, delay_ms, feedback, tail=0.12):
    """短いディレイを繰り返すコムフィルター。金属パイプの中で響いたような共鳴を付ける"""
    d = max(1, int(SR * delay_ms / 1000))
    out = x + [0.0] * int(SR * tail)
    for i in range(d, len(out)):
        out[i] += out[i - d] * feedback
    return out


def normalize(x, peak=0.9):
    m = max(abs(s) for s in x) or 1.0
    return [s * peak / m for s in x]


def note(name):
    """'C5' などを周波数に"""
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (o + 1) - 69) / 12)


def save_mp3(samples, path):
    pcm = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32000)) for s in samples)
    enc = lameenc.Encoder()
    enc.set_bit_rate(160)
    enc.set_in_sample_rate(SR)
    enc.set_channels(1)
    enc.set_quality(2)
    data = enc.encode(pcm) + enc.flush()
    with open(path, "wb") as f:
        f.write(data)
    print(f"{os.path.basename(path)}: {len(samples) / SR:.2f}s, {len(data)} bytes")


# ---------------------------------------------------------------- 各効果音
def make_brick():
    # 高い金属片がはじけるような「ギィン」。FM の金属っぽさが急に抜けていく電子的な鳴り
    zing = fm_tone(0.12, 2600, 1700, 1.41, 9.0, 0.3, vol=0.5, attack=0.0008, decay_pow=1.8)
    ring = ring_mod(0.15, 1900, 1750, 1.618, vol=0.45, decay_pow=2.0)
    metal = bell(0.18, 1750, [(1.0, 0.4, 1.0), (2.76, 0.3, 1.4), (5.40, 0.2, 2.0), (8.93, 0.12, 2.6)], vol=0.4, decay_pow=2.0)
    x = mix(zing, ring, metal)
    return normalize(comb(x, 1.7, 0.55, tail=0.06), 0.95)


def make_paddle():
    # 金属のバネを弾いたような「ビョイン」。音程が上がってから少し揺れる
    n = int(SR * 0.2)
    body = []
    pc = pm = 0.0
    for i in range(n):
        t = i / n
        f = 420 * (1 + 0.9 * (1 - (1 - min(1.0, t * 3)) ** 2))  # 素早く上がって止まる
        f *= 1 + 0.03 * math.sin(TAU * 28 * i / SR) * t           # 後半で金属的に揺れる
        pc += f / SR
        pm += f * 2.41 / SR
        idx = 6.0 * (1 - t) ** 1.5 + 0.5
        body.append(math.sin(TAU * pc + idx * math.sin(TAU * pm)) * env_ad(i, n, 0.001, 1.6) * 0.55)
    ring = ring_mod(0.18, 840, 1500, 1.414, vol=0.3, decay_pow=2.2)
    x = mix(body, ring)
    return normalize(comb(x, 3.1, 0.5, tail=0.08), 0.85)


def make_wall():
    # 金属板をはじく短い「チィン」。高い音から素早く下がる
    hit = fm_tone(0.07, 2200, 1300, 2.37, 7.0, 0.5, vol=0.5, attack=0.0005, decay_pow=2.6)
    ring = ring_mod(0.06, 1500, 1200, 1.73, vol=0.35, decay_pow=2.8)
    click = noise(0.012, vol=0.25, decay_pow=3.0, cutoff0=10000, cutoff1=4000, seed=3)
    x = mix(hit, ring, click)
    return normalize(comb(x, 1.1, 0.45, tail=0.03), 0.95)


def make_miss():
    # レーザーが下がっていく「ピューーン」→ 爆発「ボワッ」
    laser = fm_tone(0.6, 1600, 120, 1.5, 5.0, 1.0, vol=0.5, attack=0.003, decay_pow=0.7)
    wobble = pulse(0.6, 800, 90, duty=0.25, vol=0.15, decay_pow=0.8, vib_depth=0.08, vib_rate=14)
    boom = mix(
        noise(0.7, vol=0.7, decay_pow=2.0, cutoff0=4000, cutoff1=150, seed=7),
        fm_tone(0.7, 110, 40, 1.37, 3.0, 0.0, vol=0.6, decay_pow=1.8),
    )
    return normalize(place(1.35, [(0.0, mix(laser, wobble)), (0.55, boom)]), 0.9)


def make_start():
    # オリジナルの短い上昇フレーズ（約2秒）。金属的な FM 音 + パルス波を重ね、エコーで宇宙っぽく
    def voice(f, dur, vol=0.45):
        return mix(
            fm_tone(dur, f, f, 2.0, 2.2, 0.6, vol=vol, attack=0.004, decay_pow=1.2),
            pulse(dur, f * 0.5, f * 0.5, duty=0.125, vol=vol * 0.35, decay_pow=1.2),
            bell(dur, f * 2, [(1.0, 0.25, 1.0), (2.76, 0.08, 2.0)], vol=vol * 0.6, decay_pow=1.5),
        )

    step = 0.11
    phrase = [("D5", 1), ("A5", 1), ("F5", 1), ("C6", 1), ("A#5", 1), ("F6", 1)]
    items = []
    t = 0.0
    for name, length in phrase:
        items.append((t, voice(note(name), step * length + 0.08)))
        t += step * length
    # 最後に和音を伸ばす（D と A と F#: 少し明るい終わり方）
    t += 0.04
    for name in ("D5", "F#5", "A5", "D6"):
        items.append((t, voice(note(name), 0.8, vol=0.28)))
    # 和音にゆっくりかかる高いキラキラ
    items.append((t, fm_tone(0.8, note("D7"), note("D7"), 1.41, 1.5, 0.2, vol=0.08, decay_pow=1.0)))
    total = t + 0.85
    track = place(total, items)
    return normalize(echo(track, 0.14, 0.3, times=3), 0.9)


def jingle_voice(f, dur, vol=0.45):
    """ジングル用の音色（スタートと同じ、金属的な FM ＋ パルス波 ＋ ベル）"""
    return mix(
        fm_tone(dur, f, f, 2.0, 2.2, 0.6, vol=vol, attack=0.004, decay_pow=1.2),
        pulse(dur, f * 0.5, f * 0.5, duty=0.125, vol=vol * 0.35, decay_pow=1.2),
        bell(dur, f * 2, [(1.0, 0.25, 1.0), (2.76, 0.08, 2.0)], vol=vol * 0.6, decay_pow=1.5),
    )


def play_phrase(items, t, phrase, step, vol=0.45, gate_extra=0.06):
    """phrase = [(音名 or None, 長さ(step単位)), ...] を t 秒から並べる。終わりの時刻を返す"""
    for name, length in phrase:
        if name:
            items.append((t, jingle_voice(note(name), step * length + gate_extra, vol)))
        t += step * length
    return t


def sparkle(items, t, names, step, vol=0.12):
    """高い音の細かいキラキラ（ベルの分散和音）"""
    for i, name in enumerate(names):
        items.append((t + i * step, bell(0.35, note(name), [(1.0, 0.5, 1.0), (2.76, 0.2, 2.0), (5.4, 0.08, 3.0)],
                                         vol=vol, decay_pow=2.0)))


def make_clear():
    # ステージクリア（約1.7秒）：駆け上がって「ジャーン」と明るく決める
    items = []
    step = 0.09
    t = play_phrase(items, 0.0, [("C5", 1), ("E5", 1), ("G5", 1), ("C6", 1),
                                 ("E6", 1), (None, 1), ("D6", 1), ("E6", 3)], step)
    t += 0.02
    for name in ("C5", "E5", "G5", "C6", "E6"):
        items.append((t, jingle_voice(note(name), 0.9, vol=0.24)))
    items.append((t, pulse(0.9, note("C3"), note("C3"), duty=0.5, vol=0.18, decay_pow=1.2)))  # 低音で支える
    sparkle(items, t + 0.05, ["G6", "C7", "E7", "G7"], 0.06)
    track = place(t + 0.95, items)
    return normalize(echo(track, 0.12, 0.28, times=3), 0.9)


def make_allclear():
    # 全ステージクリア（約3.6秒）：弾むファンファーレ → 大きな和音 → キラキラ
    items = []
    step = 0.115
    t = 0.0
    # ベースライン（パルス波）を区切りごとに鳴らす
    bass_line = [("F3", 6), ("A#2", 6), ("C3", 6), ("F3", 6)]
    bt = 0.0
    for name, length in bass_line:
        items.append((bt, pulse(step * length, note(name), note(name), duty=0.5, vol=0.2, decay_pow=0.6)))
        items.append((bt + step * 3, pulse(step * 3, note(name) * 2, note(name) * 2, duty=0.5, vol=0.12, decay_pow=1.0)))
        bt += step * length
    t = play_phrase(items, t, [
        ("C6", 1), ("A5", 1), ("C6", 1), ("F6", 3),
        ("D6", 1), ("C6", 1), ("D6", 1), ("A#6", 3),
        ("A6", 1), ("G6", 1), ("A6", 1), ("C7", 2), ("G6", 1),
        ("A6", 1), ("C7", 1), ("D7", 1), ("F7", 3),
    ], step, vol=0.4)
    # 最後の大きな和音（F メジャー）＋ 低音 ＋ キラキラの分散和音
    t += 0.03
    for name in ("F4", "A4", "C5", "F5", "A5", "C6", "F6"):
        items.append((t, jingle_voice(note(name), 1.4, vol=0.18)))
    items.append((t, pulse(1.4, note("F2"), note("F2"), duty=0.5, vol=0.22, decay_pow=1.0)))
    items.append((t, noise(1.2, vol=0.18, decay_pow=2.5, cutoff0=9000, cutoff1=2000, seed=11)))  # シンバル風
    sparkle(items, t + 0.08, ["F6", "A6", "C7", "F7", "A7", "C8", "A7", "F7", "C7", "A6"], 0.07, vol=0.1)
    track = place(t + 1.45, items)
    return normalize(echo(track, 0.13, 0.3, times=3), 0.9)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "se")
    os.makedirs(out_dir, exist_ok=True)
    for name, fn in [("brick", make_brick), ("paddle", make_paddle), ("wall", make_wall),
                     ("miss", make_miss), ("start", make_start),
                     ("clear", make_clear), ("allclear", make_allclear)]:
        save_mp3(fn(), os.path.join(out_dir, name + ".mp3"))


if __name__ == "__main__":
    main()
